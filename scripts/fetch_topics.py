"""
fetch_topics.py — 設定不要（APIキー不要）でトレンド情報を収集するスクリプト

収集先:
  1. Hacker News       : Firebase API (認証不要・CORS対応) [tech]
  2. e621              : REST API の公開検索 (User-Agent 必要) [kemono/pokemon]
  3. RSS 各種          : Zenn / Qiita / PokéCommunity / PokeBeach など [tech/pokemon]
  4. GitHub Search     : REST API (未認証 60req/h) [kemono/pokemon]
  5. GameSpot RSS      : RSS解析（description取得） [kemono]
  6. IGN RSS           : RSS解析（description取得） [kemono]
  7. Anime News Network: HTMLパース（記事URL whitelist抽出） [kemono]

一時無効化:
  - Reddit    : 403 Blocked (2026-10-06)
  - Bluesky   : 501 Not Implemented (2026-10-06)
  - Crunchyroll News: 静的HTMLに記事リンクなし（JS描画のためナビUIのみ抽出）(2026-10-10 実測)

出力: data/topics/{YYYY-MM-DD_HHMMSS}.json + data/topics/latest.json (コピー)
"""

import html
import json
import os
import re
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
# （PYTHONIOENCODING は起動時のみ参照されるため実行時設定は無効。パイプ時はstdioがcp932にフォールバックする）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --------------------------------------------------
# 定数
# --------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_DIR = os.path.join(PROJECT_DIR, "data", "topics")
OUTPUT_PATH = os.path.join(TOPICS_DIR, "latest.json")
USER_AGENT = "my-auto-blog/1.0 (https://github.com)"  # Reddit / e621 用
TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "24"))  # データの有効期間（時間）
RSS_DESCRIPTION_MAX = 300  # description の切り詰め長（文字）

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
CHARACTER_FEATURE_CATEGORIES = ["species", "general", "character", "copyright", "artist"]

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
    {"query": "furry+writing+fanfiction", "category": "kemono"},
    {"query": "furry+story+novel", "category": "kemono"},
    {"query": "kemono+art+gallery", "category": "kemono"},
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


def _clean_rss_description(raw: str | None) -> str:
    """description から HTML タグを除去しエンティティを復元、空白を圧縮して RSS_DESCRIPTION_MAX 文字に切り詰める。

    raw が None または空の場合は空文字列を返す。
    """
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:RSS_DESCRIPTION_MAX]


def _rss_item_description(item: ET.Element) -> str:
    """RSS 2.0 item の description を抽出する（content:encoded → description の順）。"""
    encoded = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    if encoded is not None and encoded.text:
        return _clean_rss_description(encoded.text)
    desc = item.find("description")
    return _clean_rss_description(desc.text if desc is not None else None)


def _atom_entry_description(entry: ET.Element) -> str:
    """Atom entry の description を抽出する（content → summary の順）。"""
    atom = "http://www.w3.org/2005/Atom"
    content = entry.find(f"{{{atom}}}content")
    if content is not None and content.text:
        return _clean_rss_description(content.text)
    summary = entry.find(f"{{{atom}}}summary")
    return _clean_rss_description(summary.text if summary is not None else None)


def fetch_rss(url: str, timeout: int = 15) -> list[dict]:
    """RSS / Atom フィードをパースしてタイトル+URL+description のリストを返す。"""
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
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is not None and title_el.text:
            items.append({
                "title": title_el.text.strip().encode("utf-8", errors="replace").decode("utf-8"),
                "url": link_el.text.strip() if link_el is not None and link_el.text else "",
                "description": _rss_item_description(item),
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
                    "description": _atom_entry_description(entry),
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
    """e621 投稿が NSFW（rating: explicit/questionable）または既知の NSFW タグを含む場合 True"""
    rating = post.get("rating", "")
    if rating in ("e", "q"):
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


# physical_features 除外リスト（ポーズ/背景/表情/メタ/体液）
_PHYSICAL_EXCLUDE_PATTERNS = (
    "from_",
    "looking_",
    "_background",
)

# アフィリエイト不適格なコピーライト（神話/放送局/食品/ミーム/プラットフォーム）
_AFFILIATE_EXCLUDE_COPYRIGHT_PATTERNS = (
    "mythology",
    "_mythology",
)

_AFFILIATE_EXCLUDE_COPYRIGHTS = {
    # 放送局
    "adult_swim", "cartoon_network", "british_broadcasting_corporation",
    # 食品・飲料
    "monster_energy", "cup_noodles",
    # ミーム
    "the_harkness_test_(meme)", "let_me_do_it_for_you", "casualties:_unknown",
    # プラットフォーム
    "e621", "scratch21", "gameoverse", "glitch_productions",
    # 音楽
    "ac/dc", "doja_cat",
}


def _is_affiliate_excluded(copyright_tag: str) -> bool:
    """コピーライトがアフィリエイト推薦から除外されるべきか判定する。"""
    if copyright_tag in _AFFILIATE_EXCLUDE_COPYRIGHTS:
        return True
    if any(copyright_tag.startswith(pat) for pat in _AFFILIATE_EXCLUDE_COPYRIGHT_PATTERNS):
        return True
    if any(copyright_tag.endswith(pat) for pat in _AFFILIATE_EXCLUDE_COPYRIGHT_PATTERNS):
        return True
    return False


_PHYSICAL_EXCLUDE_TAGS = {
    # ポーズ・動作
    "sitting", "standing", "lying_down", "kneeling", "holding_object", "gesture",
    "lying", "hand_gesture", "tail_motion", "tailwag", "dancing", "running",
    "jumping", "pose", "bent_legs", "v_sign",
    # 視点
    "multiple_angles", "rear_view", "side_view", "three-quarter_view",
    "front_view", "solo_focus",
    # 表情
    "smile", "blush", "open_mouth", "closed_mouth", "grin", "frown",
    "one_eye_closed", "sweat", "tongue", "sweatdrop", "happy", "eyes_closed",
    "laugh", "daww", "wide_eyed", "blush_lines", "crying", "smug",
    "surprised", "smirk", "embarrassed", "tongue_out",
    # メタ
    "solo", "duo", "group", "text", "humor", "dialogue", "music",
    "container", "beverage", "cup", "furniture",
    # 参照用
    "chart", "height_chart", "color_swatch",
    # 背景・小道具
    "inside", "outdoors", "electronics", "food", "plant",
    "box", "table", "bed", "machine", "vehicle", "nature", "window",
    "phone", "book", "mug", "bag", "microphone", "weapon",
    # 映像・音響
    "speech_bubble", "sound_effects", "exclamation_point", "profanity",
    "recording", "music_video",
    # 体液
    "bodily_fluids",
    # 性別・体型（Python側のランダムパラメータと競合するため除外）
    "male", "female", "male_anthro", "female_anthro", "ambiguous_gender",
    "young", "young_anthro", "young_female", "femboy",
    "interspecies", "male/female", "larger_female", "clothed_male",
    "muscular_anthro", "small_breasts",
    # 特殊
    "toony", "furgonomics", "glowing", "glistening", "plushie",
    # NSFW関連
    "nude",
}


def _is_physical_excluded(tag: str) -> bool:
    """general タグが physical_features から除外されるべきか判定する。"""
    if tag in _PHYSICAL_EXCLUDE_TAGS:
        return True
    if any(tag.startswith(pat) for pat in _PHYSICAL_EXCLUDE_PATTERNS):
        return True
    if any(tag.endswith(pat) for pat in _PHYSICAL_EXCLUDE_PATTERNS):
        return True
    return False


def _aggregate_and_save_character_features(raw_tags: list[dict]) -> None:
    """e621 の生タグからキャラクター特徴を種別ごとに集計して保存する。
    投稿ごとのタグデータと集計結果の両方を保存する。
    """
    from collections import Counter

    # 種別ごとのタグ集計
    species_counter = Counter()
    color_counter = Counter()
    physical_counter = Counter()
    character_counter = Counter()
    copyright_counter = Counter()
    artist_counter = Counter()

    # 色のパターン（general タグから抽出）
    color_patterns = ["_fur", "_eyes", "_body", "_hair", "_scale", "_skin", "_wing", "_tail"]

    # 投稿ごとのタグデータを保存
    posts_data = []

    for tag_data in raw_tags:
        tags = tag_data.get("tags", {})
        post_id = tag_data.get("post_id")

        post_colors = []
        post_physical = []

        # species タグの集計
        post_species = tags.get("species", [])
        for species in post_species:
            species_counter[species] += 1

        # character タグの集計
        post_characters = tags.get("character", [])
        for character in post_characters:
            character_counter[character] += 1

        # copyright タグの集計
        post_copyrights = tags.get("copyright", [])
        for copyright_tag in post_copyrights:
            copyright_counter[copyright_tag] += 1

        # artist タグの集計（unknown_artist は除外）
        post_artists = tags.get("artist", [])
        for artist_tag in post_artists:
            if artist_tag not in ("unknown_artist", "anonymous_artist"):
                artist_counter[artist_tag] += 1

        # general タグから色と身体的特徴を抽出（除外フィルタ適用）
        for tag in tags.get("general", []):
            is_color = any(tag.endswith(pat) for pat in color_patterns)
            if is_color:
                color_counter[tag] += 1
                post_colors.append(tag)
            elif not _is_physical_excluded(tag):
                physical_counter[tag] += 1
                post_physical.append(tag)

        posts_data.append({
            "id": post_id,
            "species": post_species,
            "colors": post_colors,
            "physical": post_physical,
            "characters": post_characters,
            "copyrights": post_copyrights,
            "artists": post_artists,
        })

    # 最新収集分のみを保存（累積しない）
    from datetime import datetime, timezone
    data = {
        "posts": posts_data,
        "aggregates": {
            "species": dict(species_counter),
            "colors": dict(color_counter),
            "physical_features": dict(physical_counter),
            "characters": dict(character_counter),
            "copyrights": dict(copyright_counter),
            "artists": dict(artist_counter),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_posts_analyzed": len(raw_tags),
    }

    # ファイルに保存
    os.makedirs(os.path.dirname(CHARACTER_FEATURES_PATH), exist_ok=True)
    with open(CHARACTER_FEATURES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [char-features] 特徴集計を保存しました ({len(raw_tags)} posts / species:{len(species_counter)}, colors:{len(color_counter)}, physical:{len(physical_counter)}, characters:{len(character_counter)}, copyrights:{len(copyright_counter)}, artists:{len(artist_counter)})")


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
        import random
        from datetime import datetime, timezone, timedelta, date
        now_date = datetime.now(timezone.utc).date()
        start_bound = date(2010, 1, 1)
        end_bound = now_date - timedelta(days=14)
        rand_days = random.randint(0, (end_bound - start_bound).days)
        window_start = start_bound + timedelta(days=rand_days)
        window_end = window_start + timedelta(days=14)
        date_metatag = f"date:{window_start.isoformat()}..{window_end.isoformat()}"
        tag_query_with_date = f"{tag_query} {date_metatag} order:random"
        encoded = urllib.parse.quote(tag_query_with_date)
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
                "description": item.get("description", ""),
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


# アニメ・ゲーム・エンタメのトレンド情報源
# GameSpot / IGN は実測（2026-10-10）で正規の RSS 2.0 フィードのため fetch_rss で description 付き取得
# ANN は RSS が存在せず HTML パース（description なし）
# Crunchyroll は 2026-10-10 実測で /news の静的HTMLに記事リンクが 0 件（JS描画）のため除外済み。
#   静的に記事 URL を取得できる方法（__NEXT_DATA__ 等）が見つかったら再追加する
ENTERTAINMENT_RSS_SOURCES = [
    {"name": "GameSpot RSS", "url": "https://www.gamespot.com/feeds/mashup/", "category": "kemono"},
    {"name": "IGN RSS", "url": "https://feeds.feedburner.com/ign/all", "category": "kemono"},
]
ENTERTAINMENT_HTML_SOURCES = [
    {"name": "Anime News Network", "url": "https://www.animenewsnetwork.com/", "category": "kemono"},
]

# HTML ソース別: 記事 URL の whitelist パターン（ナビ/フッター UI リンクを除外）
# ANN の正規記事は日付を含むパス（/news/2026-10-10/...）を持つ（2026-10-10 ライブ確認: 73 件）
ENTERTAINMENT_ARTICLE_PATTERNS = {
    "Anime News Network": re.compile(r"^/(?:news|review|guide|interview|profile|gallery)/\d{4}-\d{2}-\d{2}/"),
}

# 全ソース失敗時の内蔵ストーリーインスピレーションテーマ
# 旧実装は未定義の STORY_INSPIRATION_THEMES を参照し NameError になっていた（2026-10-10 修正）
STORY_INSPIRATION_THEMES = [
    {"theme": "迷い込む異世界の獣人村", "description": "人間世界から獣人の村に迷い込み、仲間と暮らしながら自分の居場所を見出す物語"},
    {"theme": "廃墟に眠る古代文明", "description": "獣人たちが守ってきた古代の力と、その末裔が抱える宿命"},
    {"theme": "砂漠を横断する大商隊", "description": "オアシスを巡る長い旅路で結ばれる、異なる種族の獣人たち"},
    {"theme": "海底都市と陸上の街", "description": "海と陸の境界で起きる文化衝突と、それを橋渡しする存在"},
    {"theme": "戦場の獣人傭兵団", "description": "主を見出すことと、自らの戦いの理由を見つけるまでの旅"},
    {"theme": "山間の隠れ里と外の世界", "description": "平和な里を守るため、初めて外の世界へ出る若き獣人"},
    {"theme": "大都会の裏路地と秘密の店", "description": "多種多様な獣人が集う街で、ひとつの店を舞台にした人間模様"},
    {"theme": "季節の祭りと巡り合わせ", "description": "年に一度の祭りをきっかけに起こる、かけがえのない出会い"},
]


def _parse_entertainment_page(html_content: str, source_name: str, category: str, base_url: str = "") -> list[dict]:
    """HTML コンテンツから記事リンクを抽出する（簡易パース）。

    ENTERTAINMENT_ARTICLE_PATTERNS の whitelist に一致する記事 URL のみ収集し、
    ナビ/フッター UI リンク（ログイン・登録・アーカイブ等）を除外する。
    相対 URL は base_url に対して urljoin で解決する。
    """
    pattern = ENTERTAINMENT_ARTICLE_PATTERNS.get(source_name)
    if pattern is None:
        return []

    results = []
    link_matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_content, re.IGNORECASE | re.DOTALL)

    seen_urls = set()
    for href, text in link_matches:
        if href.startswith(("javascript:", "mailto:", "#")):
            continue
        url = urllib.parse.urljoin(base_url, href) if base_url else href
        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc:
            continue
        if not pattern.match(parsed.path):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        # HTML エンティティをデコード
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        clean_text = clean_text.replace("&amp;", "&").replace("&quot;", '"').replace("&apos;", "'")
        clean_text = clean_text.replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        if len(clean_text) < 10 or len(clean_text) > 200:
            continue
        results.append({
            "title": clean_text,
            "url": url,
            "score": 0,
            "source": source_name,
            "category": category,
        })

    return results[:15]  # 最大15件


def collect_entertainment_trends(categories: list[str] = None) -> list[dict]:
    """アニメ・ゲーム・エンタメのトレンド情報を収集してストーリーインスピレーションに使用する。

    GameSpot / IGN は RSS フィードから description 付きで、
    ANN は HTML パース（description なし・記事URL whitelist抽出）で収集する。
    """
    if categories and "kemono" not in categories:
        return []

    results = []

    # RSS ソース（description 付き）
    for source in ENTERTAINMENT_RSS_SOURCES:
        name = source["name"]
        category = source["category"]
        print(f"[Entertainment] Fetching {name}...")
        try:
            items = fetch_rss(source["url"])
            for item in items:
                results.append({
                    "title": item["title"],
                    "url": item["url"],
                    "description": item.get("description", ""),
                    "score": 0,
                    "source": name,
                    "category": category,
                })
            print(f"  -> {len(items)} items from {name}")
        except Exception as e:
            print(f"  [WARN] Failed to fetch {name}: {e}")
        time.sleep(0.5)

    # HTML ソース（description なし）
    for source in ENTERTAINMENT_HTML_SOURCES:
        name = source["name"]
        url = source["url"]
        category = source["category"]
        print(f"[Entertainment] Fetching {name}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            items = _parse_entertainment_page(content, name, category, base_url=url)
            for item in items:
                item["description"] = ""
            results.extend(items)
            print(f"  -> {len(items)} items from {name}")
        except Exception as e:
            print(f"  [WARN] Failed to fetch {name}: {e}")
        time.sleep(0.5)

    # 全ソースから取得できなかった場合は内蔵テーマを使用
    if not results:
        print("[Entertainment] 全ソース失敗、内蔵テーマを使用")
        for theme in STORY_INSPIRATION_THEMES:
            results.append({
                "title": theme["theme"],
                "url": "",
                "description": theme["description"],
                "score": 0,
                "source": "StoryInspiration",
                "category": "kemono",
            })

    print(f"  -> {len(results)} entertainment trend items collected")
    return results


# --------------------------------------------------
# カテゴリ マッピング
# --------------------------------------------------

# prompt_type -> 必要なカテゴリ一覧
PROMPT_CATEGORIES = {
    "default": ["tech"],
    "ai_deep": ["tech"],
    "kemono_story": ["kemono"],
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

    # 2. Reddit (2026-10-06: 403 Blocked で動作せず、暫定無効化)
    # try:
    #     all_topics.extend(collect_reddit(limit_per_sub=5, categories=categories))
    # except Exception as e:
    #     print(f"[ERROR] Reddit: {e}")

    # 3. e621
    try:
        all_topics.extend(collect_e621(limit_per_tag=5, categories=categories))
    except Exception as e:
        print(f"[ERROR] e621: {e}")

    # 4. RSS
    try:
        all_topics.extend(collect_rss_feeds(categories=categories))
    except Exception as e:
        print(f"[ERROR] RSS: {e}")

    # 6. GitHub
    try:
        all_topics.extend(collect_github_trending(limit_per_query=5, categories=categories))
    except Exception as e:
        print(f"[ERROR] GitHub: {e}")

    # 7. Bluesky (2026-10-06: 501 Not Implemented で動作せず、暫定無効化)
    # try:
    #     all_topics.extend(collect_bluesky(limit_per_query=5, categories=categories))
    # except Exception as e:
    #     print(f"[ERROR] Bluesky: {e}")

    # 8. Anime/Game/Entertainment Trends
    try:
        all_topics.extend(collect_entertainment_trends(categories=categories))
    except Exception as e:
        print(f"[ERROR] EntertainmentTrends: {e}")

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
