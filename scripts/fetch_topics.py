"""
fetch_topics.py — 設定不要（APIキー不要）でトレンド情報を収集するスクリプト

収集先:
  1. Hacker News  : Firebase API (認証不要・CORS対応)
  2. Reddit       : .json エンドポイント (User-Agent 必要)
  3. e621         : REST API の公開検索 (User-Agent 必要)
  4. RSS各種      : Zenn / Qiita / GitHub Trending
  5. GitHub Search: REST API (未認証 60req/h)

出力: data/topics/{YYYY-MM-DD_HHMMSS}.json + data/topics/latest.json (コピー)
"""

import json
import os
import shutil
import sys
import time
from dotenv import load_dotenv
load_dotenv()
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# Windows コンソールで cp932 → UTF-8 変換エラーを防ぐ
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# --------------------------------------------------
# 定数
# --------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_DIR = os.path.join(PROJECT_DIR, "data", "topics")
OUTPUT_PATH = os.path.join(TOPICS_DIR, "latest.json")
USER_AGENT = "my-auto-blog/1.0 (https://github.com)"  # Reddit / e621 用
TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "24"))  # データの有効期間（時間）

# 収集する Subreddit 一覧（認証不要）
REDDIT_SUBS = [
    {"name": "kemono", "category": "kemono"},
    {"name": "furry", "category": "kemono"},
    {"name": "pokemon", "category": "pokemon"},
    {"name": "furry_irl", "category": "kemono"},
    {"name": "localllama", "category": "tech"},
    {"name": "MachineLearning", "category": "tech"},
]

# e621 タグ検索 (公開 GET / 認証不要)
# order:date = 最新順, order:score = 人気順 (トレンド作品追跡用)
# rating:safe または rating:questionable に限定して NSFW フィルタ回避
E621_TAGS = [
    {"tags": "kemono rating:safe order:date", "category": "kemono"},
    {"tags": "dragon rating:safe order:date", "category": "kemono"},
    {"tags": "kemono rating:questionable order:score", "category": "kemono"},
    {"tags": "furry rating:safe order:score", "category": "kemono"},
    {"tags": "wolf rating:safe order:score", "category": "kemono"},
    {"tags": "fox rating:safe order:score", "category": "kemono"},
    {"tags": "rabbit rating:safe order:score", "category": "kemono"},
    {"tags": "pokemon rating:safe order:date", "category": "pokemon"},
]

# キャラクター特徴集計用ファイル
CHARACTER_FEATURES_PATH = os.path.join(PROJECT_DIR, "data", "character_features.json")

# e621 タグのカテゴリ分類（キャラクター特徴抽出用）
# species: 種族, general: 身体的特徴・色, character: キャラクター名, copyright: 作品名
CHARACTER_FEATURE_CATEGORIES = ["species", "general"]

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
    {
        "name": "PokéCommunity Art Studio",
        "url": "https://www.pokecommunity.com/forums/art-studio.21/index.rss",
        "category": "pokemon",
    },
    {
        "name": "PokeBeach News",
        "url": "https://kaprestridge.github.io/pokebeach-news-feed/feed.xml",
        "category": "pokemon",
    },
    {
        "name": "PokemonBlog",
        "url": "https://pokemonblog.com/feed",
        "category": "pokemon",
    },
    {
        "name": "PocketMonsters",
        "url": "https://pocketmonsters.net/rss",
        "category": "pokemon",
    },
]

# Hacker News: トップ記事
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_CATEGORIES = ["tech"]

# GitHub Search: furry / kemono / pokemon 関連リポジトリ
GITHUB_SEARCH_QUERIES = [
    {"query": "kemono+in:name,description", "category": "kemono"},
    {"query": "furry+language:python", "category": "kemono"},
    {"query": "pokemon+language:typescript", "category": "pokemon"},
]

# Bluesky 検索キーワード
BLUESKY_SEARCHES = [
    {"query": "LLM AI", "category": "tech"},
    {"query": "kemono furry art", "category": "kemono"},
    {"query": "kemono commission", "category": "kemono"},
    {"query": "furry artist", "category": "kemono"},
    {"query": "pokemon", "category": "pokemon"},
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
                "title": title_el.text.strip().encode("utf-8", errors="replace").decode("utf-8"),
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
                    "title": title_el.text.strip().encode("utf-8", errors="replace").decode("utf-8"),
                    "url": href,
                })
    return items[:10]  # 最大 10 件


# --------------------------------------------------
# 各情報源の収集関数
# --------------------------------------------------

def collect_hacker_news(limit: int = 10, categories: list[str] = None) -> list[dict]:
    """Hacker News のトップストーリーを取得する。categories が指定された場合は tech カテゴリが含まれている時のみ収集。"""
    if categories and "tech" not in categories:
        return []
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


def collect_reddit(limit_per_sub: int = 5, categories: list[str] = None) -> list[dict]:
    """Reddit の各 Subreddit から hot 投稿を取得する。categories が指定された場合は該当カテゴリのみ収集。"""
    reddit_ua = "Mozilla/5.0 (compatible; my-auto-blog/1.0; +https://github.com)"
    headers = {
        "User-Agent": reddit_ua,
        "Accept": "application/json",
    }
    results = []

    for sub_config in REDDIT_SUBS:
        sub = sub_config["name"]
        cat = sub_config.get("category", "other")
        if categories and cat not in categories:
            continue
        print(f"[Reddit] Fetching r/{sub}...")
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
                    "category": cat,
                })
        time.sleep(0.5)

    print(f"  -> {len(results)} Reddit posts collected")
    return results


def _is_nsfw_post(post: dict) -> bool:
    """e621 投稿が NSFW（rating: explicit）または既知の NSFW タグを含む場合 True"""
    rating = post.get("rating", "")
    if rating == "e":
        return True
    nsfw_tags = {
        "sexual", "sex", "bare_legs", "bare_thighs", "bare_hips", "bare_butt",
        "breast_exposure", "genital_exposure", "penis", "vagina", "ass",
        "boobs", "pussy", "dicexdick", "bare_chest", "exposed_nipple",
        "loli", "shota", "underage", "rape",
    }
    all_tags = set()
    for tag_list in post.get("tags", {}).values():
        all_tags.update(tag_list)
    if all_tags & nsfw_tags:
        return True
    return False


def _aggregate_and_save_character_features(raw_tags: list[dict]) -> None:
    """e621 の生タグからキャラクター特徴を種別ごとに集計して保存する。"""
    from collections import Counter

    # 種別ごとのタグ集計
    species_counter = Counter()
    color_counter = Counter()
    physical_counter = Counter()

    # 色のパターン（general タグから抽出）
    color_patterns = ["_fur", "_eyes", "_body", "_hair", "_scale", "_skin", "_wing", "_tail"]
    # 種族のパターン（species タグから抽出）
    species_patterns = ["wolf", "fox", "dragon", "rabbit", "cat", "dog", "tiger", "lion", "bear",
                        "panther", "hyena", "coyote", "jackal", "fox", "vulpine", "canine", "feline",
                        "equine", "avian", "reptile", "amphibian", "kemono", "pokemon", "eevee",
                        "canid", "mammal", "pokemon_(species)"]

    for tag_data in raw_tags:
        tags = tag_data.get("tags", {})

        # species タグの集計
        for species in tags.get("species", []):
            species_counter[species] += 1

        # general タグから色と身体的特徴を抽出
        for tag in tags.get("general", []):
            # 色の特徴
            is_color = any(tag.endswith(pat) for pat in color_patterns)
            if is_color:
                color_counter[tag] += 1
            # 身体的特徴（色以外の general タグ）
            else:
                physical_counter[tag] += 1

    # 既存データをロードして更新
    existing = {}
    if os.path.exists(CHARACTER_FEATURES_PATH):
        try:
            with open(CHARACTER_FEATURES_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    # 集計結果をマージ（既存のカウンターに追加）
    if "species" in existing:
        existing["species"].update(species_counter)
    else:
        existing["species"] = dict(species_counter)

    if "colors" in existing:
        existing["colors"].update(color_counter)
    else:
        existing["colors"] = dict(color_counter)

    if "physical_features" in existing:
        existing["physical_features"].update(physical_counter)
    else:
        existing["physical_features"] = dict(physical_counter)

    # 更新時刻を記録
    from datetime import datetime, timezone
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    existing["total_posts_analyzed"] = sum(existing["species"].values())

    # ファイルに保存
    os.makedirs(os.path.dirname(CHARACTER_FEATURES_PATH), exist_ok=True)
    with open(CHARACTER_FEATURES_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"  [char-features] 特徴集計を保存しました ({len(raw_tags)} posts)")


def collect_e621(limit_per_tag: int = 5, categories: list[str] = None) -> list[dict]:
    """e621 の公開 REST API で最新投稿を取得する（認証不要）。NSFW 投稿はフィルタする。"""
    headers = {"User-Agent": USER_AGENT}
    results = []
    filtered = 0
    raw_tags = []

    for tag_config in E621_TAGS:
        tag_query = tag_config["tags"]
        cat = tag_config.get("category", "kemono")
        if categories and cat not in categories:
            continue
        print(f"[e621] Fetching tag: {tag_query}...")
        encoded = urllib.parse.quote(tag_query)
        url = f"https://e621.net/posts.json?tags={encoded}&limit={limit_per_tag}"
        data = fetch_json(url, headers=headers)
        if not data:
            continue
        posts = data.get("posts", [])
        for post in posts:
            if _is_nsfw_post(post):
                filtered += 1
                continue
            pid = post.get("id")
            tags_general = post.get("tags", {}).get("general", [])
            species_tags = post.get("tags", {}).get("species", [])
            tag_summary = ", ".join((tags_general + species_tags)[:8])
            results.append({
                "title": f"e621 post #{pid}: {tag_summary}",
                "url": f"https://e621.net/posts/{pid}",
                "score": post.get("score", 0) if isinstance(post.get("score"), (int, float)) else post.get("score", {}).get("total", 0),
                "source": "e621",
                "category": cat,
                "rating": post.get("rating", "q"),
            })
            # 生タグを保存（キャラクター特徴集計用）
            raw_tags.append({
                "post_id": pid,
                "tags": post.get("tags", {}),
            })
        time.sleep(1.0)

    if filtered:
        print(f"  [NSFW] {filtered} 件の投稿をフィルタしました")
    print(f"  -> {len(results)} e621 posts collected")

    # キャラクター特徴を集計して保存
    if raw_tags:
        _aggregate_and_save_character_features(raw_tags)

    return results


def _safe_print(text: str) -> None:
    """cp932 コンソールでも失敗しない print のラッパー。"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("cp932", errors="replace").decode("cp932", errors="replace"))

def collect_rss_feeds(categories: list[str] = None) -> list[dict]:
    """RSS / Atom フィードからトピックを収集する。categories が指定された場合は該当カテゴリのみ収集。"""
    results = []

    for feed in RSS_FEEDS:
        cat = feed.get("category", "other")
        if categories and cat not in categories:
            continue
        _safe_print(f"[RSS] Fetching {feed['name']}...")
        items = fetch_rss(feed["url"])
        for item in items:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "score": 0,
                "source": feed["name"],
                "category": cat,
            })
        time.sleep(0.3)

    _safe_print(f"  -> {len(results)} RSS items collected")
    return results


def collect_github_trending(limit_per_query: int = 5, categories: list[str] = None) -> list[dict]:
    """GitHub Search API でリポジトリを検索する（未認証: 60req/h）。"""
    github_token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    results = []
    for query_config in GITHUB_SEARCH_QUERIES:
        query = query_config["query"]
        cat = query_config.get("category", "kemono")
        if categories and cat not in categories:
            continue
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
                "category": cat,
            })
        time.sleep(1.0)

    print(f"  -> {len(results)} GitHub repos collected")
    return results


def collect_kemono_api(limit: int = 10, categories: list[str] = None) -> list[dict]:
    """Kemono (kemono.cr) の公開 API で最近の投稿を取得する（認証不要）。"""
    if categories and "kemono" not in categories:
        return []
    print("[Kemono] Fetching recent posts from API...")
    headers = {"User-Agent": USER_AGENT}
    results = []
    data = fetch_json("https://kemono.cr/api/v1/posts", headers=headers)
    if not data:
        print("  -> 0 Kemono posts collected")
        return results
    posts = data.get("posts", [])
    for post in posts:
        if len(results) >= limit:
            break
        pid = post.get("id", "")
        service = post.get("service", "unknown")
        creator = post.get("user", "unknown")
        title = post.get("title", "")[:100]
        if not pid:
            continue
        results.append({
            "title": f"[{service}] {creator}: {title}" if title else f"[{service}] {creator}",
            "url": f"https://kemono.cr/{service}/user/{creator}/post/{pid}",
            "score": 0,
            "source": "Kemono",
            "category": "kemono",
        })
    print(f"  -> {len(results)} Kemono posts collected")
    return results


def collect_bluesky(limit_per_query: int = 5, categories: list[str] = None) -> list[dict]:
    """Bluesky (AT Protocol) の公開検索エンドポイントで投稿を検索する（認証不要）。"""
    results = []

    for search in BLUESKY_SEARCHES:
        query = search["query"]
        category = search["category"]
        if categories and category not in categories:
            continue
        print(f"[Bluesky] Searching: {query}...")
        encoded = urllib.parse.quote(query)
        url = f"https://public.api.bsky.app/xrpc/app.bsky.unspecced.searchPostsLazy?q={encoded}&limit={limit_per_query}"
        data = fetch_json(url, headers={"User-Agent": USER_AGENT})
        if not data:
            continue
        posts = data.get("posts", [])
        for post in posts:
            uri = post.get("uri", "")
            cid = post.get("cid", "")
            record = post.get("record", {})
            text = record.get("text", "")[:200]
            author = post.get("author", {}).get("handle", "unknown")
            if not uri:
                continue
            rkey = uri.split(':')[-1] if ':' in uri else uri
            if not rkey:
                continue
            results.append({
                "title": f"@{author}: {text[:80]}",
                "url": f"https://bsky.app/profile/{author}/post/{rkey}",
                "score": 0,
                "source": "Bluesky",
                "category": category,
            })
        time.sleep(0.5)

    print(f"  -> {len(results)} Bluesky posts collected")
    return results


# --------------------------------------------------
# カテゴリ マッピング
# --------------------------------------------------

# prompt_type -> 必要なカテゴリ一覧
PROMPT_CATEGORIES = {
    "default": ["tech"],
    "ai_deep": ["tech"],
    "kemono_story": ["kemono", "pokemon"],
}

# --------------------------------------------------
# メイン処理
# --------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="トレンド情報を収集")
    parser.add_argument("--categories", nargs="+", help="収集するカテゴリ (例: tech kemono pokemon)")
    parser.add_argument("--prompt-type", choices=list(PROMPT_CATEGORIES.keys()),
                        help="プロンプトタイプを指定すると対応カテゴリが自動選択される")
    args = parser.parse_args()

    # カテゴリを決定
    categories: list[str] = None
    if args.categories:
        categories = args.categories
    elif args.prompt_type:
        categories = PROMPT_CATEGORIES.get(args.prompt_type, None)
        if categories:
            print(f"[INFO] prompt_type={args.prompt_type} -> categories={categories}")

    if categories:
        print(f"[INFO] カテゴリフィルタ有効: {categories}")

    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)

    print("=" * 50)
    print(f"fetch_topics.py 実行開始: {now.isoformat()}")
    print("=" * 50)

    all_topics: list[dict] = []

    # 1. Hacker News
    try:
        all_topics.extend(collect_hacker_news(limit=10, categories=categories))
    except Exception as e:
        print(f"[ERROR] HackerNews: {e}")

    # 2. Reddit
    try:
        all_topics.extend(collect_reddit(limit_per_sub=5, categories=categories))
    except Exception as e:
        print(f"[ERROR] Reddit: {e}")

    # 3. e621
    try:
        all_topics.extend(collect_e621(limit_per_tag=5, categories=categories))
    except Exception as e:
        print(f"[ERROR] e621: {e}")

    # 4. Kemono API
    try:
        all_topics.extend(collect_kemono_api(limit=10, categories=categories))
    except Exception as e:
        print(f"[ERROR] Kemono API: {e}")

    # 5. RSS
    try:
        all_topics.extend(collect_rss_feeds(categories=categories))
    except Exception as e:
        print(f"[ERROR] RSS: {e}")

    # 6. GitHub
    try:
        all_topics.extend(collect_github_trending(limit_per_query=5, categories=categories))
    except Exception as e:
        print(f"[ERROR] GitHub: {e}")

    # 7. Bluesky
    try:
        all_topics.extend(collect_bluesky(limit_per_query=5, categories=categories))
    except Exception as e:
        print(f"[ERROR] Bluesky: {e}")

    # カテゴリ別に整理（score降順でソート）
    by_category = {
        "tech": [],
        "kemono": [],
        "pokemon": [],
        "other": [],
    }
    for topic in all_topics:
        cat = topic.get("category", "other")
        if cat in by_category:
            by_category[cat].append(topic)
        else:
            by_category["other"].append(topic)
    for cat in by_category:
        by_category[cat].sort(key=lambda t: t.get("score", 0), reverse=True)

    # 既存の latest.json から sources を読み込んで未収集 source の fetched_at を継承
    prev_sources = {}
    prev_by_category = {}
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                prev = json.load(f)
            prev_sources = prev.get("sources", {})
            prev_by_category = prev.get("by_category", {})
        except Exception:
            pass

    # source ごとにグループ化して per-source TTL 構造を構築
    sources = {}
    for topic in all_topics:
        src = topic.get("source", "unknown")
        if src not in sources:
            sources[src] = {"topics": []}
        sources[src]["topics"].append(topic)

    # per-source fetched_at を付与（収集済み source は現在時刻、未収集 source は前回値継承）
    for src in sources:
        sources[src]["fetched_at"] = now.isoformat()

    # 未収集の source は前のデータから継承
    for src, src_data in prev_sources.items():
        if src not in sources:
            sources[src] = src_data

    # by_category: 収集したカテゴリは上書き、未収集は前のデータを継承
    merged_by_category = {}
    for cat in by_category:
        if by_category[cat]:
            merged_by_category[cat] = by_category[cat]
        elif cat in prev_by_category:
            merged_by_category[cat] = prev_by_category[cat]
        else:
            merged_by_category[cat] = []

    # all: 全 sources のトピックを結合
    all_topics_merged = list(all_topics)
    for src, src_data in sources.items():
        if src not in {t.get("source") for t in all_topics}:
            all_topics_merged.extend(src_data.get("topics", []))

    output = {
        "fetched_at": now.isoformat(),
        "ttl_hours": TTL_HOURS,
        "total": len(all_topics_merged),
        "by_category": merged_by_category,
        "sources": sources,
        "all": sorted(all_topics_merged, key=lambda t: t.get("score", 0), reverse=True),
    }

    # タイムスタンプ付きファイルに出力
    os.makedirs(TOPICS_DIR, exist_ok=True)
    ts = now.strftime("%Y-%m-%d_%H%M%S")
    ts_path = os.path.join(TOPICS_DIR, f"{ts}.json")
    with open(ts_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 古いタイムスタンプファイルを削除（最新10件を保持）
    try:
        ts_files = sorted(
            [f for f in os.listdir(TOPICS_DIR) if f.endswith(".json") and f != "latest.json"],
            reverse=True
        )
        for old_file in ts_files[10:]:
            old_path = os.path.join(TOPICS_DIR, old_file)
            if os.path.islink(old_path) or os.path.exists(old_path):
                os.remove(old_path)
    except Exception as e:
        print(f"[WARN] 古いファイルのクリーンアップに失敗しました: {e}")

    # latest.json を最新ファイルのコピーとして更新
    try:
        os.makedirs(TOPICS_DIR, exist_ok=True)
        with open(ts_path, "r", encoding="utf-8") as src:
            content = src.read()
        with open(OUTPUT_PATH, "w", encoding="utf-8") as dst:
            dst.write(content)
    except OSError as e:
        print(f"[WARN] latest.json の更新に失敗しました: {e}")
        os.makedirs(TOPICS_DIR, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"完了: {len(all_topics)} 件のトピックを {ts_path} に保存しました")
    for cat, items in by_category.items():
        print(f"  [{cat}] {len(items)} 件")
    print("=" * 50)


if __name__ == "__main__":
    main()
