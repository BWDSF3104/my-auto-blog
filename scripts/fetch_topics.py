"""
fetch_topics.py — 設定不要（APIキー不要）でトレンド情報を収集するスクリプト

収集先:
  1. Hacker News  : Firebase API (認証不要・CORS対応)
  2. Reddit       : .json エンドポイント (User-Agent 必要)
  3. e621         : REST API の公開検索 (User-Agent 必要)
  4. RSS各種      : Zenn / Qiita / GitHub Trending
  5. GitHub Search: REST API (未認証 60req/h)

出力: data/latest_topics.json
"""

import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# --------------------------------------------------
# 定数
# --------------------------------------------------
OUTPUT_PATH = os.path.join("data", "latest_topics.json")
USER_AGENT = "my-auto-blog/1.0 (https://github.com)"  # Reddit / e621 用

# 収集する Subreddit 一覧（認証不要）
REDDIT_SUBS = [
    "kemono",       # ケモノ全般
    "furry",        # Furry 全般
    "pokemon",      # ポケモン
    "furry_irl",    # Furry 日常
    "localllama",   # LLM / AI (最新技術)
    "MachineLearning",
]

# e621 タグ検索 (公開 GET / 認証不要)
E621_TAGS = [
    "kemono order:date",
    "dragon order:date",
    "pokemon order:date",
]

# RSS フィード一覧
RSS_FEEDS = [
    {
        "name": "Zenn AI",
        "url": "https://zenn.dev/topics/ai/feed",
        "category": "tech",
    },
    {
        "name": "Zenn LLM",
        "url": "https://zenn.dev/topics/llm/feed",
        "category": "tech",
    },
    {
        "name": "Qiita AI",
        "url": "https://qiita.com/tags/ai/feed",
        "category": "tech",
    },
    {
        "name": "Qiita Python",
        "url": "https://qiita.com/tags/python/feed",
        "category": "tech",
    },
]

# Hacker News: トップ記事
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

# GitHub Search: furry / kemono / pokemon 関連リポジトリ
GITHUB_SEARCH_QUERIES = [
    "kemono+in:name,description",
    "furry+language:python",
    "pokemon+language:typescript",
]

# --------------------------------------------------
# ユーティリティ
# --------------------------------------------------

def fetch_json(url: str, headers: dict = None, timeout: int = 15) -> dict | list | None:
    """シンプルな JSON フェッチ。失敗時は None を返す。"""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        print(f"  [WARN] fetch_json failed for {url}: {e}")
        return None


def fetch_rss(url: str, timeout: int = 15) -> list[dict]:
    """RSS / Atom フィードをパースしてタイトル+URL のリストを返す。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
        root = ET.fromstring(content)
    except Exception as e:
        print(f"  [WARN] fetch_rss failed for {url}: {e}")
        return []

    items = []
    # RSS 2.0
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is not None and title_el.text:
            items.append({
                "title": title_el.text.strip(),
                "url": link_el.text.strip() if link_el is not None and link_el.text else "",
            })
    # Atom
    if not items:
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            title_el = entry.find("{http://www.w3.org/2005/Atom}title")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            if title_el is not None and title_el.text:
                href = link_el.get("href", "") if link_el is not None else ""
                items.append({
                    "title": title_el.text.strip(),
                    "url": href,
                })
    return items[:10]  # 最大 10 件


# --------------------------------------------------
# 各情報源の収集関数
# --------------------------------------------------

def collect_hacker_news(limit: int = 10) -> list[dict]:
    """Hacker News のトップストーリーを取得する。"""
    print("[HN] Fetching top stories...")
    story_ids = fetch_json(HN_TOP_STORIES_URL)
    if not story_ids:
        return []

    results = []
    for sid in story_ids[:limit * 2]:  # 多めに取って失敗をカバー
        if len(results) >= limit:
            break
        item = fetch_json(HN_ITEM_URL.format(id=sid))
        if item and item.get("type") == "story" and item.get("title"):
            results.append({
                "title": item["title"],
                "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                "score": item.get("score", 0),
                "source": "HackerNews",
                "category": "tech",
            })
        time.sleep(0.05)  # 過負荷防止

    print(f"  -> {len(results)} stories collected")
    return results


def collect_reddit(limit_per_sub: int = 5) -> list[dict]:
    """Reddit の各 Subreddit から hot 投稿を取得する。"""
    # GitHub Actions 環境に近い UA を指定することで 403 を回避しやすくなる
    reddit_ua = "Mozilla/5.0 (compatible; my-auto-blog/1.0; +https://github.com)"
    headers = {
        "User-Agent": reddit_ua,
        "Accept": "application/json",
    }
    results = []

    for sub in REDDIT_SUBS:
        print(f"[Reddit] Fetching r/{sub}...")
        # 通常エンドポイント → old.reddit.com の順にフォールバック
        urls_to_try = [
            f"https://www.reddit.com/r/{sub}/hot.json?limit={limit_per_sub}&raw_json=1",
            f"https://old.reddit.com/r/{sub}/hot.json?limit={limit_per_sub}&raw_json=1",
        ]
        data = None
        for url in urls_to_try:
            data = fetch_json(url, headers=headers)
            if data:
                break
            time.sleep(1.0)

        if not data:
            continue
        try:
            posts = data["data"]["children"]

        except (KeyError, TypeError):
            continue

        for post in posts:
            pd = post.get("data", {})
            title = pd.get("title", "")
            permalink = pd.get("permalink", "")
            if title:
                results.append({
                    "title": title,
                    "url": f"https://www.reddit.com{permalink}",
                    "score": pd.get("score", 0),
                    "source": f"Reddit/r/{sub}",
                    "category": _categorize_subreddit(sub),
                })
        time.sleep(0.5)  # Reddit レート制限対策

    print(f"  -> {len(results)} Reddit posts collected")
    return results


def _categorize_subreddit(sub: str) -> str:
    sub_lower = sub.lower()
    if sub_lower in ("localllama", "machinelearning"):
        return "tech"
    if sub_lower in ("kemono", "furry", "furry_irl"):
        return "kemono"
    if sub_lower == "pokemon":
        return "pokemon"
    return "other"


def collect_e621(limit_per_tag: int = 5) -> list[dict]:
    """e621 の公開 REST API で最新投稿を取得する（認証不要）。"""
    headers = {"User-Agent": USER_AGENT}
    results = []

    for tag_query in E621_TAGS:
        print(f"[e621] Fetching tag: {tag_query}...")
        encoded = urllib.parse.quote(tag_query)
        url = f"https://e621.net/posts.json?tags={encoded}&limit={limit_per_tag}"
        data = fetch_json(url, headers=headers)
        if not data:
            continue
        posts = data.get("posts", [])
        for post in posts:
            pid = post.get("id")
            tags_general = post.get("tags", {}).get("general", [])
            species_tags = post.get("tags", {}).get("species", [])
            tag_summary = ", ".join((tags_general + species_tags)[:8])
            results.append({
                "title": f"e621 post #{pid}: {tag_summary}",
                "url": f"https://e621.net/posts/{pid}",
                "score": post.get("score", {}).get("total", 0),
                "source": "e621",
                "category": "kemono",
            })
        time.sleep(1.0)  # e621 推奨: 1req/s

    print(f"  -> {len(results)} e621 posts collected")
    return results


def collect_rss_feeds() -> list[dict]:
    """RSS / Atom フィードからトピックを収集する。"""
    results = []

    for feed in RSS_FEEDS:
        print(f"[RSS] Fetching {feed['name']}...")
        items = fetch_rss(feed["url"])
        for item in items:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "score": 0,
                "source": feed["name"],
                "category": feed["category"],
            })
        time.sleep(0.3)

    print(f"  -> {len(results)} RSS items collected")
    return results


def collect_github_trending(limit_per_query: int = 5) -> list[dict]:
    """GitHub Search API でリポジトリを検索する（未認証: 60req/h）。"""
    # GITHUB_TOKEN が使えれば自動的に付与してレート制限を緩和する
    github_token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    results = []
    for query in GITHUB_SEARCH_QUERIES:
        print(f"[GitHub] Searching: {query}...")
        encoded = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=updated&order=desc&per_page={limit_per_query}"
        data = fetch_json(url, headers=headers)
        if not data:
            continue
        items = data.get("items", [])
        for repo in items:
            results.append({
                "title": f"{repo.get('full_name', '')}: {repo.get('description', '')}",
                "url": repo.get("html_url", ""),
                "score": repo.get("stargazers_count", 0),
                "source": "GitHub",
                "category": _categorize_github_query(query),
            })
        time.sleep(1.0)

    print(f"  -> {len(results)} GitHub repos collected")
    return results


def _categorize_github_query(query: str) -> str:
    q = query.lower()
    if "pokemon" in q:
        return "pokemon"
    if "furry" in q or "kemono" in q:
        return "kemono"
    return "tech"


# --------------------------------------------------
# メイン処理
# --------------------------------------------------

def main():
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)

    print("=" * 50)
    print(f"fetch_topics.py 実行開始: {now.isoformat()}")
    print("=" * 50)

    all_topics: list[dict] = []

    # 1. Hacker News
    try:
        all_topics.extend(collect_hacker_news(limit=10))
    except Exception as e:
        print(f"[ERROR] HackerNews: {e}")

    # 2. Reddit
    try:
        all_topics.extend(collect_reddit(limit_per_sub=5))
    except Exception as e:
        print(f"[ERROR] Reddit: {e}")

    # 3. e621
    try:
        all_topics.extend(collect_e621(limit_per_tag=5))
    except Exception as e:
        print(f"[ERROR] e621: {e}")

    # 4. RSS
    try:
        all_topics.extend(collect_rss_feeds())
    except Exception as e:
        print(f"[ERROR] RSS: {e}")

    # 5. GitHub
    try:
        all_topics.extend(collect_github_trending(limit_per_query=5))
    except Exception as e:
        print(f"[ERROR] GitHub: {e}")

    # カテゴリ別に整理
    output = {
        "fetched_at": now.isoformat(),
        "total": len(all_topics),
        "by_category": {
            "tech": [],
            "kemono": [],
            "pokemon": [],
            "other": [],
        },
        "all": all_topics,
    }
    for topic in all_topics:
        cat = topic.get("category", "other")
        if cat in output["by_category"]:
            output["by_category"][cat].append(topic)
        else:
            output["by_category"]["other"].append(topic)

    # 出力
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"完了: {len(all_topics)} 件のトピックを {OUTPUT_PATH} に保存しました")
    for cat, items in output["by_category"].items():
        print(f"  [{cat}] {len(items)} 件")
    print("=" * 50)


if __name__ == "__main__":
    main()
