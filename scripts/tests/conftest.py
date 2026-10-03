import pytest
import os
import sys

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Prevent pytest from collecting test_real_apis.py (calls external APIs)
collect_ignore = ["test_real_apis.py"]


@pytest.fixture
def sample_markdown_with_frontmatter():
    """サンプルのMarkdownコンテンツ（Frontmatter付き）"""
    return '''---
title: "テスト記事のタイトル"
description: "これはテスト用の記事の説明です。テスト用の説明です。"
tags: [テスト, テスト2]
image_prompt: "test image"
prompt_type: "default"
slug: "test-article"
---

# テスト記事のタイトル

これはテスト記事の本文です。テスト用の内容です。

## セクション1

テスト用のセクション内容です。

![test image](test-image.png)

## セクション2

もう一つのテストセクションです。
'''


@pytest.fixture
def sample_markdown_with_characters():
    """キャラクター設定が含まれるMarkdown"""
    return '''---
title: "テスト物語"
description: "テスト物語の説明です。"
tags: [物語, テスト]
prompt_type: "kemono_story"
---

# テスト物語

## キャラクター設定
- **Alice**: 青い髪の少女、猫耳、魔法使い
- **Bob**: 茶色の髪の青年、犬耳、戦士

## 物語

AliceとBobの冒険物語です。

![image_prompt](test.png)
'''


@pytest.fixture
def sample_markdown_with_art_style():
    """アートスタイルが含まれるMarkdown"""
    return '''---
title: "テスト物語"
description: "テスト物語の説明です。"
tags: [物語]
prompt_type: "kemono_story"
---

# テスト物語

## アートスタイル
- **art_style**: 水彩画風、柔らかい色調

## 物語

テスト物語の内容です。
'''


@pytest.fixture
def sample_topics_json():
    """サンプルのトピックJSONデータ"""
    return {
        "hacker_news": [
            {"title": "Test HN Topic", "url": "https://example.com/1", "score": 100}
        ],
        "reddit": [
            {"title": "Test Reddit Topic", "url": "https://example.com/2", "score": 50}
        ],
        "e621": [
            {"title": "Test E621 Topic", "url": "https://example.com/3", "score": 200}
        ],
        "rss": [
            {"title": "Test RSS Topic", "url": "https://example.com/4", "score": 30}
        ],
        "github_trending": [
            {"title": "Test GitHub Topic", "url": "https://example.com/5", "score": 150}
        ]
    }


@pytest.fixture
def sample_product_recommendations():
    """サンプルのproduct_recommendationsデータ"""
    return [
        {
            "name": "テスト商品1",
            "category": "electronics",
            "price_range": "low",
            "description": "テスト商品1の説明"
        },
        {
            "name": "テスト商品2",
            "category": "books",
            "price_range": "medium",
            "description": "テスト商品2の説明"
        }
    ]


@pytest.fixture
def temp_posts_dir(tmp_path):
    """一時的なpostsディレクトリ"""
    posts_dir = tmp_path / "src" / "content" / "posts"
    posts_dir.mkdir(parents=True)
    return posts_dir


@pytest.fixture
def temp_data_dir(tmp_path):
    """一時的なdataディレクトリ"""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def temp_images_dir(tmp_path):
    """一時的なimagesディレクトリ"""
    images_dir = tmp_path / "public" / "images"
    images_dir.mkdir(parents=True)
    return images_dir


@pytest.fixture
def mock_env_vars(monkeypatch):
    """環境変数のモック"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setenv("HF_TOKEN", "test-hf-token")
    monkeypatch.setenv("PROMPT_TYPE", "default")


@pytest.fixture
def sample_inline_image_markdown():
    """本文内画像プレースホルダーを含むMarkdown"""
    return '''---
title: "テスト記事"
description: "テスト記事の説明です。"
tags: [テスト]
prompt_type: "default"
---

# テスト記事

本文の内容です。

![image_prompt: test situation](inline-image.png)

さらに本文が続きます。
'''


@pytest.fixture
def sample_affiliate_placeholders():
    """アフィリエイトプレースホルダーを含むMarkdown"""
    return '''---
title: "テスト記事"
description: "テスト記事の説明です。"
tags: [テスト]
prompt_type: "default"
---

# テスト記事

[[affiliate:product_name:category]]

本文の内容です。

[[affiliate:another_product:books]]
'''


@pytest.fixture
def sample_product_placeholders():
    """商品プレースホルダーを含むMarkdown"""
    return '''---
title: "テスト記事"
description: "テスト記事の説明です。"
tags: [テスト]
prompt_type: "default"
---

# テスト記事

| 商品名 | カテゴリ |
|--------|----------|
| [[product:test_product:electronics]] | electronics |
| [[product:another_product:books]] | books |
'''


@pytest.fixture
def sample_product_cards_markdown():
    """product_recommendationsを含むMarkdown"""
    return '''---
title: "テスト記事"
description: "テスト記事の説明です。"
tags: [テスト]
prompt_type: "default"
product_recommendations:
  - name: "テスト商品1"
    category: "electronics"
    price_range: "low"
  - name: "テスト商品2"
    category: "books"
    price_range: "medium"
---

# テスト記事

本文の内容です。
'''


@pytest.fixture
def sample_prompt_template():
    """サンプルのプロンプトテンプレート"""
    return '''あなたはブログ記事のライターです。

{ng_instruction}

以下の条件で記事を作成してください:
- 公開日時: {pub_date_str}
- 言語: 日本語
'''


@pytest.fixture
def sample_e621_posts():
    """サンプルのe621投稿データ"""
    return [
        {
            "id": 12345,
            "tag_string_artist": "test_artist",
            "tag_string_character": "test_char",
            "tag_string_copyright": "",
            "tag_string_general": "test tag1 test tag2",
            "tag_string_meta": "",
            "tag_string_race": "",
            "tag_string_species": "",
            "tag_string_status": "",
            "tag_string_toolbar": "",
        },
        {
            "id": 67890,
            "tag_string_artist": "test_artist2",
            "tag_string_character": "",
            "tag_string_copyright": "test_copyright",
            "tag_string_general": "test tag3",
            "tag_string_meta": "",
            "tag_string_race": "",
            "tag_string_species": "",
            "tag_string_status": "",
            "tag_string_toolbar": "",
        }
    ]


@pytest.fixture
def sample_rss_items():
    """サンプルのRSSアイテム"""
    class MockRssItem:
        def __init__(self, title, link):
            self.title = title
            self.link = link
    return [
        MockRssItem("Test RSS Item 1", "https://example.com/rss1"),
        MockRssItem("Test RSS Item 2", "https://example.com/rss2"),
    ]
