"""
Unit tests for generate_article.py

Tests frontmatter parsing, character extraction, image prompt composition,
affiliate processing, description validation, and existing posts parsing.
All tests run locally without external API calls.
"""
import io
import json
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml
from PIL import Image

from generate_article import (
    BASE_QUALITY_PROMPT,
    BASE_URL,
    DEFAULT_ART_STYLE,
    DEFAULT_SITUATION,
    MIN_DESC_LEN,
    MAX_DESC_LEN,
    _extract_fm_field,
    _extract_fm_tags,
    _validate_description,
    _compose_smart_situation,
    _check_per_source_ttl,
    _auto_fetch_topics,
    _save_as_avif,
    _generate_image_pollinations,
    _load_posts_for_links,
    _load_slug_redirects,
    _save_slug_redirects,
    _get_existing_slugs,
    _resolve_slug_collision,
    _get_body_after_fm,
    _extract_faq_pairs,
    _extract_speakable_text,
    _is_valid_kemono_combination,
    _randomize_kemono_params,
    _build_kemono_tags,
    _kemono_affiliate_keywords,
    CHAR_TYPE_WEIGHTS,
    WORLD_SETTING_WEIGHTS,
    _KEMONO_WORLD_TAGS,
    _KEMONO_EXTRA_TAGS,
    _KEMONO_RELATIONSHIP_AFFILIATE,
    TRANSFORM_WEIGHTS,
    RELATIONSHIP_WEIGHTS,
    EXTRA_SETTING_WEIGHTS,
    CHAR_COUNT_WEIGHTS,
    generate_and_save_image,
    extract_character_prompts,
    extract_image_prompt,
    extract_art_style,
    compose_image_prompt,
    get_existing_posts,
    inject_internal_links,
    process_inline_affiliates,
    process_inline_products,
    validate_and_fix_frontmatter,
    _save_draft_metadata,
    DRAFTS_DIR,
    _cleanup_old_logs,
    LOG_CLEANUP_DIRS,
    _rakuten_search,
    _generate_rakuten_card,
    _rakuten_is_relevant,
    _rakuten_first_phrase,
    _rakuten_api_keywords,
    _rakuten_collect,
    _find_table_end_line,
    _rakuten_load_cache,
    _rakuten_save_cache,
    RAKUTEN_CACHE_FILE,
)


# --------------------------------------------------
# Fixtures
# --------------------------------------------------

@pytest.fixture
def sample_frontmatter():
    """Valid frontmatter with all common fields."""
    return """---
title: "Test Article Title"
description: "This is a test description for the article that is long enough."
tags: [Tech, AI, Python]
prompt_type: "default"
slug: "test-article-slug"
character_1: "A blue dragon with white scales"
character_2: "A red fox with green eyes"
image_prompt: "dragon and fox sitting together"
art_style: "watercolor style"
---
# Test Article

This is the body content.
"""


@pytest.fixture
def sample_frontmatter_minimal():
    """Minimal valid frontmatter."""
    return """---
title: "Minimal Title"
description: "Short desc."
tags: [Tech]
---
# Minimal Article

Body text here.
"""


@pytest.fixture
def sample_frontmatter_story():
    """Story-type frontmatter."""
    return """---
title: "Story Title"
description: "A story about dragons."
tags: [kemono_story]
prompt_type: "kemono_story"
---
# Story

Story content here.
"""


@pytest.fixture
def sample_content_characters():
    """Content with character prompts in frontmatter."""
    return """---
title: "Character Article"
character_1: "A blue dragon with white scales, sitting at desk"
character_2: "A red fox with green eyes, standing nearby"
---
# Character Article

Content with characters.
"""


@pytest.fixture
def sample_content_with_image_prompt():
    """Content with image_prompt field."""
    return """---
title: "Image Article"
image_prompt: "custom scene with mountains"
---
# Image Article

Content here.
"""


@pytest.fixture
def sample_content_with_art_style():
    """Content with art_style field."""
    return """---
title: "Art Style Article"
art_style: "oil painting style"
---
# Art Style Article

Content here.
"""


@pytest.fixture
def sample_content_no_image():
    """Content without image_prompt or characters."""
    return """---
title: "No Image Article"
description: "A technical article about Python."
tags: [Python, Tech]
---
# No Image Article

Content here.
"""


# --------------------------------------------------
# _extract_fm_field tests
# --------------------------------------------------

class TestExtractFmField:
    def test_extract_title(self, sample_frontmatter):
        result = _extract_fm_field(sample_frontmatter, "title")
        assert result == "Test Article Title"

    def test_extract_description(self, sample_frontmatter):
        result = _extract_fm_field(sample_frontmatter, "description")
        assert result == "This is a test description for the article that is long enough."

    def test_extract_prompt_type(self, sample_frontmatter):
        result = _extract_fm_field(sample_frontmatter, "prompt_type")
        assert result == "default"

    def test_extract_slug(self, sample_frontmatter):
        result = _extract_fm_field(sample_frontmatter, "slug")
        assert result == "test-article-slug"

    def test_extract_character_1(self, sample_frontmatter):
        result = _extract_fm_field(sample_frontmatter, "character_1")
        assert result == "A blue dragon with white scales"

    def test_extract_missing_field(self, sample_frontmatter):
        result = _extract_fm_field(sample_frontmatter, "missing_field")
        assert result == ""

    def test_extract_unquoted_field(self):
        content = '---\ntitle: Unquoted Title\n---'
        result = _extract_fm_field(content, "title")
        assert result == "Unquoted Title"

    def test_extract_single_quoted_field(self):
        content = "---\ntitle: 'Single Quoted Title'\n---"
        result = _extract_fm_field(content, "title")
        assert result == "Single Quoted Title"


# --------------------------------------------------
# _extract_fm_tags tests
# --------------------------------------------------

class TestExtractFmTags:
    def test_extract_tags(self, sample_frontmatter):
        result = _extract_fm_tags(sample_frontmatter)
        assert result == ["Tech", "AI", "Python"]

    def test_extract_single_tag(self, sample_frontmatter_minimal):
        result = _extract_fm_tags(sample_frontmatter_minimal)
        assert result == ["Tech"]

    def test_extract_no_tags(self):
        content = '---\ntitle: "No Tags"\n---'
        result = _extract_fm_tags(content)
        assert result == []

    def test_extract_tags_with_spaces(self):
        content = '---\ntags: [ Tech , AI , Python ]\n---'
        result = _extract_fm_tags(content)
        assert result == ["Tech", "AI", "Python"]


# --------------------------------------------------
# _validate_description tests
# --------------------------------------------------

class TestValidateDescription:
    def test_description_in_range(self):
        desc = "A" * 100
        result = _validate_description(desc)
        assert result == desc

    def test_description_too_long(self):
        desc = "A" * 200
        result = _validate_description(desc)
        assert len(result) <= MAX_DESC_LEN
        assert result.endswith("...")

    def test_description_too_short_no_content(self):
        desc = "Short"
        result = _validate_description(desc, "")
        assert result == desc

    def test_description_empty(self):
        result = _validate_description("")
        assert result == ""

    def test_description_none(self):
        result = _validate_description(None)
        assert result is None

    def test_description_min_length(self):
        desc = "A" * MIN_DESC_LEN
        result = _validate_description(desc)
        assert result == desc

    def test_description_max_length(self):
        desc = "A" * MAX_DESC_LEN
        result = _validate_description(desc)
        assert result == desc


# --------------------------------------------------
# _compose_smart_situation tests
# --------------------------------------------------

class TestComposeSmartSituation:
    def test_story_type_returns_default(self, sample_frontmatter_story):
        result = _compose_smart_situation(sample_frontmatter_story)
        assert result == DEFAULT_SITUATION

    def test_novel_type_returns_default(self):
        content = '---\nprompt_type: "novel"\n---'
        result = _compose_smart_situation(content)
        assert result == DEFAULT_SITUATION

    def test_tech_tag_generates_keywords(self):
        content = """---
title: "Python Tutorial"
description: "Learn Python programming"
tags: [Python, Tech]
---"""
        result = _compose_smart_situation(content)
        assert "python" in result.lower() or "coding" in result.lower()

    def test_ai_tag_generates_keywords(self):
        content = """---
title: "AI News"
tags: [AI]
---"""
        result = _compose_smart_situation(content)
        assert "artificial intelligence" in result.lower() or "neural network" in result.lower()

    def test_no_keywords_returns_default(self):
        content = '---\ntitle: "Something"\n---'
        result = _compose_smart_situation(content)
        # With only a generic title, should return title keywords or default
        assert isinstance(result, str)


# --------------------------------------------------
# extract_character_prompts tests
# --------------------------------------------------

class TestExtractCharacterPrompts:
    def test_extract_two_characters(self, sample_content_characters):
        result = extract_character_prompts(sample_content_characters)
        assert len(result) == 2
        assert "character_1" in result
        assert "character_2" in result

    def test_extract_single_character(self):
        content = """---
title: "Single Character"
character_1: "A blue dragon"
---
# Article

Body.
"""
        result = extract_character_prompts(content)
        assert len(result) == 1
        assert "character_1" in result

    def test_no_characters(self, sample_content_no_image):
        result = extract_character_prompts(sample_content_no_image)
        assert result == {}

    def test_character_prompt_maps_to_one(self):
        content = """---
title: "Article"
character_prompt: "A single character description"
---
# Article

Body.
"""
        result = extract_character_prompts(content)
        assert len(result) == 1
        assert "character_1" in result


# --------------------------------------------------
# extract_image_prompt tests
# --------------------------------------------------

class TestExtractImagePrompt:
    def test_extract_image_prompt(self, sample_content_with_image_prompt):
        result = extract_image_prompt(sample_content_with_image_prompt)
        assert result == "custom scene with mountains"

    def test_no_image_prompt(self, sample_content_no_image):
        result = extract_image_prompt(sample_content_no_image)
        assert result == DEFAULT_SITUATION


# --------------------------------------------------
# extract_art_style tests
# --------------------------------------------------

class TestExtractArtStyle:
    def test_extract_art_style(self, sample_content_with_art_style):
        result = extract_art_style(sample_content_with_art_style)
        assert result == "oil painting style"

    def test_default_art_style(self, sample_content_no_image):
        result = extract_art_style(sample_content_no_image)
        assert result == DEFAULT_ART_STYLE


# --------------------------------------------------
# compose_image_prompt tests
# --------------------------------------------------

class TestComposeImagePrompt:
    def test_compose_with_characters(self):
        characters = {
            "character_1": "A blue dragon",
            "character_2": "A red fox"
        }
        result = compose_image_prompt("[character_1, character_2] sitting together", characters, DEFAULT_ART_STYLE)
        assert BASE_QUALITY_PROMPT in result
        assert "A blue dragon" in result
        assert "A red fox" in result
        assert "sitting together" in result

    def test_compose_without_characters(self):
        result = compose_image_prompt("mountain scene", {}, DEFAULT_ART_STYLE)
        assert BASE_QUALITY_PROMPT in result
        assert "mountain scene" in result
        assert DEFAULT_ART_STYLE in result

    def test_compose_with_custom_art_style(self):
        result = compose_image_prompt("scene", {}, "oil painting style")
        assert "oil painting style" in result

    def test_compose_multi_character_tags(self):
        characters = {
            "character_1": "1boy, a dragon",
            "character_2": "1boy, a fox",
            "character_3": "1boy, a wolf"
        }
        result = compose_image_prompt("[character_1, character_2, character_3] scene", characters, DEFAULT_ART_STYLE)
        assert "3boys" in result

    def test_compose_per_character_expressions(self):
        characters = {
            "character_1": "1boy, blue wolf, golden eyes, white chest fur",
            "character_2": "1boy, black panther, emerald eyes, leather vest",
        }
        result = compose_image_prompt(
            "[character_1: blushing, smile, character_2: frown, narrowed eyes] face-to-face confrontation, dramatic lighting",
            characters, DEFAULT_ART_STYLE
        )
        # 表情/ポーズタグは各キャラ外見の直後にインターリーブ
        assert "2boys, blue wolf, golden eyes, white chest fur, blushing, smile, black panther, emerald eyes, leather vest, frown, narrowed eyes, face-to-face confrontation" in result

    def test_compose_single_character_expression(self):
        characters = {"character_1": "1boy, blue wolf, golden eyes"}
        result = compose_image_prompt("[character_1: teary eyes] quiet evening, moonlight", characters, DEFAULT_ART_STYLE)
        assert "blue wolf, golden eyes, teary eyes, quiet evening, moonlight" in result

    def test_compose_same_expression_dedup(self):
        characters = {
            "character_1": "1boy, blue wolf, golden eyes",
            "character_2": "1boy, black panther, emerald eyes",
        }
        result = compose_image_prompt("[character_1: smile, character_2: smile] peaceful afternoon", characters, DEFAULT_ART_STYLE)
        # 全キャラ同一の表情はキャラブロックの後に1回だけ出力
        assert result.count("smile") == 1
        assert "black panther, emerald eyes, smile, peaceful afternoon" in result

    def test_compose_shared_expression(self):
        characters = {
            "character_1": "1boy, blue wolf, golden eyes",
            "character_2": "1boy, black panther, emerald eyes",
        }
        result = compose_image_prompt("[character_1, character_2, smile] peaceful afternoon, warm lighting", characters, DEFAULT_ART_STYLE)
        # コロンなしの共有形式: 全キャラ共通タグを1回出力
        assert result.count("smile") == 1
        assert "black panther, emerald eyes, smile, peaceful afternoon" in result

    def test_compose_legacy_format_without_expressions(self):
        characters = {
            "character_1": "1boy, blue wolf, golden eyes",
            "character_2": "1boy, black panther, emerald eyes",
        }
        result = compose_image_prompt("[character_1, character_2] sitting together", characters, DEFAULT_ART_STYLE)
        # 旧フォーマット（表情なし）は後方互換
        assert "2boys, blue wolf, golden eyes, black panther, emerald eyes, sitting together" in result


# --------------------------------------------------
# get_existing_posts tests
# --------------------------------------------------

class TestGetExistingPosts:
    def test_parse_existing_post(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        post_file = post_dir / "2024-01-01-test.md"
        post_file.write_text(
            '---\ntitle: "Test Post"\ndescription: "A test"\ntags: [Tech]\n---\n# Test\n\nBody.',
            encoding="utf-8"
        )
        result = get_existing_posts(str(post_dir))
        assert len(result) == 1
        assert result[0]["title"] == "Test Post"

    def test_parse_multiple_posts(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        for i in range(3):
            post_file = post_dir / f"2024-01-0{i+1}-test{i}.md"
            post_file.write_text(
                f'---\ntitle: "Post {i}"\n---\n# Post {i}\n\nBody.',
                encoding="utf-8"
            )
        result = get_existing_posts(str(post_dir))
        assert len(result) == 3

    def test_empty_directory(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        result = get_existing_posts(str(post_dir))
        assert result == []

    def test_non_markdown_file_ignored(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        (post_dir / "readme.txt").write_text("not a post", encoding="utf-8")
        result = get_existing_posts(str(post_dir))
        assert result == []


# --------------------------------------------------
# process_inline_affiliates tests
# --------------------------------------------------

class TestProcessInlineAffiliates:
    def test_replace_affiliate_placeholder_plain_text(self):
        content = 'Check out <!-- AFFILIATE: "Amazon" | "best deals" --> for products.'
        result = process_inline_affiliates(content)
        assert '<!-- AFFILIATE:' not in result
        assert "best deals" in result
        assert "amazon.co.jp" not in result
        assert "rakuten.co.jp" not in result
        assert "[best deals]" not in result

    def test_no_affiliate_placeholder(self):
        content = "No affiliate links here."
        result = process_inline_affiliates(content)
        assert result == content

    def test_multiple_affiliate_placeholders(self):
        content = 'Link1: <!-- AFFILIATE: "Amazon" | "Amazon" --> Link2: <!-- AFFILIATE: "Rakuten" | "Rakuten" -->'
        result = process_inline_affiliates(content)
        assert '<!-- AFFILIATE:' not in result
        assert "amazon.co.jp" not in result
        assert "rakuten.co.jp" not in result
        assert "Amazon" in result
        assert "Rakuten" in result


# --------------------------------------------------
# process_inline_products tests
# --------------------------------------------------

class TestProcessInlineProducts:
    def test_replace_product_placeholder(self):
        with patch("generate_article._rakuten_search", return_value=None):
            content = 'Product: <!-- AFF_PRODUCT: "Noise Cancelling Headphones" -->'
            result = process_inline_products(content)
        assert "amazon.co.jp" in result
        assert "rakuten.co.jp" in result
        assert '<!-- AFF_PRODUCT:' not in result
        assert "[Amazon]" in result
        assert "[楽天]" in result
        assert "product-card" not in result

    def test_no_product_placeholder(self):
        content = "No product links here."
        result = process_inline_products(content)
        assert result == content

    def test_rakuten_card_inserted_after_table(self):
        product = {
            "itemName": "ノートPC 15型",
            "itemPrice": 3000,
            "affiliateUrl": "https://hb.afl.rakuten.co.jp/pc=xxx",
            "imageUrl": "https://img.example.com/a.jpg",
            "reviewCount": 100,
        }
        content = (
            'title: "Test"\n\n'
            '| 商品 | リンク |\n'
            '|---|---|\n'
            '| テスト商品 | <!-- AFF_PRODUCT: "ノートPC" --> |\n'
        )
        with patch("generate_article._rakuten_search", return_value=product) as m:
            result = process_inline_products(content)
        assert m.called
        assert "product-card" in result
        assert "pc-img" in result
        assert "ノートPC 15型" in result
        assert "hb.afl.rakuten.co.jp" in result
        # カードはテーブル行の直後に挿入される
        assert result.index("product-card") > result.rindex("| テスト商品 |")

    def test_rakuten_card_skipped_when_irrelevant(self):
        product = {
            "itemName": "スマホガラスフィルム 3枚セット",
            "itemPrice": 1500,
            "affiliateUrl": "https://hb.afl.rakuten.co.jp/pc=xxx",
            "imageUrl": "https://img.example.com/a.jpg",
            "reviewCount": 100,
        }
        content = (
            'title: "Test"\n\n'
            '| 商品 | リンク |\n'
            '|---|---|\n'
            '| フィルム | <!-- AFF_PRODUCT: "ノートPC" --> |\n'
        )
        with patch("generate_article._rakuten_search", return_value=product) as m:
            result = process_inline_products(content)
        assert m.called
        # 関連性フィルタでカードは挿入されない
        assert "product-card" not in result


# --------------------------------------------------
# _rakuten_search tests (APIはモック、実呼び出し禁止)
# --------------------------------------------------

def _fake_rakuten_response(items):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"Items": items}
    resp.raise_for_status.return_value = None
    return resp


def _item(name="商品", price=1000, url="https://item.rakuten.co.jp/x/", img="https://img.example.com/a.jpg", review=10):
    return {
        "itemName": name,
        "itemPrice": price,
        "itemUrl": url,
        "affiliateUrl": f"https://hb.afl.rakuten.co.jp/pc={url}",
        "mediumImageUrls": [img] if img else [],
        "reviewCount": review,
    }


class TestRakutenSearch:
    def setUp(self):
        import generate_article
        generate_article._rakuten_last_call_time = 0.0

    def _env(self):
        return patch.dict(os.environ, {
            "RAKUTEN_APPLICATION_ID": "app",
            "RAKUTEN_ACCESS_KEY": "key",
            "RAKUTEN_AFFILIATE_ID": "aff",
        })

    def test_success_returns_first_image_product(self):
        with self._env(), \
             patch("generate_article._rakuten_load_cache", return_value={}), \
             patch("generate_article._rakuten_save_cache") as save, \
             patch("generate_article.requests.get", return_value=_fake_rakuten_response([
                 _item(img=""),           # 1件目: 画像なし
                 _item(name="画像付き商品"),  # 2件目: 画像あり
             ])) as g:
            result = _rakuten_search("ノートPC")
        assert g.called
        assert save.called
        assert result["itemName"] == "画像付き商品"
        assert result["imageUrl"] == "https://img.example.com/a.jpg"
        assert "hb.afl.rakuten.co.jp" in result["affiliateUrl"]

    def test_zero_results_returns_none(self):
        with self._env(), \
             patch("generate_article._rakuten_load_cache", return_value={}), \
             patch("generate_article._rakuten_save_cache"), \
             patch("generate_article.requests.get", return_value=_fake_rakuten_response([])):
            result = _rakuten_search("存在しない商品")
        assert result is None

    def test_credentials_missing_returns_none(self):
        with patch.dict(os.environ, {
            "RAKUTEN_APPLICATION_ID": "",
            "RAKUTEN_ACCESS_KEY": "",
        }), \
             patch("generate_article._rakuten_load_cache", return_value={}), \
             patch("generate_article.requests.get") as g:
            result = _rakuten_search("ノートPC")
        assert result is None
        assert not g.called

    def test_cache_hit_no_api_call(self):
        from datetime import datetime, timezone, timedelta
        cached_at = datetime.now(timezone.utc).isoformat()
        cache = {"ノートPC": {"fetched_at": cached_at, "product": _item(name="キャッシュ商品"), "hits": 3}}
        with self._env(), \
             patch("generate_article._rakuten_load_cache", return_value=cache), \
             patch("generate_article.requests.get") as g:
            result = _rakuten_search("ノートPC")
        assert not g.called
        assert result["itemName"] == "キャッシュ商品"

    def test_429_retry_then_success(self):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        with self._env(), \
             patch("generate_article._rakuten_load_cache", return_value={}), \
             patch("generate_article._rakuten_save_cache"), \
             patch("generate_article.time.sleep"), \
             patch("generate_article.requests.get", side_effect=[resp_429, _fake_rakuten_response([_item()])]) as g:
            result = _rakuten_search("ノートPC")
        assert g.call_count == 2
        assert result["itemName"] == "商品"

    def test_api_error_returns_none(self):
        import requests as _rq
        with self._env(), \
             patch("generate_article._rakuten_load_cache", return_value={}), \
             patch("generate_article.time.sleep"), \
             patch("generate_article.requests.get", side_effect=_rq.exceptions.ConnectionError("boom")):
            result = _rakuten_search("ノートPC")
        assert result is None


class TestRakutenIsRelevant:
    def test_kemono_generic_keyword_core_token_pass(self):
        assert _rakuten_is_relevant("ケモノ娘 ペンケース", "ケモノ", "kemono_story")
        assert _rakuten_is_relevant("アニマル スリッパ", "動物", "kemono_story")
        assert _rakuten_is_relevant("獣人 ぬいぐるみ", "獣人", "kemono_story")

    def test_kemono_generic_keyword_no_core_token_fail(self):
        assert not _rakuten_is_relevant("シューファンタジー ポンプス", "ケモノ", "kemono_story")
        assert not _rakuten_is_relevant("花百合 浴衣", "動物", "kemono_story")
        assert not _rakuten_is_relevant("SF-3521 ガラスフィルム", "獣人", "kemono_story")

    def test_kemono_genre_keyword_core_token(self):
        assert _rakuten_is_relevant("ケモノ 制服 コスプレ", "ケモノ 制服", "kemono_story")
        assert not _rakuten_is_relevant("制服 コスプレ", "ケモノ 制服", "kemono_story")

    def test_non_kemono_keyword_token_containment(self):
        assert _rakuten_is_relevant("ノートPC 15型", "ノートPC", "default")
        assert _rakuten_is_relevant("Python 実践プログラミング", "Python 本", "default")
        assert not _rakuten_is_relevant("ガラスフィルム 3枚", "ノートPC", "default")

    def test_non_kemono_english_name_in_name(self):
        assert _rakuten_is_relevant("Anthro Beast pen case", "Anthro pen case", "default")

    def test_kemono_name_with_token_passes_as_gemini_name(self):
        # Gemini商品名（kemono_story）: 実語トークン包含で判定
        assert _rakuten_is_relevant("ケモノ娘 ポンチョ", "ケモノ娘 ポンチョ", "kemono_story")


class TestRakutenFirstPhrase:
    def test_english_name_first_token(self):
        assert _rakuten_first_phrase("Anthro Beast Pen Case") == "Anthro"

    def test_short_first_token_extends(self):
        assert _rakuten_first_phrase("A Cat Tail") == "A Cat"

    def test_japanese_delimiter_suffix(self):
        # 用的/向け/用/的 で区切られて先頭部分を採用
        assert _rakuten_first_phrase("ケモノ娘用のポンチョ") == "ケモノ娘"
        assert _rakuten_first_phrase("ケモノ向けぬいぐるみ") == "ケモノ"
        assert _rakuten_first_phrase("ケモノ用ポンチョ") == "ケモノ"

    def test_single_hiragana_not_split(self):
        # 平仮名1文字は区切りにならない（単語内での使用を避ける）
        assert _rakuten_first_phrase("獣人村の生活指南書") == ""
        assert _rakuten_first_phrase("にゃんこケモノぬいぐるみ") == ""

    def test_english_title_token_kept(self):
        # 作品名である「BNA」はそのまま採用
        assert _rakuten_first_phrase("BNA 完全アニメ画集") == "BNA"

    def test_unsplittable_name_skipped(self):
        # 区切れない1語は商品名と重複するためスキップ
        assert _rakuten_first_phrase("百合ケモノ恋愛小説") == ""
        assert _rakuten_first_phrase("ケモノキャラ図鑑") == ""

    def test_empty(self):
        assert _rakuten_first_phrase("") == ""


class TestRakutenApiKeywords:
    def test_kemono_cascade_order(self):
        kws = _rakuten_api_keywords(
            gemini_products=["ケモノ娘 ポンチョ"],
            base_keywords=["ケモノ コスプレ"],
            prompt_type="kemono_story",
            kemono_params={"world_tags": ["獣人村"], "relationship_key": "hetero"},
        )
        assert kws[0] == "ケモノ娘 ポンチョ"
        # 先頭句は完全一致で重複するため除外される
        assert "ケモノ娘用のポ" not in kws
        assert kws.index("ケモノ 獣人村") == 2
        # アンカーキーワードは末尾に並ぶ
        assert kws[-3:] == ["ケモノ", "獣人", "動物"]

    def test_english_only_name_excluded(self):
        kws = _rakuten_api_keywords(
            gemini_products=["Beast Mode Hoodie"],
            base_keywords=[],
            prompt_type="kemono_story",
            kemono_params={},
        )
        assert "Beast Mode Hoodie" not in kws

    def test_non_kemono_uses_base_keywords(self):
        kws = _rakuten_api_keywords(
            gemini_products=["ノートPC 15型"],
            base_keywords=["ノートPC 高性能"],
            prompt_type="default",
            kemono_params=None,
        )
        assert kws == ["ノートPC 15型", "ノートPC", "ノートPC 高性能"]

    def test_dedup_preserves_order(self):
        kws = _rakuten_api_keywords(
            gemini_products=["ケモノ ポンチョ", "ケモノ"],
            base_keywords=[],
            prompt_type="kemono_story",
            kemono_params={"world_tags": ["ポンチョ"], "relationship_key": ""},
        )
        assert kws.count("ケモノ") == 1


class TestRakutenCollect:
    def test_stops_at_max_products(self):
        products = {
            "ケモノ": _item(name="ケモノ ぬいぐるみ"),
            "獣人": _item(name="獣人 フィギュア", url="https://item.rakuten.co.jp/y/"),
            "動物": _item(name="動物 置物", url="https://item.rakuten.co.jp/z/"),
        }
        with patch("generate_article._rakuten_search", side_effect=lambda kw: products.get(kw)) as m:
            collected = _rakuten_collect(["ケモノ", "獣人", "動物"], "kemono_story", max_products=2)
        assert len(collected) == 2
        assert m.call_count == 2
        assert collected[0][0] == "ケモノ"

    def test_skips_irrelevant_and_continues(self):
        products = {
            "ケモノ": _item(name="靴下 3足セット", url="https://item.rakuten.co.jp/a/"),
            "獣人": _item(name="獣人 ぬいぐるみ", url="https://item.rakuten.co.jp/b/"),
        }
        with patch("generate_article._rakuten_search", side_effect=lambda kw: products.get(kw)):
            collected = _rakuten_collect(["ケモノ", "獣人"], "kemono_story", max_products=3)
        assert len(collected) == 1
        assert collected[0][0] == "獣人"

    def test_dedup_by_affiliate_url(self):
        same = _item(name="ケモノ ぬいぐるみ", url="https://item.rakuten.co.jp/dup/")
        with patch("generate_article._rakuten_search", return_value=same):
            collected = _rakuten_collect(["ケモノ", "獣人", "動物"], "kemono_story", max_products=3)
        assert len(collected) == 1

    def test_empty_results(self):
        with patch("generate_article._rakuten_search", return_value=None):
            collected = _rakuten_collect(["ケモノ"], "kemono_story", max_products=3)
        assert collected == []


class TestGenerateRakutenCard:
    def test_card_html_structure(self):
        product = {
            "itemName": "ノートPC 15型",
            "itemPrice": 99800,
            "affiliateUrl": "https://hb.afl.rakuten.co.jp/pc=abc",
            "imageUrl": "https://img.example.com/pc.jpg",
            "reviewCount": 500,
        }
        html = _generate_rakuten_card(product, "ノートPC", "テスト記事タイトル")
        assert 'class="product-card"' in html
        assert 'class="pc-img"' in html
        assert "https://img.example.com/pc.jpg" in html
        assert "ノートPC 15型" in html
        assert "¥99,800" in html
        assert "hb.afl.rakuten.co.jp/pc=abc" in html
        assert "amazon.co.jp/s?k=" in html

    def test_find_table_end_line(self):
        content = "intro\n| a | b |\n|---|---|\n| 1 | 2 |\nafter"
        # 行: 0=intro, 1=| a | b |, 2=|---|---|, 3=| 1 | 2 |, 4=after
        assert _find_table_end_line(content, "| 1 | 2 |") == 3
        # marker行以降がテーブル行でなければその行を返す
        assert _find_table_end_line("a\n| x | y |", "| x | y |") == 1
        assert _find_table_end_line(content, "nonexistent") is None


# --------------------------------------------------
# validate_and_fix_frontmatter tests
# --------------------------------------------------

class TestValidateAndFixFrontmatter:
    def test_valid_frontmatter_unchanged(self, sample_frontmatter):
        result = validate_and_fix_frontmatter(sample_frontmatter)
        assert result == sample_frontmatter

    def test_no_frontmatter_unchanged(self):
        content = "# Just a title\n\nNo frontmatter here."
        result = validate_and_fix_frontmatter(content)
        assert result == content

    def test_corrupted_product_recommendations_fixed(self, capsys):
        content = """---
title: "Test"
description: "Test desc"
product_recommendations:
  - name: "Product"
    broken: {invalid yaml
---
# Test

Body.
"""
        result = validate_and_fix_frontmatter(content)
        assert "product_recommendations" not in result
        captured = capsys.readouterr()
        assert "修復" in captured.out or "WARN" in captured.out

    def test_corrupted_indent_fixed(self, capsys):
        content = """---
title: "Test"
description: "Test desc"
  orphaned_line: "bad"
---
# Test

Body.
"""
        result = validate_and_fix_frontmatter(content)
        assert "orphaned_line" not in result


# --------------------------------------------------
# _check_per_source_ttl tests
# --------------------------------------------------

class TestCheckPerSourceTTL:
    """Per-source TTL 検証のテスト"""

    def _make_data(self, sources_dict, ttl_hours=24):
        return {
            "ttl_hours": ttl_hours,
            "sources": sources_dict,
            "by_category": {},
        }

    def test_fresh_source_not_expired(self):
        """直近に取得した source は期限切れにならない"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        now = datetime.now(JST).isoformat()
        data = self._make_data({
            "hackernews": {
                "fetched_at": now,
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is False

    def test_expired_source(self):
        """TTL を超えた source は期限切れとみなされる"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        old = (datetime.now(JST) - timedelta(hours=25)).isoformat()
        data = self._make_data({
            "hackernews": {
                "fetched_at": old,
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is True

    def test_source_not_matching_category_not_checked(self):
        """リクエストカテゴリと一致しない source（他カテゴリ専属）は対象外（期限切れ扱いしない）"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        old = (datetime.now(JST) - timedelta(hours=48)).isoformat()
        data = self._make_data({
            "reddit": {
                "fetched_at": old,
                "topics": [{"title": "T", "category": "kemono", "source": "reddit"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["reddit"] is False  # 他カテゴリ専属 → 自動fetch のトリガーにしない

    def test_other_category_source_mixed_with_fresh_in_scope(self):
        """他カテゴリ専属 source と対象内 source が混在する場合、他カテゴリ側は False"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        now = datetime.now(JST).isoformat()
        old = (datetime.now(JST) - timedelta(hours=48)).isoformat()
        data = self._make_data({
            "hackernews": {
                "fetched_at": now,
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            },
            "pokemon_blog": {
                "fetched_at": old,
                "topics": [{"title": "T", "category": "pokemon", "source": "pokemon_blog"}],
            },
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is False
        assert result["pokemon_blog"] is False  # 他カテゴリ → スキップ

    def test_zero_topic_source_still_expired(self):
        """トピック 0 件の source は従来どおり期限切れ（完全失敗の自愈を保持）"""
        data = self._make_data({
            "broken_source": {
                "fetched_at": "2026-10-10T00:00:00+09:00",
                "topics": [],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["broken_source"] is True

    def test_missing_fetched_at_is_expired(self):
        """fetched_at が空の source は期限切れ"""
        data = self._make_data({
            "hackernews": {
                "fetched_at": "",
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is True

    def test_invalid_fetched_at_is_expired(self):
        """fetched_at が無効な形式の source は期限切れ"""
        data = self._make_data({
            "hackernews": {
                "fetched_at": "not-a-date",
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is True

    def test_custom_ttl_hours(self):
        """ttl_hours でカスタム TTL が適用される"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        mid = (datetime.now(JST) - timedelta(hours=12)).isoformat()
        data = self._make_data({
            "hackernews": {
                "fetched_at": mid,
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            }
        }, ttl_hours=10)
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is True

    def test_multiple_sources_mixed_expiry(self):
        """複数の source で期限切れが混在する"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        now = datetime.now(JST).isoformat()
        old = (datetime.now(JST) - timedelta(hours=25)).isoformat()
        data = self._make_data({
            "hackernews": {
                "fetched_at": now,
                "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
            },
            "rss_zenn": {
                "fetched_at": old,
                "topics": [{"title": "T", "category": "tech", "source": "rss_zenn"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["hackernews"] is False
        assert result["rss_zenn"] is True


# --------------------------------------------------
# _auto_fetch_topics tests
# --------------------------------------------------

class TestAutoFetchTopics:
    """自動再取得ロジックのテスト"""

    def test_no_fetch_when_data_sufficient(self):
        """カテゴリデータが十分なら自動取得しない"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        now = datetime.now(JST).isoformat()
        data = {
            "ttl_hours": 24,
            "sources": {
                "hackernews": {
                    "fetched_at": now,
                    "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
                }
            },
            "by_category": {
                "tech": [{"title": "T", "category": "tech", "source": "hackernews"}],
            },
        }
        with patch("subprocess.run") as mock_run:
            result = _auto_fetch_topics("default", ["tech"], data)
        assert result is None
        mock_run.assert_not_called()

    def test_fetch_triggered_when_category_empty(self):
        """カテゴリデータが空なら自動取得がトリガーされる"""
        data = {
            "ttl_hours": 24,
            "sources": {},
            "by_category": {"tech": []},
        }
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="完了: 10 件", stderr="")
            with patch("builtins.open", mock_open(read_data=json.dumps({"test": True}))), \
                 patch("generate_article.TOPICS_JSON_PATH", "data/topics/latest.json"):
                result = _auto_fetch_topics("default", ["tech"], data)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "fetch_topics.py" in call_args[0][0][2]
        assert "--prompt-type" in call_args[0][0]
        assert "default" in call_args[0][0]

    def test_fetch_triggered_when_source_expired(self):
        """source が期限切れなら自動取得がトリガーされる"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        old = (datetime.now(JST) - timedelta(hours=25)).isoformat()
        data = {
            "ttl_hours": 24,
            "sources": {
                "hackernews": {
                    "fetched_at": old,
                    "topics": [{"title": "T", "category": "tech", "source": "hackernews"}],
                }
            },
            "by_category": {
                "tech": [{"title": "T", "category": "tech", "source": "hackernews"}],
            },
        }
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="完了: 10 件", stderr="")
            with patch("builtins.open", mock_open(read_data=json.dumps({"test": True}))), \
                 patch("generate_article.TOPICS_JSON_PATH", "data/topics/latest.json"):
                result = _auto_fetch_topics("default", ["tech"], data)
        mock_run.assert_called_once()

    def test_fetch_failure_returns_none(self):
        """自動取得が失敗すると None を返す"""
        data = {
            "ttl_hours": 24,
            "sources": {},
            "by_category": {"tech": []},
        }
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = _auto_fetch_topics("default", ["tech"], data)
        assert result is None

    def test_fetch_timeout_returns_none(self):
        """自動取得がタイムアウトすると None を返す"""
        import subprocess
        data = {
            "ttl_hours": 24,
            "sources": {},
            "by_category": {"tech": []},
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 120)
            result = _auto_fetch_topics("default", ["tech"], data)
        assert result is None


# --------------------------------------------------
# topics パス解決の回帰テスト (2b4a815 の退行防止)
# --------------------------------------------------

class TestTopicsPathResolution:
    """トレンドデータパスと fetch_topics.py 出力パスの一致を保障する"""

    def test_topics_json_path_under_repo_root(self):
        """TOPICS_JSON_PATH はリポジトリ直下 data/topics/latest.json 解決必須"""
        import generate_article
        topics_path = Path(generate_article.TOPICS_JSON_PATH)
        assert tuple(topics_path.parts[-3:]) == ("data", "topics", "latest.json")
        assert "scripts" not in topics_path.parts, f"TOPICS_JSON_PATH が scripts/ 配下: {topics_path}"

    def test_topics_dir_matches_fetch_topics_output(self):
        """generate_article と fetch_topics の TOPICS_DIR が一致する"""
        import generate_article
        import fetch_topics
        assert Path(generate_article.TOPICS_DIR) == Path(fetch_topics.TOPICS_DIR)

    def test_auto_fetch_invokes_scripts_fetch_topics(self):
        """自動再取得は scripts/fetch_topics.py を起動する"""
        import generate_article
        script_path = os.path.join(
            generate_article.PROJECT_DIR, "scripts", "fetch_topics.py"
        )
        assert os.path.exists(script_path)


# --------------------------------------------------
# _save_as_avif tests
# --------------------------------------------------

class TestSaveAsAvif:
    """AVIF変換・保存のテスト"""

    def _create_temp_image(self, tmp_path, mode="RGB"):
        img = Image.new(mode, (100, 100), color=(255, 0, 0))
        path = tmp_path / "test_input.png"
        img.save(str(path))
        return str(path)

    def test_rgb_image_converted_to_avif(self, tmp_path):
        """RGB画像がAVIFに変換されて保存される"""
        img_path = self._create_temp_image(tmp_path, "RGB")
        (tmp_path / "public" / "images").mkdir(parents=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("generate_article.BASE_URL", "/test"):
                result = _save_as_avif(img_path, "test-image.png")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/test-image.avif"
        assert (tmp_path / "public" / "images" / "test-image.avif").exists()

    def test_rgba_image_converted_to_rgb_then_avif(self, tmp_path):
        """RGBA画像はRGBに変換されてからAVIFになる"""
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        img_path = tmp_path / "test_rgba.png"
        img.save(str(img_path))
        (tmp_path / "public" / "images").mkdir(parents=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("generate_article.BASE_URL", "/test"):
                result = _save_as_avif(str(img_path), "rgba-test.png")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/rgba-test.avif"

    def test_output_filename_extension_replaced(self, tmp_path):
        """出力ファイル名の拡張子が.avifに置き換わる"""
        img_path = self._create_temp_image(tmp_path)
        (tmp_path / "public" / "images").mkdir(parents=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("generate_article.BASE_URL", "/test"):
                result = _save_as_avif(img_path, "test-image.jpg")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/test-image.avif"


# --------------------------------------------------
# _generate_image_pollinations tests
# --------------------------------------------------

class TestGenerateImagePollinations:
    """Pollinations.ai 画像生成のテスト"""

    def _fake_jpeg_bytes(self):
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_successful_image_generation(self, tmp_path):
        """Pollinationsから画像が正常に取得・変換される"""
        fake_bytes = self._fake_jpeg_bytes()
        mock_resp = MagicMock()
        mock_resp.content = fake_bytes
        mock_resp.raise_for_status = MagicMock()

        (tmp_path / "public" / "images").mkdir(parents=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("requests.get", return_value=mock_resp), \
                 patch("generate_article.BASE_URL", "/test"):
                result = _generate_image_pollinations("test prompt", "test-file.png")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/test-file.avif"
        assert (tmp_path / "public" / "images" / "test-file.avif").exists()

    def test_request_failure_propagates(self, tmp_path):
        """HTTPエラー時は例外が伝播する"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404")

        (tmp_path / "public" / "images").mkdir(parents=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("requests.get", return_value=mock_resp):
                with pytest.raises(Exception, match="404"):
                    _generate_image_pollinations("test prompt", "test-file.png")
        finally:
            os.chdir(orig_cwd)

    def test_prompt_url_encoded(self, tmp_path):
        """プロンプトがURLエンコードされる"""
        fake_bytes = self._fake_jpeg_bytes()
        mock_resp = MagicMock()
        mock_resp.content = fake_bytes
        mock_resp.raise_for_status = MagicMock()

        (tmp_path / "public" / "images").mkdir(parents=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("requests.get", return_value=mock_resp) as mock_get, \
                 patch("generate_article.BASE_URL", "/test"):
                _generate_image_pollinations("test prompt with spaces & symbols", "out.png")
        finally:
            os.chdir(orig_cwd)

        call_url = mock_get.call_args[0][0]
        assert "test+prompt+with+spaces+%26+symbols" in call_url or "test%20prompt%20with%20spaces%20%26%20symbols" in call_url


# --------------------------------------------------
# generate_and_save_image tests
# --------------------------------------------------

class TestGenerateAndSaveImage:
    """画像生成ルーティングとフォールバックのテスト"""

    def _fake_jpeg_bytes(self):
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_hf_provider_success(self, tmp_path, monkeypatch):
        """HFプロバイダーで正常に画像が生成される"""
        monkeypatch.setattr("generate_article.IMAGE_PROVIDER", "hf")
        monkeypatch.setenv("HF_TOKEN", "test-token")

        temp_img = tmp_path / "hf_temp.png"
        temp_img.write_bytes(self._fake_jpeg_bytes())
        (tmp_path / "public" / "images").mkdir(parents=True)

        mock_client = MagicMock()
        mock_client.predict.return_value = str(temp_img)

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("generate_article.Client", return_value=mock_client), \
                 patch("generate_article.BASE_URL", "/test"):
                result = generate_and_save_image("test prompt", "out.png")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/out.avif"
        mock_client.predict.assert_called_once()

    def test_hf_failure_fallback_to_pollinations(self, tmp_path, monkeypatch):
        """HF失敗後にPollinationsにフォールバックする"""
        monkeypatch.setattr("generate_article.IMAGE_PROVIDER", "hf")
        monkeypatch.setenv("HF_TOKEN", "test-token")

        fake_bytes = self._fake_jpeg_bytes()
        mock_poll_resp = MagicMock()
        mock_poll_resp.content = fake_bytes
        mock_poll_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.predict.side_effect = Exception("HF error")
        (tmp_path / "public" / "images").mkdir(parents=True)

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("generate_article.Client", return_value=mock_client), \
                 patch("requests.get", return_value=mock_poll_resp), \
                 patch("time.sleep", return_value=None), \
                 patch("generate_article.BASE_URL", "/test"):
                result = generate_and_save_image("test prompt", "out.png")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/out.avif"
        assert mock_client.predict.call_count == 2

    def test_hf_and_pollinations_both_fail(self, tmp_path, monkeypatch):
        """HFとPollinationsの両方が失敗すると空文字列を返す"""
        monkeypatch.setattr("generate_article.IMAGE_PROVIDER", "hf")
        monkeypatch.setenv("HF_TOKEN", "test-token")

        mock_poll_resp = MagicMock()
        mock_poll_resp.raise_for_status.side_effect = Exception("Pollinations error")

        mock_client = MagicMock()
        mock_client.predict.side_effect = Exception("HF error")
        (tmp_path / "public" / "images").mkdir(parents=True)

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("generate_article.Client", return_value=mock_client), \
                 patch("requests.get", return_value=mock_poll_resp), \
                 patch("time.sleep", return_value=None):
                result = generate_and_save_image("test prompt", "out.png")
        finally:
            os.chdir(orig_cwd)

        assert result == ""

    def test_pollinations_provider_direct(self, tmp_path, monkeypatch):
        """IMAGE_PROVIDER=pollinationsの場合はHFをスキップ"""
        monkeypatch.setattr("generate_article.IMAGE_PROVIDER", "pollinations")

        fake_bytes = self._fake_jpeg_bytes()
        mock_resp = MagicMock()
        mock_resp.content = fake_bytes
        mock_resp.raise_for_status = MagicMock()
        (tmp_path / "public" / "images").mkdir(parents=True)

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("requests.get", return_value=mock_resp), \
                 patch("generate_article.Client") as mock_client_cls, \
                 patch("generate_article.BASE_URL", "/test"):
                result = generate_and_save_image("test prompt", "out.png")
        finally:
            os.chdir(orig_cwd)

        assert result == "/test/images/out.avif"
        mock_client_cls.assert_not_called()

    def test_pollinations_provider_only_fails(self, tmp_path, monkeypatch):
        """IMAGE_PROVIDER=pollinationsでPollinationsも失敗すると空文字列"""
        monkeypatch.setattr("generate_article.IMAGE_PROVIDER", "pollinations")

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("error")
        (tmp_path / "public" / "images").mkdir(parents=True)

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch("requests.get", return_value=mock_resp):
                result = generate_and_save_image("test prompt", "out.png")
        finally:
            os.chdir(orig_cwd)

        assert result == ""


# --------------------------------------------------
# _load_posts_for_links tests
# --------------------------------------------------

class TestLoadPostsForLinks:
    def test_load_posts_with_slug(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        (post_dir / "2024-01-01-test.md").write_text(
            '---\ntitle: "Test Post"\nslug: "test-post"\ntags: [Tech]\n---\n# Test\n\nBody.',
            encoding="utf-8"
        )
        result = _load_posts_for_links(str(post_dir))
        assert len(result) == 1
        assert result[0]["title"] == "Test Post"
        assert result[0]["slug"] == "test-post"
        assert result[0]["tags"] == ["Tech"]

    def test_load_posts_slug_from_filename(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        (post_dir / "2024-01-01-auto-post.md").write_text(
            '---\ntitle: "No Slug Post"\n---\n# Post\n\nBody.',
            encoding="utf-8"
        )
        result = _load_posts_for_links(str(post_dir))
        assert len(result) == 1
        assert result[0]["slug"] == "2024-01-01"

    def test_load_posts_empty_dir(self, tmp_path):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        result = _load_posts_for_links(str(post_dir))
        assert result == []

    def test_load_posts_no_dir(self):
        result = _load_posts_for_links("/nonexistent/path")
        assert result == []


# --------------------------------------------------
# inject_internal_links tests
# --------------------------------------------------

class TestInjectInternalLinks:
    def _create_posts(self, tmp_path, posts_data):
        post_dir = tmp_path / "posts"
        post_dir.mkdir()
        for i, p in enumerate(posts_data):
            fpath = post_dir / f"2024-01-0{i+1}-auto-post.md"
            tags_str = ", ".join(p.get("tags", []))
            content = f'---\ntitle: "{p["title"]}"\nslug: "{p["slug"]}"\ntags: [{tags_str}]\n---\n# {p["title"]}\n\nBody.'
            fpath.write_text(content, encoding="utf-8")
        return str(post_dir)

    def test_basic_title_match(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "Python Tutorial", "slug": "python-tutorial", "tags": ["Tech"]},
        ])
        content = """---
title: "New Article"
---
# New Article

I recommend reading Python Tutorial for beginners.

See also Python Tutorial for advanced users.
"""
        result = inject_internal_links(content, posts_dir)
        expected_link = f"[Python Tutorial]({BASE_URL}/posts/python-tutorial)"
        assert result.count(expected_link) == 2

    def test_no_match_unchanged(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "Python Tutorial", "slug": "python-tutorial", "tags": ["Tech"]},
        ])
        content = """---
title: "New Article"
---
# New Article

This article has no references to other posts.
"""
        result = inject_internal_links(content, posts_dir)
        assert result == content

    def test_skips_text_inside_existing_link(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "Python Tutorial", "slug": "python-tutorial", "tags": ["Tech"]},
        ])
        content = """---
title: "New Article"
---
# New Article

See [Python Tutorial](https://example.com) for more.
Also check Python Tutorial locally.
"""
        result = inject_internal_links(content, posts_dir)
        assert "[Python Tutorial](https://example.com)" in result
        expected_link = f"[Python Tutorial]({BASE_URL}/posts/python-tutorial)"
        assert result.count(expected_link) == 1

    def test_respects_max_links(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "Python Tutorial", "slug": "python-tutorial", "tags": ["Tech"]},
        ])
        content = """---
title: "New Article"
---
# New Article

Python Tutorial is great. Python Tutorial is useful. Python Tutorial is recommended.
"""
        result = inject_internal_links(content, posts_dir, max_links=2)
        expected_link = f"[Python Tutorial]({BASE_URL}/posts/python-tutorial)"
        assert result.count(expected_link) == 2

    def test_preserves_frontmatter(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "Python Tutorial", "slug": "python-tutorial", "tags": ["Tech"]},
        ])
        content = """---
title: "New Article"
description: "A test article"
tags: [Tech]
---
# New Article

Read Python Tutorial first.
"""
        result = inject_internal_links(content, posts_dir)
        assert 'title: "New Article"' in result
        assert 'description: "A test article"' in result

    def test_no_posts_returns_unchanged(self, tmp_path):
        content = """---
title: "New Article"
---
# New Article

Some text here.
"""
        result = inject_internal_links(content, str(tmp_path / "nonexistent"))
        assert result == content

    def test_skips_short_titles(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "AB", "slug": "ab", "tags": []},
            {"title": "Valid Title", "slug": "valid-title", "tags": []},
        ])
        content = """---
title: "New Article"
---
# New Article

AB is short. Valid Title is long enough.
"""
        result = inject_internal_links(content, posts_dir)
        assert "AB" in result and "[AB](" not in result
        expected_link = f"[Valid Title]({BASE_URL}/posts/valid-title)"
        assert expected_link in result

    def test_skips_text_in_image_syntax(self, tmp_path):
        posts_dir = self._create_posts(tmp_path, [
            {"title": "Dragon Art", "slug": "dragon-art", "tags": []},
        ])
        content = """---
title: "New Article"
---
# New Article

![Dragon Art](/images/dragon.avif)
Check Dragon Art for details.
"""
        result = inject_internal_links(content, posts_dir)
        assert "![Dragon Art](/images/dragon.avif)" in result
        expected_link = f"[Dragon Art]({BASE_URL}/posts/dragon-art)"
        assert result.count(expected_link) == 1


class TestSlugRedirects:
    """Tests for slug redirect tracking and collision resolution."""

    def test_load_redirects_empty_file(self, tmp_path):
        f = tmp_path / "slug-redirects.json"
        f.write_text("{}")
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            result = _load_slug_redirects()
        assert result == {}

    def test_load_redirects_missing_file(self, tmp_path):
        f = tmp_path / "nonexistent.json"
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            result = _load_slug_redirects()
        assert result == {}

    def test_load_redirects_with_data(self, tmp_path):
        f = tmp_path / "slug-redirects.json"
        f.write_text(json.dumps({"old-slug": "new-slug"}))
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            result = _load_slug_redirects()
        assert result == {"old-slug": "new-slug"}

    def test_load_redirects_invalid_json(self, tmp_path):
        f = tmp_path / "slug-redirects.json"
        f.write_text("{invalid json}")
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            result = _load_slug_redirects()
        assert result == {}

    def test_save_redirects(self, tmp_path):
        f = tmp_path / "slug-redirects.json"
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            _save_slug_redirects({"a": "b"})
        assert json.loads(f.read_text()) == {"a": "b"}

    def test_get_existing_slugs_empty(self, tmp_path):
        result = _get_existing_slugs(str(tmp_path))
        assert result == set()

    def test_get_existing_slugs_no_dir(self):
        result = _get_existing_slugs("/nonexistent/path")
        assert result == set()

    def test_get_existing_slugs_with_posts(self, tmp_path):
        (tmp_path / "post1.md").write_text('---\ntitle: "Post 1"\nslug: "post-one"\n---')
        (tmp_path / "post2.md").write_text('---\ntitle: "Post 2"\nslug: "post-two"\n---')
        result = _get_existing_slugs(str(tmp_path))
        assert result == {"post-one", "post-two"}

    def test_resolve_no_collision(self):
        slug, changed = _resolve_slug_collision("unique-slug", set())
        assert slug == "unique-slug"
        assert changed is False

    def test_resolve_collision_first(self, tmp_path):
        f = tmp_path / "slug-redirects.json"
        f.write_text("{}")
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            slug, changed = _resolve_slug_collision("duplicate", {"duplicate"})
        assert slug == "duplicate-2"
        assert changed is True
        assert json.loads(f.read_text()) == {"duplicate": "duplicate-2"}

    def test_resolve_collision_multiple(self, tmp_path):
        f = tmp_path / "slug-redirects.json"
        f.write_text("{}")
        with patch("generate_article.SLUG_REDIRECTS_FILE", str(f)):
            slug, changed = _resolve_slug_collision("dup", {"dup", "dup-2", "dup-3"})
        assert slug == "dup-4"


class TestExtractFaqPairs:
    """Tests for _extract_faq_pairs() - FAQPage schema extraction"""

    def test_extract_qa_blocks_basic(self):
        content = """---
title: "Test"
---
Some intro text.

Q: 質問1は何ですか？
A: 回答1です。これは詳細な説明です。

Q: 質問2は何ですか？
A: 回答2です。これも詳細な説明です。
"""
        pairs = _extract_faq_pairs(content)
        assert len(pairs) == 2
        assert pairs[0]["question"] == "質問1は何ですか"
        assert "回答1" in pairs[0]["answer"]
        assert pairs[1]["question"] == "質問2は何ですか"
        assert "回答2" in pairs[1]["answer"]

    def test_extract_qa_blocks_english(self):
        content = """---
title: "Test"
---
Intro.

Q: What is AI?
A: Artificial Intelligence is a field of computer science.

Q: How does it work?
A: It uses machine learning algorithms to process data.
"""
        pairs = _extract_faq_pairs(content)
        assert len(pairs) == 2
        assert pairs[0]["question"] == "What is AI?"
        assert "Artificial Intelligence" in pairs[0]["answer"]

    def test_extract_heading_questions(self):
        content = """---
title: "Test"
---
Intro paragraph.

## 質問1は何ですか？

これは質問1に対する回答です。十分な長さのテキストです。

## 質問2は何ですか？

これは質問2に対する回答です。十分な長さのテキストです。
"""
        pairs = _extract_faq_pairs(content)
        assert len(pairs) >= 1
        assert "質問1" in pairs[0]["question"]

    def test_no_faq_content(self):
        content = """---
title: "Test"
---
This is a regular article without any FAQ content.
Just normal paragraphs here.
"""
        pairs = _extract_faq_pairs(content)
        assert pairs == []

    def test_empty_content(self):
        assert _extract_faq_pairs("") == []

    def test_short_question_filtered(self):
        content = """---
title: "Test"
---
Q: Q?
A: A answer that is long enough to pass the minimum length check.
"""
        pairs = _extract_faq_pairs(content)
        assert len(pairs) == 0

    def test_max_10_pairs(self):
        content = "---\ntitle: \"Test\"\n---\n"
        for i in range(15):
            content += f"\nQ: 質問{i}は何ですか？\nA: 回答{i}です。これは十分な長さのテキストです。\n"
        pairs = _extract_faq_pairs(content)
        assert len(pairs) <= 10


class TestExtractSpeakableText:
    """Tests for _extract_speakable_text() - Speakable schema extraction"""

    def test_extract_first_paragraph(self):
        content = """---
title: "Test"
---
This is the first meaningful paragraph of the article that should be extracted for speakable schema.

Some second paragraph that should not be extracted.
"""
        text = _extract_speakable_text(content)
        assert "first meaningful paragraph" in text

    def test_skip_headings(self):
        content = """---
title: "Test"
---
# Main Heading

## Sub Heading

This is the actual first paragraph of the article content that matters.
"""
        text = _extract_speakable_text(content)
        assert "first paragraph" in text
        assert "Heading" not in text

    def test_skip_image_placeholders(self):
        content = """---
title: "Test"
---
![Image caption here]

This is the first real paragraph after the image placeholder.
"""
        text = _extract_speakable_text(content)
        assert "first real paragraph" in text

    def test_empty_content(self):
        assert _extract_speakable_text("") == ""

    def test_no_body_content(self):
        content = """---
title: "Test"
---
"""
        assert _extract_speakable_text(content) == ""

    def test_max_length_300(self):
        long_text = "A" * 500
        content = f"""---
title: "Test"
---
{long_text}
"""
        text = _extract_speakable_text(content)
        assert len(text) <= 300

    def test_minimum_length_20(self):
        content = """---
title: "Test"
---
Short.

This is a longer paragraph that meets the minimum length requirement for speakable text extraction.
"""
        text = _extract_speakable_text(content)
        assert len(text) >= 20
        assert "longer paragraph" in text

    def test_japanese_text(self):
        content = """---
title: "テスト記事"
---
これは日本語の文章です。十分な長さのテキストとしてSpeakable schemaに抽出されます。テスト用です。

2段落目です。
"""
        text = _extract_speakable_text(content)
        assert "日本語" in text


# --------------------------------------------------
# Kemono Randomization Tests
# --------------------------------------------------
class TestIsValidKemonoCombination:
    def test_clone_hetero_without_tsf_invalid(self):
        assert _is_valid_kemono_combination("none", "hetero", "clone") is False

    def test_clone_hetero_with_tsf_valid(self):
        assert _is_valid_kemono_combination("tsf", "hetero", "clone") is True

    def test_clone_hetero_with_tf_tsf_valid(self):
        assert _is_valid_kemono_combination("tf+tsf", "hetero", "clone") is True

    def test_clone_partnership_valid(self):
        assert _is_valid_kemono_combination("none", "partnership", "clone") is True

    def test_clone_yaoi_valid(self):
        assert _is_valid_kemono_combination("none", "yaoi", "clone") is True

    def test_clone_yuri_valid(self):
        assert _is_valid_kemono_combination("none", "yuri", "clone") is True

    def test_rival_hetero_valid(self):
        assert _is_valid_kemono_combination("none", "hetero", "rival") is True

    def test_none_extra_valid(self):
        assert _is_valid_kemono_combination("none", "hetero", "none") is True

    def test_tf_yuri_clone_valid(self):
        assert _is_valid_kemono_combination("tf", "yuri", "clone") is True


class TestRandomizeKemonoParams:
    def test_return_keys(self):
        params = _randomize_kemono_params()
        expected_keys = {
            "char_types", "world_tags", "extra_tag",
            "char_type", "world_setting_key", "world_setting",
            "transform_key", "transform_text",
            "relationship_key", "relationship_text",
            "extra_key", "extra_text",
            "char_count", "char_count_desc",
        }
        assert set(params.keys()) == expected_keys

    def test_char_types_in_options(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            raw_types = [v[0] for v in CHAR_TYPE_WEIGHTS]
            assert params["char_types"] in raw_types
            # 表示文字列はリストの " / " 結合と一致
            assert params["char_type"] == " / ".join(params["char_types"])

    def test_world_setting_in_options(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["world_setting"] in (
                "ファンタジー", "異世界", "現代", "SF", "スペースオペラ", "日常",
                "サイバーパンク", "冒険", "ダンジョンクライム", "ファンタジーとSF",
                "ミステリー", "歴史",
            )

    def test_world_tags_consistent_with_display(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["world_tags"] == _KEMONO_WORLD_TAGS[params["world_setting_key"]]
            assert params["world_setting"] == "と".join(params["world_tags"])

    def test_extra_tag_consistent_with_display(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["extra_tag"] == _KEMONO_EXTRA_TAGS[params["extra_key"]]
            assert params["extra_text"] == (f"、{params['extra_tag']}" if params["extra_tag"] else "")

    def test_transform_text_in_options(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["transform_text"] in ("", "、TF(変身・変形)", "、TSF（性転換フィクション）", "、TF・TSF")

    def test_relationship_text_in_options(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["relationship_text"] in ("相棒関係", "同性愛（男性同士の恋愛）", "百合（女性同士の恋愛）", "異性愛")

    def test_extra_text_in_options(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["extra_text"] in ("", "、クローンによる自分同士", "、ライバル関係")

    def test_char_count_in_options(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            assert params["char_count"] in (1, 2)
            assert params["char_count_desc"] in ("クローン", "バディ", "ライバル", "カップル")

    def test_char_count_desc_matches_count(self):
        for _ in range(50):
            params = _randomize_kemono_params()
            if params["char_count"] == 1:
                assert params["char_count_desc"] == "クローン"
            else:
                assert params["char_count_desc"] in ("バディ", "ライバル", "カップル")

    def test_combination_always_valid(self):
        for _ in range(200):
            params = _randomize_kemono_params()
            transform = None
            relationship = None
            extra = None
            for k, v in {
                "": "none", "、TF(変身・変形)": "tf", "、TSF（性転換フィクション）": "tsf", "、TF・TSF": "tf+tsf"
            }.items():
                if params["transform_text"] == k:
                    transform = v
            for k, v in {
                "相棒関係": "partnership", "同性愛（男性同士の恋愛）": "yaoi",
                "百合（女性同士の恋愛）": "yuri", "異性愛": "hetero"
            }.items():
                if params["relationship_text"] == k:
                    relationship = v
            for k, v in {
                "": "none", "、クローンによる自分同士": "clone", "、ライバル関係": "rival"
            }.items():
                if params["extra_text"] == k:
                    extra = v
            assert _is_valid_kemono_combination(transform, relationship, extra) is True

    def test_distribution_char_type(self):
        counts = {}
        for _ in range(1000):
            params = _randomize_kemono_params()
            counts[params["char_type"]] = counts.get(params["char_type"], 0) + 1
        for val, count in counts.items():
            pct = count / 10
            assert 5 <= pct <= 40, f"{val}: {pct}%"

    def test_char_count_1_only_with_clone(self):
        for _ in range(200):
            params = _randomize_kemono_params()
            if params["char_count"] == 1:
                assert params["extra_text"] == "、クローンによる自分同士"

    def test_distribution_char_count(self):
        counts = {1: 0, 2: 0}
        for _ in range(1000):
            params = _randomize_kemono_params()
            counts[params["char_count"]] += 1
        assert counts[1] + counts[2] == 1000
        assert 0 < counts[1] < counts[2]


class TestBuildKemonoTags:
    """kemono_params → タグリスト（構造化データ直接使用）。"""

    def _params(self, **overrides):
        base = {
            "char_types": ["獣人", "動物"],
            "world_tags": ["ファンタジー", "SF"],
            "relationship_key": "yaoi",
            "extra_tag": "ライバル関係",
        }
        base.update(overrides)
        return base

    def test_full_order(self):
        tags = _build_kemono_tags(self._params())
        assert tags == ["ケモノ", "獣人", "動物", "ファンタジー", "SF", "BL", "ライバル関係"]

    def test_char_types_split_into_individual_tags(self):
        tags = _build_kemono_tags(self._params(char_types=["動物と獣人のハーフ", "動物"]))
        assert "動物と獣人のハーフ" in tags
        assert "動物" in tags
        # 結合済みタグ（旧バグ）が混入しない
        assert "動物と獣人のハーフ / 動物" not in tags
        assert "動物と獣人のハーフ・動物" not in tags

    def test_world_tags_split_into_individual_tags(self):
        tags = _build_kemono_tags(self._params(world_tags=["ファンタジー", "SF"]))
        assert "ファンタジー" in tags
        assert "SF" in tags
        assert "ファンタジーとSF" not in tags

    def test_extra_tag_has_no_leading_comma(self):
        tags = _build_kemono_tags(self._params(extra_tag="ライバル関係"))
        assert "ライバル関係" in tags
        # 旧バグ: extra_text の「、」接頭がタグに混入
        assert not any(t.startswith("、") for t in tags)

    def test_empty_extra_omitted(self):
        tags = _build_kemono_tags(self._params(extra_tag="", relationship_key="partnership"))
        assert tags == ["ケモノ", "獣人", "動物", "ファンタジー", "SF", "バディ"]

    def test_no_relationship_omitted(self):
        tags = _build_kemono_tags(self._params(relationship_key="", extra_tag=""))
        assert tags == ["ケモノ", "獣人", "動物", "ファンタジー", "SF"]

    def test_single_char_type(self):
        tags = _build_kemono_tags(self._params(char_types=["獣人"], world_tags=["ファンタジー"]))
        assert tags[:3] == ["ケモノ", "獣人", "ファンタジー"]


class TestKemonoAffiliateKeywords:
    """kemono_params → アフィリエイト検索キーワード（world_tags 直接使用）。"""

    def test_cascade_order(self):
        kws = _kemono_affiliate_keywords({
            "world_tags": ["ファンタジー", "SF"],
            "relationship_key": "hetero",
        })
        assert kws == [
            "ケモノ",
            "ファンタジー", "SF",
            "恋愛",
            "ケモノ ファンタジー", "ケモノ SF",
            "ケモノ 恋愛",
        ]

    def test_no_relationship(self):
        kws = _kemono_affiliate_keywords({
            "world_tags": ["SF"],
            "relationship_key": "",
        })
        assert kws == ["ケモノ", "SF", "ケモノ SF"]

    def test_world_tags_not_split_by_to(self):
        # 旧実装は world_setting を「と」で分割していた。world_tags はそのまま使用
        kws = _kemono_affiliate_keywords({
            "world_tags": ["ファンタジー", "SF"],
            "relationship_key": "yaoi",
        })
        assert "ファンタジーとSF" not in kws
        assert kws.index("ケモノ ファンタジー") < kws.index("ケモノ SF")


class TestSaveDraftMetadata:
    """Test 2-pass draft metadata tracking."""

    def test_saves_json_file(self, tmp_path):
        with patch("generate_article.DRAFTS_DIR", str(tmp_path / "drafts")):
            _save_draft_metadata(
                file_timestamp="2026-10-06-120000",
                prompt_type="kemono_story",
                article_filename="2026-10-06-120000-auto-post.md",
                draft_content="---\ntitle: Test\n---\n\nDraft content here.",
                refined_content="---\ntitle: Test\n---\n\nRefined and better content.",
                pass1_model="gemini-3.8-flash",
                pass1_duration=12.5,
                pass2_model="gemini-3.8-flash",
                pass2_duration=10.2,
            )

            json_file = tmp_path / "drafts" / "2026-10-06-120000.json"
            assert json_file.exists()

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["timestamp"] == "2026-10-06-120000"
            assert data["prompt_type"] == "kemono_story"
            assert data["article_file"] == "2026-10-06-120000-auto-post.md"

    def test_records_pass1_info(self, tmp_path):
        with patch("generate_article.DRAFTS_DIR", str(tmp_path / "drafts")):
            _save_draft_metadata(
                file_timestamp="2026-10-06-120000",
                prompt_type="default",
                article_filename="2026-10-06-120000-auto-post.md",
                draft_content="Draft text content.",
                refined_content="Refined text content that is longer.",
                pass1_model="gemini-3.6-flash",
                pass1_duration=8.3,
                pass2_model="gemini-3.8-flash",
                pass2_duration=6.1,
            )

            json_file = tmp_path / "drafts" / "2026-10-06-120000.json"
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["pass1"]["model"] == "gemini-3.6-flash"
            assert data["pass1"]["duration_seconds"] == 8.3
            assert data["pass1"]["content"] == "Draft text content."
            assert data["pass1"]["content_char_count"] == len("Draft text content.")

    def test_records_pass2_info(self, tmp_path):
        with patch("generate_article.DRAFTS_DIR", str(tmp_path / "drafts")):
            _save_draft_metadata(
                file_timestamp="2026-10-06-120000",
                prompt_type="default",
                article_filename="2026-10-06-120000-auto-post.md",
                draft_content="Draft.",
                refined_content="Refined and expanded.",
                pass1_model="gemini-3.8-flash",
                pass1_duration=5.0,
                pass2_model=None,
                pass2_duration=0.0,
            )

            json_file = tmp_path / "drafts" / "2026-10-06-120000.json"
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["pass2"]["content"] == "Refined and expanded."
            assert data["pass2"]["model"] is None

    def test_diff_stats(self, tmp_path):
        with patch("generate_article.DRAFTS_DIR", str(tmp_path / "drafts")):
            draft = "Short."
            refined = "Much longer refined content here."
            _save_draft_metadata(
                file_timestamp="2026-10-06-120000",
                prompt_type="default",
                article_filename="2026-10-06-120000-auto-post.md",
                draft_content=draft,
                refined_content=refined,
                pass1_model="gemini-3.8-flash",
                pass1_duration=5.0,
                pass2_model="gemini-3.8-flash",
                pass2_duration=4.0,
            )

            json_file = tmp_path / "drafts" / "2026-10-06-120000.json"
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["diff_stats"]["char_count_change"] == len(refined) - len(draft)
            assert data["diff_stats"]["char_count_change"] > 0
            assert data["diff_stats"]["char_count_change_percent"] > 0

    def test_creates_directory(self, tmp_path):
        drafts_path = tmp_path / "drafts"
        assert not drafts_path.exists()

        with patch("generate_article.DRAFTS_DIR", str(drafts_path)):
            _save_draft_metadata(
                file_timestamp="2026-10-06-120000",
                prompt_type="default",
                article_filename="2026-10-06-120000-auto-post.md",
                draft_content="Draft.",
                refined_content="Refined.",
                pass1_model="gemini-3.8-flash",
                pass1_duration=1.0,
                pass2_model="gemini-3.8-flash",
                pass2_duration=1.0,
            )

        assert drafts_path.exists()
        assert (drafts_path / "2026-10-06-120000.json").exists()

    def test_line_count(self, tmp_path):
        with patch("generate_article.DRAFTS_DIR", str(tmp_path / "drafts")):
            draft = "line1\nline2\nline3"
            _save_draft_metadata(
                file_timestamp="2026-10-06-120000",
                prompt_type="default",
                article_filename="2026-10-06-120000-auto-post.md",
                draft_content=draft,
                refined_content=draft,
                pass1_model="gemini-3.8-flash",
                pass1_duration=1.0,
                pass2_model="gemini-3.8-flash",
                pass2_duration=1.0,
            )

            json_file = tmp_path / "drafts" / "2026-10-06-120000.json"
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["pass1"]["content_line_count"] == 3


# --------------------------------------------------
# ログ・メタファイルの期間ベースクリーンアップ
# --------------------------------------------------

class TestCleanupOldLogs:
    """Test time-based cleanup of log/metadata directories."""

    @staticmethod
    def _now_jst():
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone(timedelta(hours=9)))

    @staticmethod
    def _make_file(dir_path, ts, ext=".json", content="{}"):
        f = dir_path / f"{ts}{ext}"
        f.write_text(content, encoding="utf-8")
        return f

    def test_deletes_old_keeps_recent(self, tmp_path):
        from datetime import timedelta
        now = self._now_jst()
        old_ts = (now - timedelta(days=60)).strftime("%Y-%m-%d-%H%M%S")
        recent_ts = now.strftime("%Y-%m-%d-%H%M%S")

        d = tmp_path / "logs"
        d.mkdir()
        old_file = self._make_file(d, old_ts)
        recent_file = self._make_file(d, recent_ts)

        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d)]):
            removed = _cleanup_old_logs(days=30)

        assert removed == 1
        assert not old_file.exists()
        assert recent_file.exists()

    def test_keeps_all_recent(self, tmp_path):
        from datetime import timedelta
        now = self._now_jst()
        ts1 = now.strftime("%Y-%m-%d-%H%M%S")
        ts2 = (now - timedelta(days=5)).strftime("%Y-%m-%d-%H%M%S")

        d = tmp_path / "logs"
        d.mkdir()
        f1 = self._make_file(d, ts1)
        f2 = self._make_file(d, ts2)

        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d)]):
            removed = _cleanup_old_logs(days=30)

        assert removed == 0
        assert f1.exists()
        assert f2.exists()

    def test_never_deletes_gitkeep(self, tmp_path):
        d = tmp_path / "logs"
        d.mkdir()
        (d / ".gitkeep").write_text("", encoding="utf-8")

        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d)]):
            removed = _cleanup_old_logs(days=30)

        assert removed == 0
        assert (d / ".gitkeep").exists()

    def test_skips_non_timestamp_files(self, tmp_path):
        d = tmp_path / "logs"
        d.mkdir()
        weird = self._make_file(d, "no-timestamp-here", ext=".json")

        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d)]):
            removed = _cleanup_old_logs(days=30)

        assert removed == 0
        assert weird.exists()

    def test_missing_dir_no_error(self, tmp_path):
        missing = str(tmp_path / "does-not-exist")
        with patch("generate_article.LOG_CLEANUP_DIRS", [missing]):
            removed = _cleanup_old_logs(days=30)
        assert removed == 0

    def test_multiple_dirs(self, tmp_path):
        from datetime import timedelta
        now = self._now_jst()
        old_ts = (now - timedelta(days=90)).strftime("%Y-%m-%d-%H%M%S")
        recent_ts = now.strftime("%Y-%m-%d-%H%M%S")

        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        old_a = self._make_file(d1, old_ts)
        recent_b = self._make_file(d2, recent_ts)

        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d1), str(d2)]):
            removed = _cleanup_old_logs(days=30)

        assert removed == 1
        assert not old_a.exists()
        assert recent_b.exists()

    def test_custom_days_threshold(self, tmp_path):
        from datetime import timedelta
        now = self._now_jst()
        ts_45 = (now - timedelta(days=45)).strftime("%Y-%m-%d-%H%M%S")

        d = tmp_path / "logs"
        d.mkdir()
        f = self._make_file(d, ts_45)

        # 30日基準なら削除対象、60日基準なら保持
        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d)]):
            assert _cleanup_old_logs(days=30) == 1
            assert not f.exists()

        f2 = self._make_file(d, ts_45)
        with patch("generate_article.LOG_CLEANUP_DIRS", [str(d)]):
            assert _cleanup_old_logs(days=60) == 0
            assert f2.exists()

    def test_log_cleanup_dirs_covers_renamed_dirs(self):
        """リネーム後のログディレクトリがクリーンアップ対象に含まれること。"""
        dirs = [os.path.normpath(p) for p in LOG_CLEANUP_DIRS]
        assert any(p.endswith("drafts") for p in dirs)
        assert any(p.endswith("trend_usage_logs") for p in dirs)
        assert any(p.endswith("affiliate_logs") for p in dirs)
        assert any(p.endswith("prompt_logs") for p in dirs)


# --------------------------------------------------
# ジャンル事前スコアリング統合テスト
# --------------------------------------------------

class TestWorldSettingGenreMap:
    def test_fantasy_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["fantasy"] == ["fantasy"]

    def test_sf_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["sf"] == ["sf"]

    def test_slice_of_life_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["slice_of_life"] == ["slice_of_life"]

    def test_cyberpunk_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["cyberpunk"] == ["cyberpunk"]

    def test_adventure_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["adventure"] == ["action", "fantasy"]

    def test_mystery_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["mystery"] == ["mystery"]

    def test_isekai_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["isekai"] == ["fantasy", "action"]

    def test_modern_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["modern"] == ["slice_of_life", "action", "mystery"]

    def test_space_opera_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["space_opera"] == ["sf", "action"]

    def test_dungeon_crawl_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["dungeon_crawl"] == ["fantasy", "action"]

    def test_historical_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["historical"] == ["historical"]

    def test_all_settings_have_genre_map_entry(self):
        from generate_article import WORLD_SETTING_GENRE_MAP, WORLD_SETTING_WEIGHTS
        for key, _ in WORLD_SETTING_WEIGHTS:
            assert WORLD_SETTING_GENRE_MAP.get(key), f"{key} に genre map エントリがない"

    def test_weights_sum_to_100(self):
        from generate_article import WORLD_SETTING_WEIGHTS
        assert sum(w for _, w in WORLD_SETTING_WEIGHTS) == 100

    def test_fantasy_sf_mapping(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP["fantasy+sf"] == ["fantasy", "sf"]

    def test_unknown_setting_returns_none(self):
        from generate_article import WORLD_SETTING_GENRE_MAP
        assert WORLD_SETTING_GENRE_MAP.get("unknown_setting", []) == []


class TestLoadGenreScores:
    def test_missing_file_returns_empty(self, tmp_path):
        import generate_article
        with patch.object(generate_article, "GENRE_SCORES_PATH", str(tmp_path / "nonexistent.json")):
            result = generate_article._load_genre_scores()
        assert result == {}

    def test_valid_file(self, tmp_path):
        import generate_article
        path = tmp_path / "topics.json"
        data = {"scored_at": "2026-10-09T12:00:00Z", "topics": [], "copyrights": []}
        path.write_text(json.dumps(data), encoding="utf-8")
        with patch.object(generate_article, "GENRE_SCORES_PATH", str(path)):
            result = generate_article._load_genre_scores()
        assert result["topics"] == []

    def test_corrupt_file_returns_empty(self, tmp_path):
        import generate_article
        path = tmp_path / "topics.json"
        path.write_text("{invalid json", encoding="utf-8")
        with patch.object(generate_article, "GENRE_SCORES_PATH", str(path)):
            result = generate_article._load_genre_scores()
        assert result == {}


class TestFilterByGenre:
    def test_sorts_by_genre_score(self):
        import generate_article
        items = [
            {"url": "https://a.com", "title": "low genre"},
            {"url": "https://b.com", "title": "high genre"},
            {"url": "https://c.com", "title": "no score"},
        ]
        scores_data = {
            "topics": [
                {"key": "https://a.com", "scores": {"sf": 10, "fantasy": 5, "cyberpunk": 3, "action": 2}},
                {"key": "https://b.com", "scores": {"sf": 90, "fantasy": 80, "cyberpunk": 85, "action": 40}},
            ]
        }
        result = generate_article._filter_by_genre(items, ["sf"], scores_data)
        assert result[0]["url"] == "https://b.com"
        assert result[1]["url"] == "https://a.com"
        assert result[2]["url"] == "https://c.com"

    def test_multi_genre_takes_max(self):
        import generate_article
        items = [
            {"url": "https://a.com", "title": "fantasy high"},
            {"url": "https://b.com", "title": "sf high"},
        ]
        scores_data = {
            "topics": [
                {"key": "https://a.com", "scores": {"sf": 10, "fantasy": 95, "cyberpunk": 20, "action": 5}},
                {"key": "https://b.com", "scores": {"sf": 90, "fantasy": 15, "cyberpunk": 85, "action": 30}},
            ]
        }
        result = generate_article._filter_by_genre(items, ["fantasy", "sf"], scores_data)
        assert result[0]["url"] == "https://a.com"

    def test_empty_scores_data(self):
        import generate_article
        items = [{"url": "https://a.com", "title": "t"}]
        result = generate_article._filter_by_genre(items, ["sf"], {})
        assert len(result) == 1


class TestAppendTrendingTopicsGenre:
    def test_genre_filter_applied(self, tmp_path):
        import generate_article
        topics_path = tmp_path / "latest.json"
        topics_data = {
            "fetched_at": "2026-10-09T12:00:00+09:00",
            "ttl_hours": 24,
            "total": 2,
            "by_category": {
                "kemono": [
                    {"title": "sf topic", "url": "https://sf.com", "source": "rss", "category": "kemono", "score": 50},
                    {"title": "fantasy topic", "url": "https://fan.com", "source": "rss", "category": "kemono", "score": 50},
                ]
            },
        }
        topics_path.write_text(json.dumps(topics_data, ensure_ascii=False), encoding="utf-8")
        scores_path = tmp_path / "scores.json"
        scores_data = {
            "topics": [
                {"key": "https://sf.com", "scores": {"sf": 95, "fantasy": 10, "cyberpunk": 80, "action": 20}},
                {"key": "https://fan.com", "scores": {"sf": 15, "fantasy": 90, "cyberpunk": 25, "action": 30}},
            ]
        }
        scores_path.write_text(json.dumps(scores_data), encoding="utf-8")

        with patch.object(generate_article, "TOPICS_JSON_PATH", str(topics_path)), \
             patch.object(generate_article, "GENRE_SCORES_PATH", str(scores_path)), \
             patch.object(generate_article, "_save_trend_usage_log"), \
             patch.object(generate_article, "_check_topics_ttl", return_value=False), \
             patch.object(generate_article, "_check_per_source_ttl", return_value={}):
            result, keywords, urls, titles = generate_article._append_trending_topics(
                "", "kemono_story", target_genres=["sf"]
            )
        assert "sf topic" in result
        assert "https://sf.com" in urls
        assert titles == ["sf topic（rss）", "fantasy topic（rss）"]

    def test_no_genre_scores_falls_back_to_random(self, tmp_path):
        import generate_article
        topics_path = tmp_path / "latest.json"
        topics_data = {
            "fetched_at": "2026-10-09T12:00:00+09:00",
            "ttl_hours": 24,
            "total": 1,
            "by_category": {
                "kemono": [
                    {"title": "any topic", "url": "https://any.com", "source": "rss", "category": "kemono", "score": 50},
                ]
            },
        }
        topics_path.write_text(json.dumps(topics_data, ensure_ascii=False), encoding="utf-8")

        with patch.object(generate_article, "TOPICS_JSON_PATH", str(topics_path)), \
             patch.object(generate_article, "GENRE_SCORES_PATH", str(tmp_path / "nonexistent.json")), \
             patch.object(generate_article, "_save_trend_usage_log"), \
             patch.object(generate_article, "_check_topics_ttl", return_value=False), \
             patch.object(generate_article, "_check_per_source_ttl", return_value={}):
            result, keywords, urls, titles = generate_article._append_trending_topics(
                "", "kemono_story", target_genres=["sf"]
            )
        assert "any topic" in result
        assert titles == ["any topic（rss）"]


class TestAppendTrendingTopicsDescription:
    """_append_trending_topics() の description スニペット注入テスト"""

    def _write_topics(self, tmp_path, items):
        topics_path = tmp_path / "latest.json"
        topics_data = {
            "fetched_at": "2026-10-10T12:00:00+09:00",
            "ttl_hours": 24,
            "total": len(items),
            "by_category": {"kemono": items},
        }
        topics_path.write_text(json.dumps(topics_data, ensure_ascii=False), encoding="utf-8")
        return topics_path

    def test_description_injected_into_trend_block(self, tmp_path):
        import generate_article
        desc = "A long description that explains the game features and world in detail."
        topics_path = self._write_topics(tmp_path, [
            {"title": "Game news", "url": "https://gs.com/1", "source": "GameSpot RSS",
             "category": "kemono", "score": 0, "description": desc},
        ])
        with patch.object(generate_article, "TOPICS_JSON_PATH", str(topics_path)), \
             patch.object(generate_article, "GENRE_SCORES_PATH", str(tmp_path / "nonexistent.json")), \
             patch.object(generate_article, "_save_trend_usage_log"), \
             patch.object(generate_article, "_check_topics_ttl", return_value=False), \
             patch.object(generate_article, "_check_per_source_ttl", return_value={}):
            result, _, _, _ = generate_article._append_trending_topics("", "kemono_story")
        assert "Game news" in result
        assert desc[:100] in result
        assert " — " in result

    def test_no_description_no_snippet(self, tmp_path):
        import generate_article
        topics_path = self._write_topics(tmp_path, [
            {"title": "Plain topic", "url": "https://x.com/1", "source": "rss",
             "category": "kemono", "score": 0},
        ])
        with patch.object(generate_article, "TOPICS_JSON_PATH", str(topics_path)), \
             patch.object(generate_article, "GENRE_SCORES_PATH", str(tmp_path / "nonexistent.json")), \
             patch.object(generate_article, "_save_trend_usage_log"), \
             patch.object(generate_article, "_check_topics_ttl", return_value=False), \
             patch.object(generate_article, "_check_per_source_ttl", return_value={}):
            result, _, _, _ = generate_article._append_trending_topics("", "kemono_story")
        assert "Plain topic" in result
        assert " — " not in result

    def test_description_truncated_to_100_in_prompt(self, tmp_path):
        import generate_article
        desc = "あ" * 150
        topics_path = self._write_topics(tmp_path, [
            {"title": "t", "url": "https://gs.com/1", "source": "GameSpot RSS",
             "category": "kemono", "score": 0, "description": desc},
        ])
        with patch.object(generate_article, "TOPICS_JSON_PATH", str(topics_path)), \
             patch.object(generate_article, "GENRE_SCORES_PATH", str(tmp_path / "nonexistent.json")), \
             patch.object(generate_article, "_save_trend_usage_log"), \
             patch.object(generate_article, "_check_topics_ttl", return_value=False), \
             patch.object(generate_article, "_check_per_source_ttl", return_value={}):
            result, _, _, _ = generate_article._append_trending_topics("", "kemono_story")
        assert " — " + "あ" * 100 in result
        assert "あ" * 101 not in result

    def test_description_logged_in_trend_usage(self, tmp_path):
        import generate_article
        desc = "あ" * 250
        topics_path = self._write_topics(tmp_path, [
            {"title": "t", "url": "https://gs.com/1", "source": "GameSpot RSS",
             "category": "kemono", "score": 0, "description": desc},
        ])
        mock_log = MagicMock()
        with patch.object(generate_article, "TOPICS_JSON_PATH", str(topics_path)), \
             patch.object(generate_article, "GENRE_SCORES_PATH", str(tmp_path / "nonexistent.json")), \
             patch.object(generate_article, "_save_trend_usage_log", mock_log), \
             patch.object(generate_article, "_check_topics_ttl", return_value=False), \
             patch.object(generate_article, "_check_per_source_ttl", return_value={}):
            generate_article._append_trending_topics("", "kemono_story")
        log = mock_log.call_args[0][0]
        assert log["selected"][0]["description"] == "あ" * 200


class TestBuildGenerationInfoSection:
    """_build_generation_info_section() のテスト"""

    KEMONO_PARAMS = {
        "char_types": ["猫耳獣人", "犬耳獣人"],
        "char_type": "猫耳獣人 / 犬耳獣人",
        "world_setting_key": "fantasy",
        "world_setting": "ファンタジー",
        "transform_key": "tf",
        "transform_text": "、TF(変身・変形)",
        "relationship_key": "partnership",
        "relationship_text": "相棒関係",
        "extra_key": "rival",
        "extra_tag": "ライバル関係",
        "char_count": 2,
    }

    def test_kemono_full(self):
        import generate_article
        content = '---\ntitle: "x"\ncharacter_1: "cat_ears"\ncharacter_2: "dog_ears"\n---\n\nbody'
        section = generate_article._build_generation_info_section(
            ["Game news（GameSpot RSS）"], "kemono_story", self.KEMONO_PARAMS, content
        )
        assert '<details class="gen-info">' in section
        assert "🤖 生成情報" in section
        assert "Game news（GameSpot RSS）" in section
        assert "猫耳獣人 / 犬耳獣人" in section
        assert "ファンタジー" in section
        assert "TF（変身・変形）" in section
        assert "相棒関係" in section
        assert "ライバル関係" in section
        assert "cat_ears" in section
        assert "dog_ears" in section

    def test_transform_none_shows_nashi(self):
        import generate_article
        params = dict(self.KEMONO_PARAMS, transform_key="none", transform_text="")
        content = '---\ntitle: "x"\ncharacter_1: "cat_ears"\ncharacter_2: "dog_ears"\n---\n\nbody'
        section = generate_article._build_generation_info_section(
            [], "kemono_story", params, content
        )
        assert "なし" in section

    def test_extra_none_omitted(self):
        import generate_article
        params = dict(self.KEMONO_PARAMS, extra_key="none", extra_tag="")
        content = '---\ntitle: "x"\ncharacter_1: "cat_ears"\ncharacter_2: "dog_ears"\n---\n\nbody'
        section = generate_article._build_generation_info_section(
            [], "kemono_story", params, content
        )
        assert "追加設定" not in section

    def test_trend_only_non_kemono(self):
        import generate_article
        content = '---\ntitle: "x"\n---\n\nbody'
        section = generate_article._build_generation_info_section(
            ["AI news（GitHub）"], "default", {}, content
        )
        assert "使用したトレンド情報" in section
        assert "キャラクターデータ" not in section

    def test_empty_returns_empty_string(self):
        import generate_article
        content = '---\ntitle: "x"\n---\n\nbody'
        assert generate_article._build_generation_info_section([], "default", {}, content) == ""

    def test_html_escaped(self):
        import generate_article
        content = '---\ntitle: "x"\ncharacter_1: "cat & <dog>"\ncharacter_2: ""\n---\n\nbody'
        section = generate_article._build_generation_info_section(
            ['<script>alert("x")</script>（rss）'], "kemono_story", self.KEMONO_PARAMS, content
        )
        assert "<script>" not in section
        assert "&lt;script&gt;" in section
        assert "cat &amp; &lt;dog&gt;" in section


class TestLoadCharacterFeaturesGenre:
    def test_copyright_genre_priority(self, tmp_path):
        import generate_article
        cf_dir = tmp_path / "data"
        cf_dir.mkdir()
        cf_path = cf_dir / "character_features.json"
        cf_data = {
            "posts": [
                {"species": ["wolf"], "colors": ["blue"], "physical": ["ears"], "characters": ["A"], "copyrights": ["nintendo"]},
                {"species": ["fox"], "colors": ["red"], "physical": ["tail"], "characters": ["B"], "copyrights": ["harry_potter"]},
            ],
            "aggregates": {
                "copyrights": {"nintendo": 10, "harry_potter": 5, "pokemon": 3},
                "artists": {"artist_a": 5, "artist_b": 3},
            },
            "updated_at": "2026-10-09",
            "total_posts_analyzed": 25,
        }
        cf_path.write_text(json.dumps(cf_data, ensure_ascii=False), encoding="utf-8")
        scores_path = tmp_path / "scores.json"
        scores_data = {
            "copyrights": [
                {"name": "nintendo", "scores": {"sf": 90, "fantasy": 20, "cyberpunk": 70, "action": 40}},
                {"name": "harry_potter", "scores": {"sf": 10, "fantasy": 95, "cyberpunk": 15, "action": 30}},
                {"name": "pokemon", "scores": {"sf": 85, "fantasy": 10, "cyberpunk": 60, "action": 50}},
            ]
        }
        scores_path.write_text(json.dumps(scores_data), encoding="utf-8")

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            with patch.object(generate_article, "GENRE_SCORES_PATH", str(scores_path)):
                result = generate_article._load_character_features(target_genres=["fantasy"])
        finally:
            os.chdir(orig_cwd)

        assert "harry_potter" in result
        assert "nintendo" in result
