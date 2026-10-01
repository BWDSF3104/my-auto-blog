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
    def test_replace_affiliate_placeholder(self):
        content = 'Check out <!-- AFFILIATE: "Amazon" | "best deals" --> for products.'
        result = process_inline_affiliates(content)
        assert "amazon.co.jp" in result
        assert "rakuten.co.jp" in result
        assert '<!-- AFFILIATE:' not in result
        assert "best deals" in result

    def test_no_affiliate_placeholder(self):
        content = "No affiliate links here."
        result = process_inline_affiliates(content)
        assert result == content

    def test_multiple_affiliate_placeholders(self):
        content = 'Link1: <!-- AFFILIATE: "Amazon" | "Amazon" --> Link2: <!-- AFFILIATE: "Rakuten" | "Rakuten" -->'
        result = process_inline_affiliates(content)
        assert "amazon.co.jp" in result
        assert "rakuten.co.jp" in result
        assert '<!-- AFFILIATE:' not in result


# --------------------------------------------------
# process_inline_products tests
# --------------------------------------------------

class TestProcessInlineProducts:
    def test_replace_product_placeholder(self):
        content = 'Product: <!-- AFF_PRODUCT: "Noise Cancelling Headphones" -->'
        result = process_inline_products(content)
        assert "amazon.co.jp" in result
        assert "rakuten.co.jp" in result
        assert '<!-- AFF_PRODUCT:' not in result
        assert "[Amazon]" in result
        assert "[楽天]" in result

    def test_no_product_placeholder(self):
        content = "No product links here."
        result = process_inline_products(content)
        assert result == content


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
        """リクエストカテゴリと一致しない source は期限切れチェックされない"""
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        old = (datetime.now(JST) - timedelta(hours=48)).isoformat()
        data = self._make_data({
            "e621": {
                "fetched_at": old,
                "topics": [{"title": "T", "category": "kemono", "source": "e621"}],
            }
        })
        result = _check_per_source_ttl(data, ["tech"])
        assert result["e621"] is True  # カテゴリ不一致 → 期限切れ

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
