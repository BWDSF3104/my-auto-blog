import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fetch_topics import _is_nsfw_post, TOPICS_DIR, OUTPUT_PATH, TTL_HOURS


class TestIsNSFWPost:
    """_is_nsfw_post() のユニットテスト"""

    def test_nsfw_rating_explicit(self):
        """rating: 'e' (explicit) の場合はTrueを返す"""
        post = {
            "rating": "e",
            "tags": {"general": ["test", "safe"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_rating_questionable(self):
        """rating: 'q' (questionable) の場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "safe"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_rating_safe(self):
        """rating: 's' (safe) の場合はFalseを返す"""
        post = {
            "rating": "s",
            "tags": {"general": ["test", "safe"]}
        }
        assert _is_nsfw_post(post) is False

    def test_nsfw_tag_in_general(self):
        """generalタグにNSFW用語が含まれる場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "sexual"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_tag_in_species(self):
        """speciesタグにNSFW用語が含まれる場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test"], "species": ["loli"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_tag_in_copyright(self):
        """copyrightタグにNSFW用語が含まれる場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test"], "copyright": ["penis"]}
        }
        assert _is_nsfw_post(post) is True

    def test_sfw_post(self):
        """SFWな投稿の場合はFalseを返す"""
        post = {
            "rating": "s",
            "tags": {"general": ["kemono", "dragon"], "species": ["dragon"]}
        }
        assert _is_nsfw_post(post) is False

    def test_empty_tags(self):
        """タグが空でsafeの場合はFalseを返す"""
        post = {
            "rating": "s",
            "tags": {}
        }
        assert _is_nsfw_post(post) is False

    def test_multiple_nsfw_tags(self):
        """複数のNSFWタグが含まれる場合はTrueを返す"""
        post = {
            "rating": "e",
            "tags": {"general": ["sexual", "breast_exposure"]}
        }
        assert _is_nsfw_post(post) is True

    def test_case_sensitive_nsfw(self):
        """NSFWタグは小文字でマッチする"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "sex"]}
        }
        assert _is_nsfw_post(post) is True

    def test_partial_word_no_match(self):
        """部分一致ではなく完全一致でマッチする"""
        post = {
            "rating": "s",
            "tags": {"general": ["test", "namespace"]}
        }
        assert _is_nsfw_post(post) is False

    def test_missing_keys(self):
        """必要なキーが不足している場合はFalseを返す"""
        post = {}
        assert _is_nsfw_post(post) is False

    def test_mixed_tags(self):
        """SFWとNSFWのタグが混在する場合はTrueを返す"""
        post = {
            "rating": "s",
            "tags": {"general": ["safe", "test", "vagina"]}
        }
        assert _is_nsfw_post(post) is True


# --------------------------------------------------
# Cache architecture tests (per-source TTL, merge, copy, cleanup)
# --------------------------------------------------

def _run_main(tmp_path, collect_returns, prev_data=None):
    """main() をテスト用環境で実行して出力 JSON を返す。
    collect_returns: {"hackernews": [...], "rss": [...], "reddit": [...], "e621": [...]}
    """
    import fetch_topics
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir(exist_ok=True)
    latest_json = topics_dir / "latest.json"

    orig_topics_dir = fetch_topics.TOPICS_DIR
    orig_output_path = fetch_topics.OUTPUT_PATH
    fetch_topics.TOPICS_DIR = str(topics_dir)
    fetch_topics.OUTPUT_PATH = str(latest_json)

    if prev_data is not None:
        latest_json.write_text(json.dumps(prev_data), encoding="utf-8")

    try:
        with patch.object(sys, "argv", ["fetch_topics.py"]), \
             patch.object(fetch_topics, "collect_hacker_news", return_value=collect_returns.get("hackernews", [])), \
             patch.object(fetch_topics, "collect_rss_feeds", return_value=collect_returns.get("rss", [])), \
             patch.object(fetch_topics, "collect_reddit", return_value=collect_returns.get("reddit", [])), \
             patch.object(fetch_topics, "collect_e621", return_value=collect_returns.get("e621", [])), \
             patch.object(fetch_topics, "collect_kemono_api", return_value=collect_returns.get("kemono", [])), \
             patch.object(fetch_topics, "collect_github_trending", return_value=[]), \
             patch.object(fetch_topics, "collect_bluesky", return_value=[]):
            fetch_topics.main()
        return json.loads(latest_json.read_text(encoding="utf-8"))
    finally:
        fetch_topics.TOPICS_DIR = orig_topics_dir
        fetch_topics.OUTPUT_PATH = orig_output_path


class TestCacheOutputStructure:
    """Per-source TTL 構造とタイムスタンプファイルのテスト"""

    def test_per_source_fetched_at_in_output(self, tmp_path):
        """sources 内の各 source に fetched_at が記録される"""
        topics = [
            {"title": "Tech news", "source": "hackernews", "category": "tech", "score": 10, "url": "https://hn.com/1"},
        ]
        result = _run_main(tmp_path, {"hackernews": topics})
        assert "sources" in result
        assert "hackernews" in result["sources"]
        assert "fetched_at" in result["sources"]["hackernews"]

    def test_timestamped_file_created(self, tmp_path):
        """タイムスタンプ付き JSON ファイルが topics/ に作成される"""
        topics = [
            {"title": "Test", "source": "hackernews", "category": "tech", "score": 5, "url": "https://hn.com/1"},
        ]
        _run_main(tmp_path, {"hackernews": topics})
        topics_dir = tmp_path / "topics"
        ts_files = [f for f in topics_dir.glob("*.json") if f.name != "latest.json"]
        assert len(ts_files) >= 1
        assert ts_files[0].name.endswith(".json")
        assert ts_files[0].name.replace(".json", "").count("_") >= 1

    def test_latest_json_is_copy_of_timestamped_file(self, tmp_path):
        """latest.json がタイムスタンプファイルのコピーとして存在する"""
        topics = [
            {"title": "Test", "source": "hackernews", "category": "tech", "score": 5, "url": "https://hn.com/1"},
        ]
        _run_main(tmp_path, {"hackernews": topics})
        topics_dir = tmp_path / "topics"
        latest_json = topics_dir / "latest.json"
        assert latest_json.exists()
        assert not latest_json.is_symlink()
        content = json.loads(latest_json.read_text(encoding="utf-8"))
        assert "by_category" in content

    def test_output_has_by_category(self, tmp_path):
        """出力 JSON に by_category キーが含まれる"""
        topics = [
            {"title": "Tech1", "source": "hackernews", "category": "tech", "score": 10, "url": "https://hn.com/1"},
            {"title": "Tech2", "source": "hackernews", "category": "tech", "score": 8, "url": "https://hn.com/2"},
        ]
        result = _run_main(tmp_path, {"hackernews": topics})
        assert "by_category" in result
        assert "tech" in result["by_category"]
        assert len(result["by_category"]["tech"]) == 2
        assert result["by_category"]["tech"][0]["score"] >= result["by_category"]["tech"][1]["score"]


class TestPartialFetchMerge:
    """部分的な fetch 時のマージロジックのテスト"""

    def test_uncollected_source_inherited_from_previous(self, tmp_path):
        """今回収集しなかった source は前のデータから継承される"""
        prev = {
            "fetched_at": "2026-01-01T00:00:00+09:00",
            "ttl_hours": 24,
            "sources": {
                "hackernews": {"fetched_at": "2026-01-01T00:00:00+09:00", "topics": []},
                "e621": {"fetched_at": "2026-01-01T00:00:00+09:00", "topics": [
                    {"title": "Prev e621", "source": "e621", "category": "kemono", "score": 5, "url": "https://e621.net/1"}
                ]},
            },
            "by_category": {"kemono": []},
            "all": [],
        }
        current_topics = {
            "hackernews": [{"title": "New HN", "source": "hackernews", "category": "tech", "score": 10, "url": "https://hn.com/1"}],
            "e621": [],
        }
        result = _run_main(tmp_path, current_topics, prev_data=prev)
        assert "e621" in result["sources"]
        assert len(result["sources"]["e621"]["topics"]) == 1
        assert result["sources"]["e621"]["topics"][0]["title"] == "Prev e621"

    def test_uncollected_source_fetched_at_preserved(self, tmp_path):
        """未収集 source の fetched_at は前の値を保持"""
        prev = {
            "fetched_at": "2026-01-01T00:00:00+09:00",
            "ttl_hours": 24,
            "sources": {
                "e621": {"fetched_at": "2026-01-01T00:00:00+09:00", "topics": [
                    {"title": "Prev", "source": "e621", "category": "kemono", "score": 5, "url": "https://e621.net/1"}
                ]},
            },
            "by_category": {},
            "all": [],
        }
        current_topics = {
            "hackernews": [],
            "e621": [],
        }
        result = _run_main(tmp_path, current_topics, prev_data=prev)
        assert result["sources"]["e621"]["fetched_at"] == "2026-01-01T00:00:00+09:00"

    def test_by_category_uncollected_inherited(self, tmp_path):
        """未収集カテゴリの by_category は前のデータを継承"""
        prev = {
            "fetched_at": "2026-01-01T00:00:00+09:00",
            "ttl_hours": 24,
            "sources": {},
            "by_category": {
                "kemono": [{"title": "Prev kemono", "source": "e621", "category": "kemono", "score": 5, "url": "https://e621.net/1"}],
            },
            "all": [],
        }
        current_topics = {
            "hackernews": [{"title": "New tech", "source": "hackernews", "category": "tech", "score": 10, "url": "https://hn.com/1"}],
            "e621": [],
        }
        result = _run_main(tmp_path, current_topics, prev_data=prev)
        assert "kemono" in result["by_category"]
        assert len(result["by_category"]["kemono"]) == 1
        assert result["by_category"]["kemono"][0]["title"] == "Prev kemono"

    def test_by_category_collected_overwrites(self, tmp_path):
        """収集したカテゴリの by_category は上書きされる"""
        prev = {
            "fetched_at": "2026-01-01T00:00:00+09:00",
            "ttl_hours": 24,
            "sources": {},
            "by_category": {
                "tech": [{"title": "Old tech", "source": "hackernews", "category": "tech", "score": 3, "url": "https://hn.com/old"}],
            },
            "all": [],
        }
        current_topics = {
            "hackernews": [{"title": "New tech", "source": "hackernews", "category": "tech", "score": 10, "url": "https://hn.com/1"}],
        }
        result = _run_main(tmp_path, current_topics, prev_data=prev)
        assert len(result["by_category"]["tech"]) == 1
        assert result["by_category"]["tech"][0]["title"] == "New tech"


class TestOldFileCleanup:
    """古いファイルのクリーンアップテスト"""

    def test_keeps_last_10_files(self, tmp_path):
        """タイムスタンプファイルは最新10件まで保持"""
        topics_dir = tmp_path / "topics"
        topics_dir.mkdir()
        for i in range(12):
            ts_file = topics_dir / f"2026-01-0{i if i < 9 else '1'}_{100+i:04d}.json"
            ts_file.write_text('{"test": true}', encoding="utf-8")
        _run_main(tmp_path, {})
        ts_files = [f for f in topics_dir.iterdir() if f.is_file() and f.name != "latest.json"]
        assert len(ts_files) <= 11


class TestTTLHours:
    """TTL_HOURS 環境変数設定のテスト"""

    def test_ttl_hours_default(self):
        """TTL_HOURS のデフォルトは24"""
        assert TTL_HOURS == 24

    def test_ttl_hours_from_env(self, tmp_path, monkeypatch):
        """CACHE_TTL_HOURS 環境変数で上書き可能"""
        monkeypatch.setenv("CACHE_TTL_HOURS", "48")
        import importlib
        import fetch_topics
        importlib.reload(fetch_topics)
        assert fetch_topics.TTL_HOURS == 48
