"""
test_real_apis.py — トレンド収集の各データソースに対してリアルAPIを呼び出して応答を確認するスクリプト

既存のユニットテスト（モック使用）とは別に、実際に各APIに接続して
- 応答ステータス
- レート制限ヘッダー
- 応答時間
- 取得した実際のコンテンツ（タイトル、URL、スコア）
を確認する。

使用法:
  python scripts/tests/test_real_apis.py                    # 全ソーステスト
  python scripts/tests/test_real_apis.py --source e621      # 単一ソース
  python scripts/tests/test_real_apis.py --save              # 結果をJSONに保存
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# pytest による自動収集を無効化（このファイルは独立スクリプトとして実行する）
__test__ = False

# Windows コンソールで cp932 → UTF-8 変換エラーを防ぐ
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

USER_AGENT = "my-auto-blog/1.0 (https://github.com)"
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "api_test_results")


def _safe_print(text: str) -> None:
    """cp932 コンソールでも失敗しない print のラッパー。"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("cp932", errors="replace").decode("cp932", errors="replace"))


def fetch_full(url: str, headers: dict = None, timeout: int = 15) -> dict:
    """リクエストを送信して完全な応答を返す。"""
    req = urllib.request.Request(url, headers=headers or {})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.monotonic() - start
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "status": resp.status,
                "elapsed_ms": round(elapsed * 1000, 1),
                "headers": dict(resp.headers),
                "body": body,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        body = e.read().decode("utf-8", errors="replace")
        return {
            "status": e.code,
            "elapsed_ms": round(elapsed * 1000, 1),
            "headers": dict(e.headers),
            "body": body,
            "error": f"HTTP {e.code}",
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "status": 0,
            "elapsed_ms": round(elapsed * 1000, 1),
            "headers": {},
            "body": "",
            "error": str(e),
        }


def _rate_limit_headers(resp_headers: dict) -> dict:
    """レート制限関連のヘッダーを抽出。"""
    out = {}
    for k, v in resp_headers.items():
        kl = k.lower()
        if any(x in kl for x in ["rate", "limit", "retry-after"]):
            out[k] = v
    return out


def _print_items(items: list[dict], source_name: str) -> None:
    """取得したアイテム一覧を印刷。"""
    if not items:
        _safe_print(f"  [{source_name}] No items returned")
        return
    _safe_print(f"  [{source_name}] --- {len(items)} items ---")
    for i, item in enumerate(items, 1):
        title = item.get("title", "(no title)")
        url = item.get("url", "")
        score = item.get("score", "")
        _safe_print(f"    {i}. [{score if score else ' '}] {title}")
        if url:
            _safe_print(f"       {url}")
    _safe_print(f"  [{source_name}] --- end ---")


# ============================================================
# 各ソースのテスト関数
# ============================================================

def test_hacker_news() -> dict:
    """Hacker News Firebase API"""
    _safe_print("\n=== 1. Hacker News (Firebase API) ===")
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    _safe_print(f"  URL: {url}")

    resp = fetch_full(url)
    _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
    rl = _rate_limit_headers(resp["headers"])
    if rl:
        _safe_print(f"  Rate limit: {rl}")

    items = []
    if resp["status"] == 200:
        story_ids = json.loads(resp["body"])
        # 上位3件の詳細を取得
        for sid in story_ids[:3]:
            item_resp = fetch_full(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            if item_resp["status"] == 200:
                data = json.loads(item_resp["body"])
                if data.get("type") == "story":
                    items.append({
                        "title": data.get("title", ""),
                        "url": data.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "score": data.get("score", 0),
                    })
                    time.sleep(0.05)

    _print_items(items, "HN")

    return {
        "source": "hacker_news",
        "url": url,
        "status": resp["status"],
        "elapsed_ms": resp["elapsed_ms"],
        "error": resp["error"],
        "items": items,
        "items_count": len(items),
        "rate_limit_headers": rl,
    }


def test_reddit() -> dict:
    """Reddit .json エンドポイント"""
    _safe_print("\n=== 2. Reddit (.json endpoint) ===")
    url = "https://www.reddit.com/r/MachineLearning/hot.json?limit=3&raw_json=1"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    _safe_print(f"  URL: {url}")

    resp = fetch_full(url, headers=headers)
    _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
    rl = _rate_limit_headers(resp["headers"])
    if rl:
        _safe_print(f"  Rate limit: {rl}")
    if resp["error"]:
        _safe_print(f"  Error: {resp['error']}")

    items = []
    if resp["status"] == 200:
        data = json.loads(resp["body"])
        for post in data.get("data", {}).get("children", []):
            pd = post.get("data", {})
            items.append({
                "title": pd.get("title", ""),
                "url": f"https://www.reddit.com{pd.get('permalink', '')}",
                "score": pd.get("score", 0),
            })

    _print_items(items, "Reddit")

    return {
        "source": "reddit",
        "url": url,
        "status": resp["status"],
        "elapsed_ms": resp["elapsed_ms"],
        "error": resp["error"],
        "items": items,
        "items_count": len(items),
        "rate_limit_headers": rl,
    }


def test_e621() -> dict:
    """e621 REST API"""
    _safe_print("\n=== 3. e621 (REST API) ===")
    tags = urllib.parse.quote("kemono rating:safe order:date")
    url = f"https://e621.net/posts.json?tags={tags}&limit=3"
    headers = {"User-Agent": USER_AGENT}
    _safe_print(f"  URL: {url}")

    resp = fetch_full(url, headers=headers)
    _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
    rl = _rate_limit_headers(resp["headers"])
    if rl:
        _safe_print(f"  Rate limit: {rl}")

    items = []
    if resp["status"] == 200:
        data = json.loads(resp["body"])
        for post in data.get("posts", []):
            pid = post.get("id", "")
            general = post.get("tags", {}).get("general", [])[:5]
            species = post.get("tags", {}).get("species", [])[:3]
            tag_summary = ", ".join(general + species)
            items.append({
                "title": f"Post #{pid}: {tag_summary}",
                "url": f"https://e621.net/posts/{pid}",
                "score": post.get("score", 0),
                "rating": post.get("rating", ""),
            })

    _print_items(items, "e621")

    return {
        "source": "e621",
        "url": url,
        "status": resp["status"],
        "elapsed_ms": resp["elapsed_ms"],
        "error": resp["error"],
        "items": items,
        "items_count": len(items),
        "rate_limit_headers": rl,
    }


def test_rss_feeds() -> dict:
    """RSS フィード（Zenn, Qiita, PokéCommunity）"""
    feeds = [
        {"name": "Zenn AI", "url": "https://zenn.dev/topics/ai/feed"},
        {"name": "Qiita AI", "url": "https://qiita.com/tags/ai/feed"},
        {"name": "PokéCommunity", "url": "https://www.pokecommunity.com/forums/art-studio.21/index.rss"},
    ]

    all_items = []
    results = []

    for feed in feeds:
        _safe_print(f"\n=== RSS: {feed['name']} ===")
        _safe_print(f"  URL: {feed['url']}")

        resp = fetch_full(feed["url"], headers={"User-Agent": USER_AGENT})
        _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
        rl = _rate_limit_headers(resp["headers"])
        if rl:
            _safe_print(f"  Rate limit: {rl}")

        items = []
        if resp["status"] == 200:
            try:
                root = ET.fromstring(resp["body"])
                # RSS 2.0
                for item_el in root.findall(".//item")[:3]:
                    title_el = item_el.find("title")
                    link_el = item_el.find("link")
                    if title_el is not None and title_el.text:
                        items.append({
                            "title": title_el.text.strip(),
                            "url": link_el.text.strip() if link_el is not None and link_el.text else "",
                            "score": 0,
                        })
                # Atom (fallback)
                if not items:
                    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:3]:
                        title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                        if title_el is not None and title_el.text:
                            items.append({
                                "title": title_el.text.strip(),
                                "url": link_el.get("href", "") if link_el is not None else "",
                                "score": 0,
                            })
            except ET.ParseError as e:
                _safe_print(f"  Parse error: {e}")

        _print_items(items, feed["name"])
        all_items.extend(items)
        results.append({
            "source": f"rss_{feed['name'].lower().replace(' ', '_')}",
            "url": feed["url"],
            "status": resp["status"],
            "elapsed_ms": resp["elapsed_ms"],
            "error": resp.get("error"),
            "items": items,
            "items_count": len(items),
            "rate_limit_headers": rl,
        })
        time.sleep(0.3)

    return results


def test_github_search() -> dict:
    """GitHub Search API"""
    _safe_print("\n=== 6. GitHub Search API ===")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    query = urllib.parse.quote("kemono in:name,description")
    url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc&per_page=3"
    _safe_print(f"  URL: {url}")
    _safe_print(f"  Auth: {'Bearer token' if github_token else 'unauthenticated'}")

    resp = fetch_full(url, headers=headers)
    _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
    rl = _rate_limit_headers(resp["headers"])
    if rl:
        _safe_print(f"  Rate limit: {rl}")

    items = []
    if resp["status"] == 200:
        data = json.loads(resp["body"])
        for repo in data.get("items", []):
            items.append({
                "title": f"{repo.get('full_name', '')}: {repo.get('description', '')}",
                "url": repo.get("html_url", ""),
                "score": repo.get("stargazers_count", 0),
            })

    _print_items(items, "GitHub")

    return {
        "source": "github_search",
        "url": url,
        "authenticated": bool(github_token),
        "status": resp["status"],
        "elapsed_ms": resp["elapsed_ms"],
        "error": resp["error"],
        "items": items,
        "items_count": len(items),
        "rate_limit_headers": rl,
    }


def test_kemono_api() -> dict:
    """Kemono API"""
    _safe_print("\n=== 7. Kemono API ===")
    url = "https://kemono.cr/api/v1/posts"
    headers = {"User-Agent": USER_AGENT}
    _safe_print(f"  URL: {url}")

    resp = fetch_full(url, headers=headers)
    _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
    rl = _rate_limit_headers(resp["headers"])
    if rl:
        _safe_print(f"  Rate limit: {rl}")

    items = []
    if resp["status"] == 200:
        data = json.loads(resp["body"])
        for post in data.get("posts", [])[:3]:
            pid = post.get("id", "")
            service = post.get("service", "unknown")
            creator = post.get("user", "unknown")
            title = post.get("title", "")[:100]
            items.append({
                "title": f"[{service}] {creator}: {title}" if title else f"[{service}] {creator}",
                "url": f"https://kemono.cr/{service}/user/{creator}/post/{pid}",
                "score": 0,
            })

    _print_items(items, "Kemono")

    return {
        "source": "kemono_api",
        "url": url,
        "status": resp["status"],
        "elapsed_ms": resp["elapsed_ms"],
        "error": resp["error"],
        "items": items,
        "items_count": len(items),
        "rate_limit_headers": rl,
    }


def test_bluesky() -> dict:
    """Bluesky AT Protocol Search API"""
    _safe_print("\n=== 8. Bluesky Search API ===")
    query = urllib.parse.quote("LLM AI")
    url = f"https://public.api.bsky.app/xrpc/app.bsky.unspecced.searchPostsLazy?q={query}&limit=3"
    headers = {"User-Agent": USER_AGENT}
    _safe_print(f"  URL: {url}")

    resp = fetch_full(url, headers=headers)
    _safe_print(f"  Status: {resp['status']}, Time: {resp['elapsed_ms']}ms")
    rl = _rate_limit_headers(resp["headers"])
    if rl:
        _safe_print(f"  Rate limit: {rl}")
    if resp["error"]:
        _safe_print(f"  Error: {resp['error']}")

    items = []
    if resp["status"] == 200:
        data = json.loads(resp["body"])
        for post in data.get("posts", []):
            author = post.get("author", {}).get("handle", "unknown")
            record = post.get("record", {})
            text = record.get("text", "")[:80]
            uri = post.get("uri", "")
            rkey = uri.split(":")[-1] if ":" in uri else ""
            items.append({
                "title": f"@{author}: {text}",
                "url": f"https://bsky.app/profile/{author}/post/{rkey}",
                "score": 0,
            })

    _print_items(items, "Bluesky")

    return {
        "source": "bluesky",
        "url": url,
        "status": resp["status"],
        "elapsed_ms": resp["elapsed_ms"],
        "error": resp["error"],
        "items": items,
        "items_count": len(items),
        "rate_limit_headers": rl,
    }


# ============================================================
# テスト実行
# ============================================================

TESTS = [
    ("hacker-news", test_hacker_news),
    ("reddit", test_reddit),
    ("e621", test_e621),
    ("rss-feeds", test_rss_feeds),
    ("github-search", test_github_search),
    ("kemono-api", test_kemono_api),
    ("bluesky", test_bluesky),
]


def print_summary(results: list[dict]) -> None:
    """テスト結果のサマリーを表示"""
    _safe_print("\n" + "=" * 70)
    _safe_print("TEST SUMMARY")
    _safe_print("=" * 70)
    _safe_print(f"{'Source':<20} {'Status':<8} {'Time(ms)':<10} {'Items':<8} {'Rate Limit'}")
    _safe_print("-" * 70)

    for r in results:
        rl = r.get("rate_limit_headers", {})
        rl_str = "yes" if rl else "none"
        _safe_print(f"{r['source']:<20} {r['status']:<8} {r['elapsed_ms']:<10} {r['items_count']:<8} {rl_str}")
        if r.get("error"):
            _safe_print(f"  ERROR: {r['error']}")
        if rl:
            for k, v in rl.items():
                _safe_print(f"  {k}: {v}")

    passed = sum(1 for r in results if 200 <= r["status"] < 300)
    _safe_print("-" * 70)
    _safe_print(f"Passed: {passed}/{len(results)}")

    rl_sources = [r["source"] for r in results if r.get("rate_limit_headers")]
    if rl_sources:
        _safe_print(f"\nRate limit headers found: {', '.join(rl_sources)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="リアルAPIテスト")
    parser.add_argument("--source", choices=[t[0] for t in TESTS], help="単一ソースのみテスト")
    parser.add_argument("--save", action="store_true", help="結果をJSONに保存")
    args = parser.parse_args()

    results = []

    if args.source:
        test_name, test_func = next((t for t in TESTS if t[0] == args.source), None)
        result = test_func()
        if isinstance(result, list):
            results.extend(result)
        else:
            results.append(result)
    else:
        for test_name, test_func in TESTS:
            result = test_func()
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
            time.sleep(0.5)

    print_summary(results)

    if args.save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        out_path = os.path.join(RESULTS_DIR, f"api_test_{ts}.json")
        save_data = []
        for r in results:
            save_entry = {k: v for k, v in r.items() if k != "headers"}
            save_data.append(save_entry)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        _safe_print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
