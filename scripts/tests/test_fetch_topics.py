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
from fetch_topics import (
    _clean_rss_description,
    _is_nsfw_post,
    _parse_entertainment_page,
    STORY_INSPIRATION_THEMES,
    TOPICS_DIR,
    OUTPUT_PATH,
    TTL_HOURS,
    fetch_rss,
)


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
             patch.object(fetch_topics, "collect_github_trending", return_value=[]), \
             patch.object(fetch_topics, "collect_bluesky", return_value=[]), \
             patch.object(fetch_topics, "collect_entertainment_trends", return_value=collect_returns.get("entertainment", [])):
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


class TestCleanRssDescription:
    """_clean_rss_description() のユニットテスト"""

    def test_none_returns_empty(self):
        assert _clean_rss_description(None) == ""

    def test_empty_returns_empty(self):
        assert _clean_rss_description("") == ""

    def test_plain_text_unchanged(self):
        assert _clean_rss_description("hello world") == "hello world"

    def test_html_tags_stripped(self):
        assert _clean_rss_description("<p>Today a <b>game</b> was announced.</p>") == "Today a game was announced."

    def test_entities_unescaped(self):
        assert _clean_rss_description("Tom &amp; Jerry") == "Tom & Jerry"

    def test_whitespace_collapsed(self):
        assert _clean_rss_description("line1\n\nline2   line3") == "line1 line2 line3"

    def test_truncated_to_max(self):
        result = _clean_rss_description("あ" * 500)
        assert len(result) == 300


class TestFetchRssDescription:
    """fetch_rss() の description 抽出テスト（urlopen をモック）"""

    @staticmethod
    def _mock_feed(xml: str):
        resp = MagicMock()
        resp.read.return_value = xml.encode("utf-8")
        resp.__enter__.return_value = resp
        return resp

    def test_rss20_description(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<rss version=\"2.0\"><channel><title>Feed</title>"
            "<item><title>Game News</title><link>https://example.com/1</link>"
            "<description>&lt;p&gt;Today a &lt;b&gt;game&lt;/b&gt; was announced.&lt;/p&gt;More details.</description>"
            "</item></channel></rss>"
        )
        with patch("fetch_topics.urllib.request.urlopen", return_value=self._mock_feed(xml)):
            items = fetch_rss("https://example.com/feed")
        assert items[0]["title"] == "Game News"
        assert items[0]["description"] == "Today a game was announced. More details."

    def test_content_encoded_preferred(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<rss version=\"2.0\"><channel><title>Feed</title>"
            "<item><title>Article</title><link>https://example.com/2</link>"
            "<description>Short summary</description>"
            '<content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">'
            "Full article body with extra details."
            "</content:encoded></item></channel></rss>"
        )
        with patch("fetch_topics.urllib.request.urlopen", return_value=self._mock_feed(xml)):
            items = fetch_rss("https://example.com/feed")
        assert items[0]["description"] == "Full article body with extra details."

    def test_atom_content_preferred_over_summary(self):
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<title>Feed</title>"
            '<entry><title>Entry</title><link href="https://example.com/3"/>'
            "<summary>Summary text</summary>"
            "<content>Full content body here</content></entry>"
            "</feed>"
        )
        with patch("fetch_topics.urllib.request.urlopen", return_value=self._mock_feed(xml)):
            items = fetch_rss("https://example.com/feed")
        assert items[0]["title"] == "Entry"
        assert items[0]["description"] == "Full content body here"

    def test_atom_summary_when_no_content(self):
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<title>Feed</title>"
            '<entry><title>Entry</title><link href="https://example.com/4"/>'
            "<summary>Only summary</summary></entry>"
            "</feed>"
        )
        with patch("fetch_topics.urllib.request.urlopen", return_value=self._mock_feed(xml)):
            items = fetch_rss("https://example.com/feed")
        assert items[0]["description"] == "Only summary"

    def test_no_description_returns_empty(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<rss version=\"2.0\"><channel><title>Feed</title>"
            "<item><title>No Desc</title><link>https://example.com/5</link></item>"
            "</channel></rss>"
        )
        with patch("fetch_topics.urllib.request.urlopen", return_value=self._mock_feed(xml)):
            items = fetch_rss("https://example.com/feed")
        assert items[0]["description"] == ""


class TestCollectRssFeedsDescription:
    """collect_rss_feeds() の description 引き継ぎテスト"""

    def test_description_passthrough(self):
        import fetch_topics
        with patch.object(fetch_topics, "fetch_rss", return_value=[
            {"title": "t", "url": "https://x.com/1", "description": "desc text"},
        ]), patch.object(fetch_topics, "RSS_FEEDS", [
            {"name": "TestFeed", "url": "https://x.com/feed", "category": "tech"},
        ]):
            results = fetch_topics.collect_rss_feeds()
        assert results[0]["description"] == "desc text"


class TestCollectEntertainmentTrends:
    """collect_entertainment_trends() の RSS/HTML 分離とフォールバックテスト"""

    def test_rss_sources_have_description(self):
        import fetch_topics
        with patch.object(fetch_topics, "fetch_rss", return_value=[
            {"title": "Game news", "url": "https://gs.com/1", "description": "Game description text"},
        ]), patch.object(fetch_topics, "ENTERTAINMENT_HTML_SOURCES", []):
            results = fetch_topics.collect_entertainment_trends(["kemono"])
        assert len(results) == 2
        assert {r["source"] for r in results} == {"GameSpot RSS", "IGN RSS"}
        assert all(r["description"] == "Game description text" for r in results)

    def test_html_sources_have_empty_description(self):
        import fetch_topics
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'<html><body><a href="https://www.animenewsnetwork.com/news/2026-10-10/some-anime-news-headline">'
            b'Some anime news headline</a></body></html>'
        )
        mock_resp.__enter__.return_value = mock_resp
        with patch.object(fetch_topics, "fetch_rss", return_value=[]), \
             patch.object(fetch_topics, "ENTERTAINMENT_RSS_SOURCES", []), \
             patch.object(fetch_topics.urllib.request, "urlopen", return_value=mock_resp):
            results = fetch_topics.collect_entertainment_trends(["kemono"])
        assert len(results) > 0
        assert all(r["description"] == "" for r in results)

    def test_html_sources_excludes_crunchyroll(self):
        """Crunchyroll は静的HTMLに記事リンクが 0 件のため収集対象外（2026-10-10 実測）"""
        import fetch_topics
        names = [s["name"] for s in fetch_topics.ENTERTAINMENT_HTML_SOURCES]
        assert "Crunchyroll News" not in names

    def test_all_sources_failed_uses_builtin_themes(self):
        import fetch_topics
        with patch.object(fetch_topics, "fetch_rss", return_value=[]), \
             patch.object(fetch_topics, "ENTERTAINMENT_HTML_SOURCES", []):
            results = fetch_topics.collect_entertainment_trends(["kemono"])
        assert len(results) == len(STORY_INSPIRATION_THEMES)
        assert all(r["source"] == "StoryInspiration" for r in results)
        assert all(r["description"] for r in results)

    def test_category_filter_excludes_non_kemono(self):
        import fetch_topics
        results = fetch_topics.collect_entertainment_trends(["tech"])
        assert results == []


class TestParseEntertainmentPage:
    """_parse_entertainment_page() の whitelist 抽出テスト"""

    ANN_BASE = "https://www.animenewsnetwork.com/"

    def _html(self, body: str) -> str:
        return f"<html><body>{body}</body></html>"

    def test_nav_links_excluded(self):
        """ナビ/フッター UI リンク（ログイン・登録・アーカイブ等）は除外される"""
        html = self._html(
            '<a href="/auth/facebook/login">Sign in with Facebook account</a>'
            '<a href="/register">Create a new account now</a>'
            '<a href="/character/index">Character index and archive page</a>'
        )
        results = _parse_entertainment_page(html, "Anime News Network", "kemono", base_url=self.ANN_BASE)
        assert results == []

    def test_article_links_kept_with_resolved_url(self):
        """記事URL（日付付きパス）は抽出され、相対URLは base_url に対して解決される"""
        html = self._html(
            '<a href="/news/2026-10-10/some-anime-news-headline">Some anime news headline for testing</a>'
            '<a href="/review/2026-09-01/show-a-movie-review">A review of the movie show</a>'
        )
        results = _parse_entertainment_page(html, "Anime News Network", "kemono", base_url=self.ANN_BASE)
        assert [r["url"] for r in results] == [
            "https://www.animenewsnetwork.com/news/2026-10-10/some-anime-news-headline",
            "https://www.animenewsnetwork.com/review/2026-09-01/show-a-movie-review",
        ]
        assert results[0]["title"] == "Some anime news headline for testing"
        assert all(r["source"] == "Anime News Network" and r["category"] == "kemono" for r in results)

    def test_non_article_path_excluded(self):
        """日付付きでないパス（動画・アーカイブ等）は除外される"""
        html = self._html(
            '<a href="/video/popular">Popular videos on the site page</a>'
            '<a href="https://www.animenewsnetwork.com/news/archive">News archive page for all years</a>'
        )
        results = _parse_entertainment_page(html, "Anime News Network", "kemono", base_url=self.ANN_BASE)
        assert results == []

    def test_duplicate_urls_deduplicated(self):
        html = self._html(
            '<a href="/news/2026-10-10/some-anime-news-headline">Some anime news headline for testing</a>'
            '<a href="/news/2026-10-10/some-anime-news-headline">Some anime news headline for testing</a>'
        )
        results = _parse_entertainment_page(html, "Anime News Network", "kemono", base_url=self.ANN_BASE)
        assert len(results) == 1

    def test_max_15_results(self):
        parts = "".join(
            f'<a href="/news/2026-10-10/article-number-{i:02d}">Article headline number {i:02d} here</a>'
            for i in range(20)
        )
        results = _parse_entertainment_page(self._html(parts), "Anime News Network", "kemono", base_url=self.ANN_BASE)
        assert len(results) == 15

    def test_unknown_source_returns_empty(self):
        """whitelist が定義されていない source は何も返さない"""
        html = self._html('<a href="/news/2026-10-10/x">Some anime news headline for testing</a>')
        results = _parse_entertainment_page(html, "Unknown Source", "kemono", base_url="https://unknown.example.com/")
        assert results == []
