import os
import glob
import html
import json
import random
from dotenv import load_dotenv
load_dotenv()
import re
from datetime import datetime, timezone, timedelta
import subprocess
import sys
import time
import urllib.parse
import requests
from PIL import Image
import pillow_avif
from google import genai
from google.genai import errors
from gradio_client import Client
import yaml

# Windows コンソールで cp932 → UTF-8 変換エラーを防ぐ
# （パイプ時はstdioがロケールcp932にフォールバックし、絵文字等非収録文字でUnicodeEncodeErrorになる）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --------------------------------------------------
# 設定
# --------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

HF_TOKEN = os.environ.get("HF_TOKEN")

# 画像生成プロバイダー: "hf" (デフォルト) または "pollinations"
IMAGE_PROVIDER = os.environ.get("IMAGE_PROVIDER", "hf").lower()

client = genai.Client(api_key=GEMINI_API_KEY)

MODELS_TO_TRY = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite"
]

HF_SPACE_ID = "blume/kemono-image-api"
BASE_URL = "/my-auto-blog"  # GitHub Pagesのベースパス
MAX_INLINE_IMAGES = int(os.environ.get("MAX_INLINE_IMAGES", "7"))
MIN_SCORE_THRESHOLD = int(os.environ.get("MIN_SCORE_THRESHOLD", "0"))
GENRE_SCORES_PATH = os.path.join("data", "genre_scores", "topics.json")
GENRE_FILTER_MIN_SCORE = int(os.environ.get("GENRE_FILTER_MIN_SCORE", "30"))

# 画像プロンプトの固定ベース・フォールバック指定 (Nova-Furry-XL向け)
# SFWタグを常に付与して安全な画像生成を強制
# アートスタイルは記事ごとにFrontmatterのart_styleで決定（BASE_QUALITY_PROMPTには含めない）
BASE_QUALITY_PROMPT = "masterpiece, best quality, very aesthetic, ultra-detailed, furry, safe for work"
DEFAULT_ART_STYLE = "anime style, illustration, cel shading"
DEFAULT_SITUATION = "dragon, blueeyes, white scale, sitting at desk with laptop, tech room"

# kemono_story プロンプトのPython側ランダム化設定
# 各項目の重み付き選択でテーマの多様性を確保
# 値は体型タグのリスト（個別タグとしてそのまま使用）。
# プロンプト表示文字列は " / " 結合（char_type）で生成する
CHAR_TYPE_WEIGHTS = [
    (["獣人"], 30),
    (["動物と獣人のハーフ"], 20),
    (["動物"], 20),
    (["獣人", "動物と獣人のハーフ"], 10),
    (["獣人", "動物"], 10),
    (["動物と獣人のハーフ", "動物"], 10),
]

WORLD_SETTING_WEIGHTS = [
    ("fantasy", 21),
    ("isekai", 10),
    ("modern", 10),
    ("slice_of_life", 10),
    ("sf", 8),
    ("space_opera", 7),
    ("adventure", 7),
    ("cyberpunk", 7),
    ("dungeon_crawl", 6),
    ("mystery", 5),
    ("historical", 5),
    ("fantasy+sf", 4),
]

TRANSFORM_WEIGHTS = [
    ("none", 40),
    ("tf", 25),
    ("tsf", 25),
    ("tf+tsf", 10),
]

RELATIONSHIP_WEIGHTS = [
    ("partnership", 30),
    ("yaoi", 25),
    ("yuri", 25),
    ("hetero", 20),
]

EXTRA_SETTING_WEIGHTS = [
    ("none", 70),
    ("clone", 20),
    ("rival", 10),
]

CHAR_COUNT_WEIGHTS = [
    (1, 40),
    (2, 60),
]


WORLD_SETTING_GENRE_MAP = {
    "fantasy": ["fantasy"],
    "isekai": ["fantasy", "action"],
    "modern": ["slice_of_life", "action", "mystery"],
    "sf": ["sf"],
    "space_opera": ["sf", "action"],
    "slice_of_life": ["slice_of_life"],
    "cyberpunk": ["cyberpunk"],
    "adventure": ["action", "fantasy"],
    "dungeon_crawl": ["fantasy", "action"],
    "mystery": ["mystery"],
    "historical": ["historical"],
    "fantasy+sf": ["fantasy", "sf"],
}


def _load_genre_scores() -> dict:
    """data/genre_scores/topics.json を読み込む。存在しない・破損時は空 dict。"""
    if not os.path.exists(GENRE_SCORES_PATH):
        return {}
    try:
        with open(GENRE_SCORES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _filter_by_genre(items: list[dict], target_genres: list[str], scores_data: dict) -> list[dict]:
    """事前スコアリング結果でジャンル適合度の高い順にソートする。
    スコア未登録の項目は末尾に保持（除外しない）。"""
    topic_scores = {t["key"]: t.get("scores") for t in scores_data.get("topics", []) if t.get("scores")}
    def _genre_score(item: dict) -> float:
        url = item.get("url", item.get("title", ""))
        scores = topic_scores.get(url)
        if not scores:
            return -1
        return max(scores.get(g, 0) for g in target_genres)
    scored = [(it, _genre_score(it)) for it in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [it for it, _ in scored]


def _is_valid_kemono_combination(transform, relationship, extra):
    """無効な組み合わせをフィルタ"""
    if extra == "clone" and relationship == "hetero" and "tsf" not in transform:
        return False
    return True


# 世界設定のタグリスト（個別タグとしてそのまま使用）
# プロンプト表示文字列は "と" 結合（_KEMONO_WORLD_TEXT）で生成する
_KEMONO_WORLD_TAGS = {
    "fantasy": ["ファンタジー"],
    "isekai": ["異世界"],
    "modern": ["現代"],
    "sf": ["SF"],
    "space_opera": ["スペースオペラ"],
    "slice_of_life": ["日常"],
    "cyberpunk": ["サイバーパンク"],
    "adventure": ["冒険"],
    "dungeon_crawl": ["ダンジョンクライム"],
    "mystery": ["ミステリー"],
    "historical": ["歴史"],
    "fantasy+sf": ["ファンタジー", "SF"],
}
_KEMONO_WORLD_TEXT = {key: "と".join(tags) for key, tags in _KEMONO_WORLD_TAGS.items()}

_KEMONO_TRANSFORM_TEXT = {
    "none": "",
    "tf": "、TF(変身・変形)",
    "tsf": "、TSF（性転換フィクション）",
    "tf+tsf": "、TF・TSF",
}

# 生成情報セクション用のクリーンな変身ラベル（プロンプト表示用の "、" 接頭文字列は表示に不適のため別定数）
_KEMONO_TRANSFORM_LABEL = {
    "none": "なし",
    "tf": "TF（変身・変形）",
    "tsf": "TSF（性転換フィクション）",
    "tf+tsf": "TF・TSF",
}

_KEMONO_RELATIONSHIP_TEXT = {
    "partnership": "相棒関係",
    "yaoi": "同性愛（男性同士の恋愛）",
    "yuri": "百合（女性同士の恋愛）",
    "hetero": "異性愛",
}

# 追加設定のタグ（個別タグとしてそのまま使用）
# プロンプト表示文字列は "、" 接頭（_KEMONO_EXTRA_TEXT）で生成する
_KEMONO_EXTRA_TAGS = {
    "none": "",
    "clone": "クローンによる自分同士",
    "rival": "ライバル関係",
}
_KEMONO_EXTRA_TEXT = {key: (f"、{text}" if text else "") for key, text in _KEMONO_EXTRA_TAGS.items()}

_KEMONO_CHAR_COUNT_DESC_1 = ["クローン"]
_KEMONO_CHAR_COUNT_DESC_2 = ["バディ", "ライバル", "カップル"]


def _randomize_kemono_params():
    """kemono_story プロンプト用のランダムパラメータを重み付き選択で生成する。
    バリデーションに失敗した場合は再試行（最大100回）。
    char_count=1 は extra=clone の時のみに制限。"""
    for _ in range(100):
        char_types = random.choices(
            [v[0] for v in CHAR_TYPE_WEIGHTS],
            weights=[v[1] for v in CHAR_TYPE_WEIGHTS],
            k=1,
        )[0]
        world_setting = random.choices(
            [v[0] for v in WORLD_SETTING_WEIGHTS],
            weights=[v[1] for v in WORLD_SETTING_WEIGHTS],
            k=1,
        )[0]
        transform = random.choices(
            [v[0] for v in TRANSFORM_WEIGHTS],
            weights=[v[1] for v in TRANSFORM_WEIGHTS],
            k=1,
        )[0]
        relationship = random.choices(
            [v[0] for v in RELATIONSHIP_WEIGHTS],
            weights=[v[1] for v in RELATIONSHIP_WEIGHTS],
            k=1,
        )[0]
        extra = random.choices(
            [v[0] for v in EXTRA_SETTING_WEIGHTS],
            weights=[v[1] for v in EXTRA_SETTING_WEIGHTS],
            k=1,
        )[0]

        if extra == "clone":
            char_count = random.choices(
                [v[0] for v in CHAR_COUNT_WEIGHTS],
                weights=[v[1] for v in CHAR_COUNT_WEIGHTS],
                k=1,
            )[0]
        else:
            char_count = 2

        if _is_valid_kemono_combination(transform, relationship, extra):
            break
    else:
        transform = "none"
        extra = "none"
        char_count = 2

    return {
        # 構造化データ（タグ生成・アフィリエイトkwに直接使用）
        "char_types": list(char_types),
        "world_tags": list(_KEMONO_WORLD_TAGS[world_setting]),
        "extra_tag": _KEMONO_EXTRA_TAGS[extra],
        # プロンプト表示用（結合済み文字列）
        "char_type": " / ".join(char_types),
        "world_setting_key": world_setting,
        "world_setting": _KEMONO_WORLD_TEXT[world_setting],
        "transform_key": transform,
        "transform_text": _KEMONO_TRANSFORM_TEXT[transform],
        "relationship_key": relationship,
        "relationship_text": _KEMONO_RELATIONSHIP_TEXT[relationship],
        "extra_key": extra,
        "extra_text": _KEMONO_EXTRA_TEXT[extra],
        "char_count": char_count,
        "char_count_desc": random.choice(_KEMONO_CHAR_COUNT_DESC_1 if char_count == 1 else _KEMONO_CHAR_COUNT_DESC_2),
    }


# SEOメタ記述の文字数制約
MIN_DESC_LEN = 80
MAX_DESC_LEN = 120

# 本文内画像プレースホルダーの正規表現 (例: <!-- IMAGE_PROMPT: "..." -->)
INLINE_IMAGE_PATTERN = re.compile(
    r'<!--\s*IMAGE_PROMPT:\s*(.*?)\s*-->',
    re.IGNORECASE
)

# 本文内アフィリエイトプレースホルダーの正規表現 (例: <!-- AFFILIATE: "kw" | "anchor" -->)
INLINE_AFFILIATE_PATTERN = re.compile(
    r'<!--\s*AFFILIATE:\s*"([^"]+)"\s*\|\s*"([^"]+)"\s*-->',
    re.IGNORECASE
)

# 比較表内の商品リンクプレースホルダー (例: <!-- AFF_PRODUCT: "keyword" -->)
INLINE_AFF_PRODUCT_PATTERN = re.compile(
    r'<!--\s*AFF_PRODUCT:\s*"([^"]+)"\s*-->',
    re.IGNORECASE
)


# --------------------------------------------------
# 画像生成関数
# --------------------------------------------------
def _save_as_avif(image_path: str, output_filename: str) -> str:
    """画像をAVIF形式に変換してpublic/images/ に保存し、URLパスを返す"""
    save_dir = os.path.join("public", "images")
    os.makedirs(save_dir, exist_ok=True)

    gitkeep_path = os.path.join(save_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        open(gitkeep_path, 'w').close()

    output_filename_avif = os.path.splitext(output_filename)[0] + ".avif"
    target_path = os.path.join(save_dir, output_filename_avif)

    with Image.open(image_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(target_path, "AVIF", quality=80)

    print(f"🖼️ AVIF画像保存成功: {target_path}")
    return f"{BASE_URL}/images/{output_filename_avif}"


def _generate_image_pollinations(prompt: str, output_filename: str, seed: int = -1) -> str:
    """Pollinations.ai をフォールバック画像生成として使用"""
    save_dir = os.path.join("public", "images")
    os.makedirs(save_dir, exist_ok=True)

    actual_seed = seed if seed >= 0 else int(time.time())
    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?model=flux&width=896&height=512&seed={actual_seed}"

    print(f"🌐 Pollinations.ai 画像生成中: {url[:120]}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    output_filename_tmp = os.path.splitext(output_filename)[0] + ".jpg"
    temp_path = os.path.join(save_dir, output_filename_tmp)
    with open(temp_path, "wb") as f:
        f.write(resp.content)

    return _save_as_avif(temp_path, output_filename)


def generate_and_save_image(prompt: str, output_filename: str, seed: int = -1) -> str:
    """HF Space APIを呼び出して画像を生成し、public/images/ にAVIF形式で保存してURLパスを返す。
    HF 失敗時は Pollinations.ai にフォールバック。
    IMAGE_PROVIDER=pollinations の場合は HF をスキップして直接 Pollinations を使用。
    seed が指定された場合、同じ記事内の画像で一貫したスタイルを維持する。"""
    save_dir = os.path.join("public", "images")
    os.makedirs(save_dir, exist_ok=True)

    gitkeep_path = os.path.join(save_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        open(gitkeep_path, 'w').close()

    seed_info = f" seed={seed}" if seed >= 0 else ""
    print(f"🎨 画像生成開始: {output_filename}{seed_info}")

    # IMAGE_PROVIDER=pollinations の場合は HF をスキップ
    if IMAGE_PROVIDER == "pollinations":
        print("🌐 IMAGE_PROVIDER=pollinations: 直接 Pollinations.ai を使用します。")
        try:
            return _generate_image_pollinations(prompt, output_filename, seed)
        except Exception as e:
            print(f"⚠️ Pollinations.ai 画像生成失敗: {e}")
            print("⚠️ 画像生成を断念し、画像なしで記事のみ出力します。")
            return ""

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            hf_client = Client(HF_SPACE_ID, token=HF_TOKEN)

            temp_image_path = hf_client.predict(
                prompt,
                "nsfw, worst quality, bad anatomy, deformed, bad hands, missing fingers, extra digits, fewer digits, cropped, very displeasing, ugly, jpeg artifacts, signature, watermark, username",
                18,
                5.0,
                896,
                512,
                seed,
                api_name="/predict"
            )

            return _save_as_avif(temp_image_path, output_filename)

        except Exception as e:
            print(f"⚠️ 画像生成試行 {attempt} 失敗: {e}")
            if attempt < max_retries:
                time.sleep(15)

    # HF 全試行失敗 → Pollinations.ai フォールバック
    print("🔄 HuggingFace 全試行失敗。Pollinations.ai にフォールバックします。")
    try:
        return _generate_image_pollinations(prompt, output_filename, seed)
    except Exception as e:
        print(f"⚠️ Pollinations.ai フォールバックも失敗: {e}")

    print("⚠️ 画像生成を断念し、画像なしで記事のみ出力します。")
    return ""


# --------------------------------------------------
# 過去記事情報の取得・重複防止
# --------------------------------------------------
def get_existing_posts(posts_dir="src/content/posts"):
    """
    既存の全記事からタイトル、日付、prompt_type（系統）を抽出して新しい順（降順）にソートして返す。
    """
    posts = []
    if not os.path.exists(posts_dir):
        return posts
    
    md_files = glob.glob(os.path.join(posts_dir, "*.md"))
    for filepath in md_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
            if not title_match:
                continue
            title = title_match.group(1).strip()

            date_match = re.search(r'^pubDate:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
            pub_date = date_match.group(1).strip() if date_match else os.path.basename(filepath)

            # 系統（prompt_type）判定
            type_match = re.search(r'^prompt_type:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
            if type_match:
                p_type = type_match.group(1).strip()
            else:
                # 既存記事用のフォールバック推測（author, tags, character定義から判定）
                if 'author: "AI Storyteller"' in content or 'tags: ["Kemono"' in content or 'character_1:' in content:
                    p_type = "kemono_story"
                else:
                    p_type = "default"

            posts.append({
                "title": title,
                "pub_date": pub_date,
                "prompt_type": p_type
            })
        except Exception as e:
            print(f"⚠️ 記事ファイル読み込みスキップ ({filepath}): {e}")
            continue

    # 日付降順（新しい順）にソート
    posts.sort(key=lambda x: x["pub_date"], reverse=True)
    return posts



def get_recent_titles_by_type(current_prompt_type: str, posts_dir="src/content/posts") -> list[str]:
    """
    同系統の記事から直近のタイトルを指定件数分取得する。
    物語生成（kemono_story等）の場合は直近5件程度、通常記事は直近30件。
    """
    LIMITS_BY_TYPE = {
        "kemono_story": 5,  # 物語系は直近5件に緩和
        "default": 30       # 技術記事などは直近30件
    }
    limit = LIMITS_BY_TYPE.get(current_prompt_type, 10)

    posts = get_existing_posts(posts_dir)

    # 物語系とみなす系統一覧
    story_types = {"kemono_story", "novel", "story"}

    same_type_titles = []
    for p in posts:
        post_type = p["prompt_type"]
        is_same = False
        if current_prompt_type in story_types and post_type in story_types:
            is_same = True
        elif current_prompt_type == post_type:
            is_same = True

        if is_same:
            same_type_titles.append(p["title"])

    print(f"📚 同系統（{current_prompt_type}）の過去記事を {len(same_type_titles)} 件検出（直近 {min(len(same_type_titles), limit)} 件を参照）")
    return same_type_titles[:limit]


def get_recent_meta_by_type(current_prompt_type: str, posts_dir="src/content/posts") -> list[dict]:
    """
    同系統の記事から直近N件の frontmatter メタデータを抽出する。
    返り値: [{title, character_1, character_2, tags, art_style}, ...]
    """
    LIMITS_BY_TYPE = {
        "kemono_story": 5,
        "default": 10,
    }
    limit = LIMITS_BY_TYPE.get(current_prompt_type, 5)

    posts = get_existing_posts(posts_dir)

    story_types = {"kemono_story", "novel", "story"}
    metas = []

    for p in posts:
        post_type = p["prompt_type"]
        is_same = False
        if current_prompt_type in story_types and post_type in story_types:
            is_same = True
        elif current_prompt_type == post_type:
            is_same = True

        if not is_same:
            continue

        filepath = None
        for md_file in glob.glob(os.path.join(posts_dir, "*.md")):
            with open(md_file, "r", encoding="utf-8") as f:
                fc = f.read()
            tm = re.search(r'^title:\s*["\']?(.*?)["\']?$', fc, re.MULTILINE)
            if tm and tm.group(1).strip() == p["title"]:
                filepath = md_file
                break

        if not filepath:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        meta = {"title": p["title"]}

        c1 = _extract_fm_field(content, "character_1")
        c2 = _extract_fm_field(content, "character_2")
        if c1:
            meta["character_1"] = c1
        if c2:
            meta["character_2"] = c2

        tags = _extract_fm_field(content, "tags")
        if tags:
            meta["tags"] = tags

        art = _extract_fm_field(content, "art_style")
        if art:
            meta["art_style"] = art

        metas.append(meta)

        if len(metas) >= limit:
            break

    if metas:
        print(f"🔍 被り検出用メタデータを {len(metas)} 件取得")
    return metas


# --------------------------------------------------
# プロンプト読み込み
# --------------------------------------------------
def load_prompt_template(prompt_type="default"):
    prompt_path = os.path.join("scripts", "prompts", f"{prompt_type}.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("scripts", "prompts", "default.txt")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# アフィリエイト不適格なコピーライト
_AF_EXCLUDE_CP_PATTERNS = ("mythology", "_mythology", "inktober")
_AF_EXCLUDE_CPS = {
    # 放送局
    "adult_swim", "cartoon_network", "british_broadcasting_corporation",
    # 食品・飲料・小売
    "monster_energy", "cup_noodles", "jack_in_the_box_(restaurant)",
    "cheetos", "frito-lay", "pepsico", "ikea",
    # ミーム
    "the_harkness_test_(meme)", "let_me_do_it_for_you", "casualties:_unknown",
    "gigachad", "low_tier_god", "no_thoughts_head_empty",
    "is_that_your_fucking_fursona?_that's_cringe",
    # プラットフォーム
    "e621", "scratch21", "gameoverse", "glitch_productions", "patreon", "bilibili",
    # 音楽
    "ac/dc", "doja_cat", "nirvana", "michael_jackson", "in_utero_(album)",
    # ライセンス
    "cc0", "creative_commons",
    # 政府機関
    "fbi",
    # 抽象・イベント
    "mood", "halloween", "father's_day",
    # 成人向け
    "takeshi_loves_sex",
}


def _is_affiliate_excluded(cp: str) -> bool:
    if cp in _AF_EXCLUDE_CPS:
        return True
    if any(cp.startswith(p) for p in _AF_EXCLUDE_CP_PATTERNS):
        return True
    if any(cp.endswith(p) for p in _AF_EXCLUDE_CP_PATTERNS):
        return True
    return False


def _load_character_features(target_genres: list[str] | None = None) -> str:
    """e621 から集計したキャラクター特徴を読み込んで、プロンプト用の指示文を生成する。
    投稿データからランダムに2投稿選出（版権重複時は再抽選）してキャラクタープロファイルを生成。
    版権は選出投稿から抽出し、不足分を集計結果から補完（アフィリエイト不適格は除外）。
    target_genres 指定時は、事前スコアリング結果でジャンル適合度の高い版権を優先する。
    """
    features_path = os.path.join("data", "character_features.json")
    if not os.path.exists(features_path):
        print("  [char-features] character_features.json が見つかりません（注入スキップ）")
        return ""

    try:
        with open(features_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [char-features] 読み取り失敗: {e}（注入スキップ）")
        return ""

    posts = data.get("posts", [])
    aggregates = data.get("aggregates", data)

    if not posts:
        print("  [char-features] 投稿データが空です（注入スキップ）")
        return ""

    updated_at = data.get("updated_at", "unknown")
    total_posts = data.get("total_posts_analyzed", 0)

    # 投稿からランダムに2つ選出（版権重複時は再抽選）
    import random
    selected = _select_two_posts(posts, max_retries=10)

    # 集計結果からベース版権を確保（アフィリエイト不適格は除外）
    aggregate_copyrights = sorted(aggregates.get("copyrights", {}).items(), key=lambda x: -x[1])
    all_valid_cps = [cp for cp, _ in aggregate_copyrights if not _is_affiliate_excluded(cp)]
    if target_genres:
        scores_data = _load_genre_scores()
        cp_scores = {c["name"]: c.get("scores") for c in scores_data.get("copyrights", []) if c.get("scores")}
        def _cp_genre_score(cp: str) -> float:
            s = cp_scores.get(cp)
            if not s:
                return -1
            return max(s.get(g, 0) for g in target_genres)
        all_valid_cps.sort(key=_cp_genre_score, reverse=True)
    base_copyrights = all_valid_cps[:10]

    # 選出投稿から版権を抽出（アフィリエイト不適格は除外）
    post_copyrights = []
    for post in selected:
        for cp in post.get("copyrights", []):
            if not _is_affiliate_excluded(cp) and cp not in post_copyrights:
                post_copyrights.append(cp)

    # 選出投稿の版権を先頭に、不足分を集計ベースで補完
    all_copyrights = list(post_copyrights)
    for cp in base_copyrights:
        if cp not in all_copyrights:
            all_copyrights.append(cp)

    copyright_names = ", ".join(c for c in all_copyrights[:8]) if all_copyrights else "-"

    # 人気artistを抽出（unknown_artistは既に除外済み）
    aggregate_artists = sorted(aggregates.get("artists", {}).items(), key=lambda x: -x[1])
    artist_names = ", ".join(a for a, _ in aggregate_artists[:8]) if aggregate_artists else "-"

    lines = [
        "",
        "【キャラクター特徴のトレンドデータ（参考）】",
        "",
    ]

    # 各投稿からキャラクタープロファイルを生成
    for i, post in enumerate(selected, 1):
        species = ", ".join(post.get("species", [])) or "-"
        colors = ", ".join(post.get("colors", [])) or "-"
        physical = ", ".join(post.get("physical", [])[:8]) or "-"
        characters = ", ".join(post.get("characters", [])) or "-"
        post_copyrights = ", ".join(cp for cp in post.get("copyrights", []) if not _is_affiliate_excluded(cp)) or "-"
        lines.append(f"・参考キャラクター{i}:")
        lines.append(f"  種族: {species}")
        lines.append(f"  色: {colors}")
        lines.append(f"  身体的特徴: {physical}")
        lines.append(f"  参照: {characters}")
        lines.append(f"  作品: {post_copyrights}")
        lines.append("")

    lines.append(f"・人気版権: {copyright_names}")
    lines.append(f"・人気artist: {artist_names}")
    lines.append("")
    lines.append("アフィリエイトの製品推薦では、人気版権・キャラクターの公式グッズまたはトレンドに関連するゲーム・書籍・グッズを推奨してください。")

    print(f"  [char-features] 注入: updated_at={updated_at}, posts={total_posts} (raw:{len(posts)}), selected={len(selected)}, copyrights={len(copyright_names)}, artists={len(artist_names)}")

    return "\n".join(lines)


def _select_two_posts(posts: list[dict], max_retries: int = 10) -> list[dict]:
    """投稿リストからランダムに2つ選出。版権が重複する場合は再抽選。"""
    import random

    if len(posts) < 2:
        return list(posts)

    # 最初の投稿をランダム選択
    first = random.choice(posts)
    first_copyrights = set(first.get("copyrights", []))

    # 2つ目の投稿を版権重複なしで選択
    for _ in range(max_retries):
        second = random.choice(posts)
        second_copyrights = set(second.get("copyrights", []))
        if not (first_copyrights & second_copyrights):
            return [first, second]

    # 再試行しても重複回避できない場合は最初の2投稿を返す
    return posts[:2]


# --------------------------------------------------
# キャラクター設定抽出関数
# --------------------------------------------------
def extract_character_prompts(markdown_content: str) -> dict[str, str]:
    """
    MarkdownのFrontmatterからキャラクター定義（character_1, character_2, character_prompt等）を抽出する。
    返り値の例: {'character_1': '1boy, blue wolf, ...', 'character_2': '1boy, black panther, ...'}
    """
    characters = {}

    # 1. character_1: "...", character_2: "..." などを抽出
    char_matches = re.finditer(
        r'^\s*character_?(\d+|[a-zA-Z0-9_-]+)\s*:\s*["\']?(.*?)["\']?\s*$',
        markdown_content,
        re.MULTILINE
    )
    for m in char_matches:
        suffix = m.group(1).lower()
        val = m.group(2).strip()
        val = re.sub(r'\s*#.*$', '', val).strip().strip('"\'')
        if not val:
            continue
        if suffix in ("prompt", "prompts"):
            key = "character_1"
        else:
            num_match = re.search(r'\d+', suffix)
            key = f"character_{num_match.group(0)}" if num_match else f"character_{suffix}"
        
        if key not in characters:
            characters[key] = val

    # 2. 単一 character_prompt: "..." のフォールバック
    if not characters:
        single_match = re.search(
            r'^\s*character_prompt\s*:\s*["\']?(.*?)["\']?\s*$',
            markdown_content,
            re.MULTILINE
        )
        if single_match and single_match.group(1):
            val = single_match.group(1).strip()
            val = re.sub(r'\s*#.*$', '', val).strip().strip('"\'')
            if val:
                characters["character_1"] = val

    # 3. YAMLリスト形式 characters:\n  - "..." のフォールバック
    if not characters:
        list_match = re.search(
            r'^\s*characters:\s*\n((?:\s*-\s*.*?\n)+)',
            markdown_content,
            re.MULTILINE
        )
        if list_match:
            lines = list_match.group(1).strip().splitlines()
            for idx, line in enumerate(lines, start=1):
                val = re.sub(r'^\s*-\s*', '', line).strip().strip('"\'')
                val = re.sub(r'\s*#.*$', '', val).strip()
                if val:
                    characters[f"character_{idx}"] = val

    return characters


# --------------------------------------------------
# アートスタイル抽出関数
# --------------------------------------------------
def extract_art_style(markdown_content: str) -> str:
    """MarkdownのFrontmatterから art_style の値を抽出する"""
    match = re.search(r'^art_style:\s*["\']?(.*?)["\']?$', markdown_content, re.MULTILINE)
    if match and match.group(1):
        return match.group(1).strip()
    return DEFAULT_ART_STYLE

# --------------------------------------------------
# プロンプト合成関数（複数キャラ対応）
# --------------------------------------------------
def _parse_image_prompt_targets(bracket_content: str, characters: dict[str, str]) -> tuple[list[str], dict[str, str], str]:
    """画像プロンプトの括弧内 [character_1: tags, ...] を解析する。

    対応形式:
      [character_1]                                     (legacy)
      [character_1, character_2]                        (legacy)
      [character_1: blushing, character_2: frown]       (キャラ別表情/ポーズ)
      [character_1, character_2, smile]                 (共有表情/ポーズ)
    戻り値: (target_chars, per_char_tags, shared_tags)
      - per_char_tags: コロン指定があるキャラのタグ（カンマ結合済み）
      - shared_tags: コロンなし形式の末尾に続く全キャラ共通タグ
    """
    target_chars: list[str] = []
    per_char_tags: dict[str, list[str]] = {}
    shared_parts: list[str] = []
    current: str | None = None
    has_colon_ref = False

    for raw_entry in re.split(r'[,、&]+', bracket_content):
        entry = raw_entry.strip()
        if not entry:
            continue
        ref_match = re.match(r'^(character_\d+)(?:\s*[:：]\s*(.*))?$', entry, re.IGNORECASE)
        if ref_match:
            has_colon_ref = has_colon_ref or ref_match.group(2) is not None
            key = ref_match.group(1).lower()
            matched = next((k for k in characters if k.lower() == key), None)
            if matched and matched not in target_chars:
                target_chars.append(matched)
            current = matched
            tags = (ref_match.group(2) or "").strip()
            if tags:
                per_char_tags.setdefault(matched, []).append(tags)
        elif current is not None and has_colon_ref and current in characters:
            # コロン指定モード: 直前のキャラIDに属するタグ
            per_char_tags.setdefault(current, []).append(entry)
        else:
            # legacyの部分一致、または共有タグ
            matched = next((k for k in characters if entry.lower() in k.lower()), None)
            if matched and matched not in target_chars:
                target_chars.append(matched)
                current = matched
            else:
                shared_parts.append(entry)

    return target_chars, {k: ", ".join(v) for k, v in per_char_tags.items()}, ", ".join(shared_parts)


def compose_image_prompt(raw_prompt: str, characters: dict[str, str], art_style: str = DEFAULT_ART_STYLE) -> str:
    """
    指定された画像プロンプト（シチュエーション文）から登場キャラクター [character_1, ...] を解析し、
    被写体数 + キャラクター外見 + 表情/ポーズ + シチュエーション + artist名 + 品質タグ + アートスタイル を合成する。
    表情/ポーズは各キャラクター外見の直後に配置（全キャラ同一の場合は1回だけ出力）。
    Illustrious系の公式トレーニング順序に準拠（person count → character → situation → artist → quality → style）。
    """
    raw_prompt = raw_prompt.strip().strip('"\'"\"')

    # art_styleからartist名を抽出（"by artist_name"形式）
    artist_name = ""
    style_without_artist = art_style
    artist_match = re.search(r'\s*by\s+([\w-]+)\s*$', art_style)
    if artist_match:
        artist_name = "by " + artist_match.group(1)
        style_without_artist = art_style[:artist_match.start()].rstrip(', ')

    # 括弧 [character_1, ...] の検出 (複数対応)
    bracket_contents = re.findall(r'\[(.*?)\]', raw_prompt)
    target_chars: list[str] = []
    per_char_tags: dict[str, str] = {}
    shared_tags = ""
    clean_situation = re.sub(r'\[[^\]]*\]', '', raw_prompt).strip().strip(', ')

    for tag_content in bracket_contents:
        parsed_targets, parsed_tags, parsed_shared = _parse_image_prompt_targets(tag_content, characters)
        for key in parsed_targets:
            if key not in target_chars:
                target_chars.append(key)
        for key, tags in parsed_tags.items():
            per_char_tags[key] = f"{per_char_tags[key]}, {tags}".strip(", ") if key in per_char_tags else tags
        if parsed_shared and not shared_tags:
            shared_tags = parsed_shared

    # ターゲットキャラが指定されていない場合のフォールバック
    if not target_chars:
        if "character_1" in characters:
            target_chars.append("character_1")
        elif characters:
            target_chars.append(next(iter(characters.keys())))

    # 選択されたキャラのプロンプトリスト
    selected_char_prompts = [characters[k] for k in target_chars if k in characters]

    # キャラ定義が無い場合（技術記事など）
    if not selected_char_prompts:
        parts = []
        if clean_situation:
            parts.append(clean_situation)
        if artist_name:
            parts.append(artist_name)
        parts.append(BASE_QUALITY_PROMPT)
        if style_without_artist:
            parts.append(style_without_artist)
        return ", ".join(parts)

    # 1人の場合
    if len(selected_char_prompts) == 1:
        char_desc = selected_char_prompts[0]
        parts = [char_desc]
        char_tags = per_char_tags.get(target_chars[0], "") if target_chars else ""
        if not char_tags:
            char_tags = shared_tags
        if char_tags:
            parts.append(char_tags)
        if clean_situation:
            parts.append(clean_situation)
        if artist_name:
            parts.append(artist_name)
        parts.append(BASE_QUALITY_PROMPT)
        if style_without_artist:
            parts.append(style_without_artist)
        return ", ".join(parts)

    # 2人以上の場合: 全体カウントタグ（2boys, 1boy and 1girl, 2characters等）を計算
    boys_count = sum(1 for p in selected_char_prompts if re.search(r'\b(1boy|boy|male)\b', p, re.IGNORECASE))
    girls_count = sum(1 for p in selected_char_prompts if re.search(r'\b(1girl|girl|female)\b', p, re.IGNORECASE))
    total_count = len(selected_char_prompts)

    if boys_count == total_count:
        count_tag = f"{total_count}boys"
    elif girls_count == total_count:
        count_tag = f"{total_count}girls"
    elif boys_count > 0 and girls_count > 0 and (boys_count + girls_count == total_count):
        count_tag = f"{boys_count}boy{'s' if boys_count > 1 else ''}, {girls_count}girl{'s' if girls_count > 1 else ''}"
    else:
        count_tag = f"{total_count}characters"

    # 各キャラ定義から単独カウントタグ（1boy, 1girl等）を除去して整理
    cleaned_char_descs = []
    for p in selected_char_prompts:
        cleaned_p = re.sub(r'^\s*(?:1boy|1girl|1other|male|female)\s*,\s*', '', p, flags=re.IGNORECASE).strip()
        cleaned_char_descs.append(cleaned_p)

    # 表情/ポーズタグを各キャラの直後に配置（全キャラ同一の場合は1回だけ出力）
    per_tags = [per_char_tags.get(k, "").strip() for k in target_chars]
    non_empty_tags = [t for t in per_tags if t]
    all_tags_same = (
        len(non_empty_tags) == len(target_chars)
        and len({t.lower() for t in non_empty_tags}) == 1
    )

    if all_tags_same:
        char_block = ", ".join(cleaned_char_descs)
        if non_empty_tags:
            char_block = f"{char_block}, {non_empty_tags[0]}"
    else:
        segments = [f"{desc}, {tags}" if tags else desc for desc, tags in zip(cleaned_char_descs, per_tags)]
        char_block = ", ".join(segments)
    if shared_tags:
        char_block = f"{char_block}, {shared_tags}"

    parts = [count_tag, char_block]
    if clean_situation:
        parts.append(clean_situation)
    if artist_name:
        parts.append(artist_name)
    parts.append(BASE_QUALITY_PROMPT)
    if style_without_artist:
        parts.append(style_without_artist)

    return ", ".join(parts)


# --------------------------------------------------
# 記事テキストから画像プロンプトを抽出する関数
# --------------------------------------------------
def extract_image_prompt(markdown_content: str) -> str:
    """MarkdownのFrontmatterから image_prompt の値を抽出する"""
    match = re.search(r'^image_prompt:\s*["\']?(.*?)["\']?$', markdown_content, re.MULTILINE)
    if match and match.group(1):
        return match.group(1).strip()
    return DEFAULT_SITUATION


# --------------------------------------------------
# 本文内画像の抽出・生成・置換処理
# --------------------------------------------------
def process_inline_images(content: str, file_timestamp: str, characters: dict[str, str], max_images: int = MAX_INLINE_IMAGES, art_style: str = DEFAULT_ART_STYLE, base_seed: int = -1) -> str:
    """本文内の <!-- IMAGE_PROMPT: "..." --> を検出し、画像生成してMarkdown画像記法に置換する。
    base_seed が指定された場合、ヘッダーは base_seed、本文挿絵は base_seed+1, +2... を使用して
    記事内の画像スタイルを一貫させる。"""
    matches = list(INLINE_IMAGE_PATTERN.finditer(content))
    if not matches:
        return content

    print(f"📷 本文内画像プロンプトを {len(matches)} 箇所検出 (上限: {max_images} 枚)")

    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        raw_prompt = match.group(1).strip().strip('"\'“"')

        # 上限枚数を超えたタグは削除
        if idx > max_images:
            content = content.replace(full_tag, "", 1)
            continue

        filename = f"{file_timestamp}-inline-{idx}.png"
        full_prompt = compose_image_prompt(raw_prompt, characters, art_style)
        inline_seed = base_seed if base_seed >= 0 else -1

        print(f"🎨 本文挿絵 {idx}/{min(len(matches), max_images)} 合成プロンプト: {full_prompt}")
        image_url = generate_and_save_image(full_prompt, filename, inline_seed)

        if image_url:
            # 成功時: 前後に空行を入れてMarkdown画像タグに置換
            alt_text = re.sub(r'\[.*?\]', '', raw_prompt).strip().strip(', ')
            alt_text = re.sub(r'\bcharacter_\d+\b', '', alt_text).strip().strip(', ')
            alt_text = alt_text or "Illustration"
            replacement = f"\n\n![{alt_text}]({image_url})\n\n"
            content = content.replace(full_tag, replacement, 1)
        else:
            # 失敗時: 痕跡を残さないよう削除
            content = content.replace(full_tag, "", 1)

    # 念のため残存したタグがあれば消去
    content = INLINE_IMAGE_PATTERN.sub("", content)
    # 連続する過剰な改行を整理
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


# --------------------------------------------------
# 本文内の [character_N] プレースホルダーの置換
# --------------------------------------------------
def replace_character_placeholders(content: str, characters: dict[str, str]) -> str:
    """
    本文内の [character_1], [character_2] などのプレースホルダーを、
    キャラクター設定の最初のタグ（種別）に置換する。
    例: [character_1] → "狼少年" (character_1の最初のタグが "1boy" の場合)
    """
    if not characters:
        return content

    tag_to_japanese = {
        "1boy": "少年",
        "2boys": "二人の少年",
        "1girl": "少女",
        "2girls": "二人の少女",
        "1male": "男性",
        "2males": "二人の男性",
        "1female": "女性",
        "2females": "二人の女性",
    }

    for char_key, char_desc in characters.items():
        tags = [t.strip() for t in char_desc.split(",")]
        first_tag = tags[0] if tags else ""
        replacement = tag_to_japanese.get(first_tag.lower(), first_tag)
        if not replacement:
            replacement = "キャラクター"
        pattern = rf"\[{re.escape(char_key)}\]"
        content = re.sub(pattern, replacement, content)
        content = re.sub(rf"\b{re.escape(char_key)}\b", replacement, content)

    return content


# --------------------------------------------------
# 本文内アフィリエイトプレースホルダーの置換
# --------------------------------------------------
def process_inline_affiliates(content: str) -> str:
    """
    本文内の <!-- AFFILIATE: "keyword" | "anchor" --> を検出し、
    anchorテキストのみ（プレーンテキスト）で置換する。
    商品カードが唯一のリンク表示となるため、本文内はテキストのみ残す。
    """
    matches = list(INLINE_AFFILIATE_PATTERN.finditer(content))
    if not matches:
        return content

    print(f"🔗 本文内アフィリエイトプレースホルダーを {len(matches)} 箇所検出（プレーンテキスト化）")

    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        keyword = match.group(1).strip()
        anchor = match.group(2).strip()

        # プレーンテキストで置換（商品カードが唯一のリンク表示）
        replacement = anchor
        content = content.replace(full_tag, replacement, 1)
        print(f"   🔗 インラインアフィリエイト {idx}: 「{anchor}」→ {keyword}（プレーンテキスト化）")

    # 連続する過剰な改行を整理
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


# --------------------------------------------------
# 比較表内の商品リンクプレースホルダーの置換
# --------------------------------------------------
def process_inline_products(content: str) -> str:
    """
    比較表内の <!-- AFF_PRODUCT: "keyword" --> を検出し、
    Amazon・楽天の検索リンクボタンに置換する。
    さらに楽天APIで商品検索し、比較表の直後に商品画像カードを追加する。
    """
    matches = list(INLINE_AFF_PRODUCT_PATTERN.finditer(content))
    if not matches:
        return content

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")

    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "post"
    utm_content = urllib.parse.quote(title[:50])

    type_match = re.search(r'^prompt_type:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    prompt_type = type_match.group(1).strip() if type_match else "default"

    print(f"🛒 比較表内商品プレースホルダーを {len(matches)} 箇所検出")

    keywords: list[str] = []
    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        keyword = match.group(1).strip()
        encoded_kw = urllib.parse.quote(keyword)

        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        # 比較表内に埋め込むコンパクトなリンク形式
        replacement = f"[Amazon]({amazon_url}) | [楽天]({rakuten_url})"
        content = content.replace(full_tag, replacement, 1)
        print(f"   🛒 商品リンク {idx}: {keyword}")
        keywords.append(keyword)

    # 楽天API商品カードの追加（比較表の直後に挿入）
    cards_html = ""
    seen_kw: set[str] = set()
    for kw in keywords:
        if kw in seen_kw:
            continue
        seen_kw.add(kw)
        if _is_affiliate_bad_keyword(kw):
            continue
        product = _rakuten_search(kw)
        if product and _rakuten_is_relevant(product.get("itemName", ""), kw, prompt_type):
            cards_html += _generate_rakuten_card(product, kw, title)
        elif product:
            print(f"   🛒 [filter] {kw} → 関連性不足、カードをスキップ: {product.get('itemName', '')[:40]}")

    if cards_html:
        # テーブルの最終行を特定し、その直後にカードを挿入
        card_div_open = '<div class="product-card">'
        first_amazon_marker = "amazon.co.jp/s?k="
        end_line = _find_table_end_line(content, first_amazon_marker)
        if end_line is not None:
            lines = content.split('\n')
            lines.insert(end_line + 1, f"\n<div class=\"product-cards\">{cards_html}\n</div>")
            content = '\n'.join(lines)
            card_count = cards_html.count(card_div_open)
            print(f"   🖼️ 楽天API商品カードを {card_count} 枚追加（比較表の直後）")

    return content


# --------------------------------------------------
# アフィリエイトリンク自動挿入
# --------------------------------------------------

# 無意味なキーワードのフィルタリスト（アフィリエイト検索に不適切な語）
_AFFILIATE_BAD_PREFIXES = (
    "a ", "an ", "the ", "how to", "what is", "why ", "best ",
    "top ", "new ", "latest", "review", "tutorial", "guide ",
    "e621", "github", "repo ", "repository", "source code",
    "open source", "free ", "download", "install", "setup ",
)

# キーワード改善辞書：一般的なタグ → 購買意欲の高い検索語
_KEYWORD_ENHANCEMENT = {
    "tech": "プログラミング 入門書",
    "ai": "AI 入門 書籍",
    "pokemon": "ポケモン 公式",
    "game": "ゲーム 周辺機器",
    "programming": "プログラミング 本",
    "web": "Web開発 書籍",
    "javascript": "JavaScript 本",
    "python": "Python 本",
    "rust": "Rust 本",
    "react": "React 書籍",
    "vue": "Vue.js 本",
    "next": "Next.js 書籍",
    "docker": "Docker 入門",
    "linux": "Linux 本",
    "css": "CSS 本",
    "html": "HTML 本",
}


def _is_affiliate_bad_keyword(kw: str) -> bool:
    """アフィリエイト検索に適さないキーワードを判定"""
    kw_lower = kw.lower().strip()
    if len(kw_lower) < 2:
        return True
    for prefix in _AFFILIATE_BAD_PREFIXES:
        if kw_lower.startswith(prefix):
            return True
    # 半角英数字のみで構成され、かつスペースを含む場合は検索不适
    if re.match(r'^[a-zA-Z0-9\s]+$', kw) and kw.count(' ') > 3:
        return True
    return False


def _improve_keyword(kw: str, prompt_type: str) -> str:
    """
    キーワードを購買意欲の高い検索語に改善する。
    技術系は「入門書」「本」などを付与、物語系は関連グッズに転換。
    """
    kw_lower = kw.lower().strip()

    # 辞書で直接マッチする場合は改善語を使用
    for key, improved in _KEYWORD_ENHANCEMENT.items():
        if key in kw_lower:
            return improved

    # prompt_type に応じてサフィックスを付与
    if prompt_type in ("default",):
        # 技術記事: 書籍・グッズを検索
        if re.match(r'^[a-zA-Z]+$', kw):
            return f"{kw} 書籍"
        return f"{kw} 関連グッズ"
    elif prompt_type in ("kemono_story", "novel", "story"):
        # 物語系: キーワードをそのまま使用（作品名のみで検索すれば商品がヒットする）
        return kw

    return kw


def _extract_article_body(content: str) -> str:
    """Frontmatter を除去した記事本文を返す。"""
    m = re.search(r'^---\s*\n.*?\n---\s*\n?', content, re.DOTALL)
    if m:
        return content[m.end():]
    return content


def _is_github_repo_name(keyword: str) -> bool:
    """
    GitHubリポジトリ名（技術識別子）の判定。
    単一の英単語、キャメルケース、ハイフン区切り、または「/」を含むパターンを除外対象とする。
    """
    kw = keyword.strip()
    if not kw:
        return False
    # スラッシュを含む場合はowner/repo形式
    if "/" in kw:
        return True
    # 英字・数字・ハイフン・アンダースコアのみで構成され、日本語文字を含まない
    if re.match(r'^[a-zA-Z0-9_\-]+$', kw) and not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', kw):
        return True
    return False


# --------------------------------------------------
# 楽天市場API 商品検索
# --------------------------------------------------
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RAKUTEN_ORIGIN = "https://bwdsf3104.github.io"
RAKUTEN_REFERER = "https://bwdsf3104.github.io/my-auto-blog/"
RAKUTEN_CACHE_FILE = "data/rakuten_cache.json"
RAKUTEN_CACHE_TTL_DAYS = 30
_rakuten_last_call_time: float = 0.0


def _rakuten_load_cache() -> dict:
    if not os.path.exists(RAKUTEN_CACHE_FILE):
        return {}
    try:
        with open(RAKUTEN_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _rakuten_save_cache(cache: dict):
    os.makedirs(os.path.dirname(RAKUTEN_CACHE_FILE), exist_ok=True)
    now = datetime.now(timezone.utc)
    ttl = timedelta(days=RAKUTEN_CACHE_TTL_DAYS)
    cleaned = {}
    for kw, entry in cache.items():
        try:
            fetched_at = datetime.fromisoformat(entry["fetched_at"])
            if now - fetched_at < ttl:
                cleaned[kw] = entry
        except (KeyError, ValueError):
            continue
    with open(RAKUTEN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)


def _rakuten_search(keyword: str) -> dict | None:
    """
    楽天市場APIで商品を検索し、画像付きの先頭商品を返す。
    30日キャッシュ・429リトライ・呼び出し間隔1.5秒。
    戻り値: {"itemName", "itemPrice", "affiliateUrl", "imageUrl", "reviewCount"} | None
    """
    global _rakuten_last_call_time

    cache = _rakuten_load_cache()
    if keyword in cache:
        entry = cache[keyword]
        try:
            fetched_at = datetime.fromisoformat(entry["fetched_at"])
            if datetime.now(timezone.utc) - fetched_at < timedelta(days=RAKUTEN_CACHE_TTL_DAYS):
                product = entry.get("product")
                if product:
                    print(f"   🛒 [cache] {keyword} → {product['itemName']}")
                else:
                    print(f"   🛒 [cache] {keyword} → 商品なし（キャッシュ）")
                return product
        except (KeyError, ValueError):
            pass

    app_id = os.environ.get("RAKUTEN_APPLICATION_ID", "")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
    if not app_id or not access_key:
        print(f"   ⚠️ 楽天APIクレデンシャル未設定: 「{keyword}」をスキップ")
        return None

    elapsed = time.time() - _rakuten_last_call_time
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)

    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "affiliateId": affiliate_id,
        "keyword": keyword,
        "hits": 3,
        "sort": "-reviewCount",
        "format": "json",
        "formatVersion": "2",
    }
    headers = {"Origin": RAKUTEN_ORIGIN, "Referer": RAKUTEN_REFERER}

    max_retries = 3
    for attempt in range(max_retries):
        _rakuten_last_call_time = time.time()
        try:
            resp = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = 2 * (attempt + 1)
                print(f"   ⏳ 楽天API 429: {wait}秒待機 ({attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            items = data.get("Items", [])

            product = None
            for item in items:
                images = item.get("mediumImageUrls") or []
                if images and images[0]:
                    product = {
                        "itemName": item.get("itemName", ""),
                        "itemPrice": item.get("itemPrice", 0),
                        "affiliateUrl": item.get("affiliateUrl") or item.get("itemUrl", ""),
                        "imageUrl": images[0],
                        "reviewCount": item.get("reviewCount", 0),
                    }
                    break

            cache[keyword] = {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "product": product,
                "hits": len(items),
            }
            _rakuten_save_cache(cache)

            if product:
                print(f"   🛒 [rakuten] {keyword} → {product['itemName']} (¥{product['itemPrice']:,})")
            else:
                print(f"   🛒 [rakuten] {keyword} → 画像付き商品なし（{len(items)}件）")
            return product

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 * (attempt + 1)
                print(f"   ⚠️ 楽天APIエラー: {e} — {wait}秒待機 ({attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"   ❌ 楽天API失敗: 「{keyword}」— {e}")
                return None

    return None


def _generate_rakuten_card(product: dict, keyword: str, title: str) -> str:
    """楽天API商品から商品カードHTMLを生成（既存 .product-card 体系に統合）"""
    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    encoded_kw = urllib.parse.quote(keyword)
    utm_content = urllib.parse.quote(title[:50])
    amazon_url = (
        f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
        f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
    )
    price = product.get("itemPrice", 0)
    price_html = f'<div class="pc-price">¥{price:,}</div>' if price else ""
    name = product.get("itemName", "")
    img = product.get("imageUrl", "")
    afl = product.get("affiliateUrl", "")
    return f"""
<div class="product-card">
  <img class="pc-img" src="{img}" alt="{name}" loading="lazy" />
  <div class="pc-info">
    <div class="pc-name">{name}</div>
    <div class="pc-category">{keyword}</div>
    {price_html}
  </div>
  <div class="pc-links">
    <a href="{amazon_url}" target="_blank" rel="noopener noreferrer nofollow" class="pc-btn pc-btn-amazon">Amazon</a>
    <a href="{afl}" target="_blank" rel="noopener noreferrer nofollow sponsored" class="pc-btn pc-btn-rakuten">楽天</a>
  </div>
</div>"""


def _find_table_end_line(content: str, marker: str) -> int | None:
    """markerを含むmarkdownテーブルの最終行の行番号（0始まり）を返す"""
    lines = content.split('\n')
    marker_idx = None
    for i, line in enumerate(lines):
        if marker in line:
            marker_idx = i
            break
    if marker_idx is None:
        return None
    end_idx = marker_idx
    while end_idx + 1 < len(lines) and lines[end_idx + 1].strip().startswith('|'):
        end_idx += 1
    return end_idx


def _extract_article_keywords(content: str, max_kw: int = 2, prompt_type: str = "default") -> list[str]:
    """
    記事本文（Frontmatter後のテキスト）からテーマキーワードを抽出。
    1. Frontmatterのtagsを優先使用
    2. 本文の先頭 paragraphs から日本語のキーワード候補を抽出
    """
    body = _extract_article_body(content)
    keywords: list[str] = []
    seen = set()

    # 1. tags から抽出
    tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
    if tags_match:
        for t in tags_match.group(1).split(','):
            tag = t.strip().strip('"\'')
            if tag and len(tag) >= 2 and tag not in seen:
                # 日本語フィルタ（一旦無効化: SF/TF/BL等の英字タグも通す）
                # if prompt_type in ("kemono_story", "novel", "story"):
                #     if not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', tag):
                #         continue
                seen.add(tag)
                keywords.append(tag)
                if len(keywords) >= max_kw:
                    return keywords

    # 2. 本文の先頭2段落から日本語のキーワード候補を抽出
    paragraphs = re.split(r'\n\s*\n', body.strip())
    jp_chunks: list[str] = []
    for para in paragraphs[:2]:
        # マークダウン記号を除去
        para = re.sub(r'[#*\-\[]>`]', '', para)
        # 日本語の単語候補を抽出（2文字以上の連続日本語文字列）
        matches = re.findall(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]{2,}', para)
        for m in matches:
            if m not in seen and len(m) >= 2:
                seen.add(m)
                jp_chunks.append(m)

    # 先頭からキーワードを補充
    for kw in jp_chunks:
        if len(keywords) >= max_kw:
            break
        keywords.append(kw)

    return keywords


_KEMONO_RELATIONSHIP_AFFILIATE = {
    "partnership": "バディ",
    "yaoi": "BL",
    "yuri": "百合",
    "hetero": "恋愛",
}


def _build_kemono_tags(kemono_params: dict) -> list[str]:
    """kemono_story のパラメータからタグリストを生成する。

    スクリプト内で決定した構造化データ（char_types / world_tags / extra_tag）を
    直接使用するため、文字列の結合・分割処理は不要。

    生成順:
    1. ケモノ（固定）
    2. キャラ体型タグ（char_types の各要素を個別タグに）
    3. 世界設定タグ（world_tags の各要素を個別タグに）
    4. キャラ関係性タグ（_KEMONO_RELATIONSHIP_AFFILIATE）
    5. 追加設定タグ（extra_tag、空なら省略）
    """
    tags = ["ケモノ"]
    tags.extend(kemono_params["char_types"])
    tags.extend(kemono_params["world_tags"])
    rel = _KEMONO_RELATIONSHIP_AFFILIATE.get(kemono_params.get("relationship_key", ""), "")
    if rel:
        tags.append(rel)
    extra = kemono_params.get("extra_tag", "")
    if extra:
        tags.append(extra)
    return tags


def _kemono_affiliate_keywords(kemono_params: dict) -> list[str]:
    """kemono_story のスクリプト決定パラメータからアフィリエイト検索キーワードを生成。

    生成順:
    1. ケモノ単体
    2. ジャンル単体（world_tags）
    3. キャラ関係性単体
    4. ケモノ + ジャンル
    5. ケモノ + キャラ関係性
    """
    kws: list[str] = []

    # 1. ケモノ単体
    kws.append("ケモノ")

    # 2. ジャンル（world_tags）を単体使用
    genres = list(kemono_params["world_tags"])
    for g in genres:
        kws.append(g)

    # 3. キャラ関係性単体
    rel_key = kemono_params.get("relationship_key", "")
    relationship = _KEMONO_RELATIONSHIP_AFFILIATE.get(rel_key, "")
    if relationship:
        kws.append(relationship)

    # 4. ケモノ + ジャンル
    for g in genres:
        kws.append(f"ケモノ {g}")

    # 5. ケモノ + キャラ関係性
    if relationship:
        kws.append(f"ケモノ {relationship}")

    # 重複排除（順序維持）
    seen: set[str] = set()
    result: list[str] = []
    for kw in kws:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


# kemono_story 商品名の関連性判定トークン（固定リスト）
_KEMONO_CORE_TOKENS = ("ケモノ", "バケモノ", "獣人", "獣", "動物", "アニマル", "anthro", "beast")
_KEMONO_ANCHOR_KEYWORDS = ("ケモノ", "獣人", "動物")


def _rakuten_is_relevant(item_name: str, keyword: str, prompt_type: str) -> bool:
    """楽天検索結果の関連性を判定する。

    - kemono_story の汎用キーワード（ケモノ/獣人/動物/ケモノ＋ジャンル/関係性）:
      商品名にコアトークンを1つ以上含むこと
    - その他（Gemini商品名・tech系）:
      検索キーワードの実語トークン（2文字以上）が商品名に1つ以上含まれること
    """
    name = item_name.lower()
    is_kemono_generic = (
        prompt_type == "kemono_story"
        and (keyword in _KEMONO_ANCHOR_KEYWORDS or keyword.startswith("ケモノ "))
    )
    if is_kemono_generic:
        return any(tok in name for tok in _KEMONO_CORE_TOKENS)
    tokens = [t for t in keyword.split() if len(t) >= 2]
    if not tokens:
        return True
    return any(t.lower() in name for t in tokens)


# 先頭句分割用の区切り語（長いもの優先に並べる。平仮名1文字は単語内で使われるため使わない）
_RAKUTEN_PHRASE_DELIMITERS = r'(?:用的|向け|用|的)'


def _rakuten_first_phrase(name: str) -> str:
    """Gemini生成商品名から先頭句を抽出する。

    スペースと区切り語（用的/向け/用/的）で分割し先頭セグメントを採用する。
    平仮名1文字（の/に/へ/と/や）は「にゃんこ」の「に」「けもの」の「の」のように
    単語内で使われるため、区切り語に含めない。
    先頭セグメントが2文字未満なら2番目のセグメントを連結する。
    区切りがどこにも無く商品名そのまま（1語）になる場合は、
    既に検索済みの商品名と重複するため空文字を返す（スキップ）。
    """
    name = name.strip()
    if not name:
        return ""
    segments = [s for s in re.split(r'\s+|' + _RAKUTEN_PHRASE_DELIMITERS, name) if s]
    if len(segments) < 2:
        return ""
    phrase = segments[0]
    if len(phrase) < 2:
        phrase = f"{phrase} {segments[1]}"
    if phrase == name:
        return ""
    return phrase


def _rakuten_api_keywords(
    gemini_products: list[str] | None,
    base_keywords: list[str],
    prompt_type: str,
    kemono_params: dict | None,
) -> list[str]:
    """楽天API検索キーワードリスト（カスケード順序）を構築する。

    kemono_story:
      Gemini商品名 → 先頭句 → ケモノ+ジャンル → ケモノ+関係性 → ケモノ → 獣人 → 動物
    その他:
      Gemini商品名 → 先頭句 → 基底キーワード（既存の改善キーワード）

    ジャンル単体語・関係性単体語はAPIに送らない（検索リンクのみ）。
    英語のみのキーワードも送らない（楽天では0ヒット）。
    """
    kws: list[str] = []
    for name in gemini_products or []:
        name = name.strip()
        if not name or _is_affiliate_bad_keyword(name):
            continue
        if not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', name):
            continue
        kws.append(name)
        phrase = _rakuten_first_phrase(name)
        if phrase and phrase != name and not _is_affiliate_bad_keyword(phrase):
            kws.append(phrase)

    if prompt_type == "kemono_story" and kemono_params:
        for g in kemono_params.get("world_tags", []):
            kws.append(f"ケモノ {g}")
        rel = _KEMONO_RELATIONSHIP_AFFILIATE.get((kemono_params or {}).get("relationship_key", ""), "")
        if rel:
            kws.append(f"ケモノ {rel}")
        kws.extend(_KEMONO_ANCHOR_KEYWORDS)
    else:
        kws.extend(base_keywords)

    # 重複排除（順序維持）
    seen: set[str] = set()
    result: list[str] = []
    for kw in kws:
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def _rakuten_collect(keywords: list[str], prompt_type: str, max_products: int = 3) -> list[tuple[str, dict]]:
    """カスケード順序で楽天を順次検索し、関連性フィルタ通過した最大 max_products 商品を収集する。

    max_products 到達で即停止。同一商品（affiliateUrl）は重複排除する。
    戻り値: (keyword, product) タプルのリスト。
    """
    collected: list[tuple[str, dict]] = []
    seen_urls: set[str] = set()
    for kw in keywords:
        if len(collected) >= max_products:
            break
        product = _rakuten_search(kw)
        if not product:
            continue
        if not _rakuten_is_relevant(product.get("itemName", ""), kw, prompt_type):
            print(f"   🛒 [filter] {kw} → 関連性不足、スキップ: {product.get('itemName', '')[:40]}")
            continue
        url = product.get("affiliateUrl", "")
        if url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        collected.append((kw, product))
    return collected


def inject_affiliate_links(content: str, trend_keywords: list[str] = None, script_keywords: list[str] = None, file_timestamp: str = None, gemini_products: list[str] = None, kemono_params: dict = None) -> str:
    """
    記事末尾にAmazon・楽天のアフィリエイト検索リンクブロックを自動挿入する。

    キーワード優先順位:
    1. script_keywords（スクリプトが直接生成したキーワード。ストーリー系）
    2. trend_keywords（GitHubリポジトリ名は除外）
    3. tags / title のフォールバック

    改善点:
    - スクリプト決定パラメータからキーワード生成（ストーリー系）
    - UTM パラメータによるトラッキング
    - 複数のプラットフォーム対応
    - 購買意欲を促すCTA文言
    """
    if "関連のおすすめアイテム" in content or "スポンサーリンク" in content:
        return content

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")

    # prompt_type を取得（キーワード改善用）
    type_match = re.search(r'^prompt_type:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    prompt_type = type_match.group(1).strip() if type_match else "default"

    keywords_to_use: list[str] = []
    keyword_sources: list[str] = []

    # 1. スクリプトが直接生成したキーワード（最優先）
    if script_keywords:
        for kw in script_keywords:
            if not _is_affiliate_bad_keyword(kw):
                keywords_to_use.append(kw)
                keyword_sources.append("script")
    else:
        # フォールバック: 記事本文からテーマキーワードを抽出
        article_kw = _extract_article_keywords(content, max_kw=2, prompt_type=prompt_type)
        for kw in article_kw:
            if _is_affiliate_bad_keyword(kw):
                continue
            improved = _improve_keyword(kw, prompt_type)
            keywords_to_use.append(improved)
            keyword_sources.append("article_extract")

    # 2. trend_keywords を補充（GitHubリポジトリ名は除外）
    if trend_keywords and len(keywords_to_use) < 3:
        seen = set(k.replace(" 書籍", "").replace(" 関連グッズ", "").replace(" 関連作品", "") for k in keywords_to_use)
        for kw in trend_keywords:
            kw_clean = kw.strip()
            if _is_github_repo_name(kw_clean):
                continue
            if _is_affiliate_bad_keyword(kw_clean):
                continue
            if kw_clean in seen:
                continue
            seen.add(kw_clean)
            improved = _improve_keyword(kw_clean, prompt_type)
            keywords_to_use.append(improved)
            keyword_sources.append("trend")
            if len(keywords_to_use) >= 3:
                break

    # 3. 全て空の場合は tags / title 抽出にフォールバック
    if not keywords_to_use:
        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else ""

        tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
        keyword = None
        if tags_match:
            tag_items = [t.strip().strip('"\'') for t in tags_match.group(1).split(',') if t.strip()]
            if tag_items:
                keyword = tag_items[0]

        if not keyword:
            cleaned = re.sub(r'[【】「」『』\[\]()（）\s]', ' ', title).strip()
            words = [w for w in cleaned.split() if len(w) > 1]
            keyword = words[0] if words else None

        if keyword:
            keywords_to_use = [_improve_keyword(keyword, prompt_type)]
            keyword_sources = ["fallback_tags_title"]
        else:
            # 最終フォールバック
            if prompt_type in ("kemono_story", "novel", "story"):
                keywords_to_use = ["ライトノベル おすすめ"]
            else:
                keywords_to_use = ["プログラミング 入門書"]
            keyword_sources = ["fallback_default"]

    # UTM トラッキングパラメータ
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    utm_content = urllib.parse.quote((title_match.group(1).strip() if title_match else "post")[:50])

    links_html = ""
    link_log_entries: list[dict] = []
    for i, kw in enumerate(keywords_to_use):
        encoded_kw = urllib.parse.quote(kw)

        # Amazon: 検索リンク + UTM
        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        # Rakuten: 検索リンク
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        links_html += f'\n- 📦 <a href="{amazon_url}" target="_blank" rel="noopener noreferrer nofollow sponsored">Amazonで「{kw}」を探す</a>'
        links_html += f'\n- 🛍️ <a href="{rakuten_url}" target="_blank" rel="noopener noreferrer nofollow sponsored">楽天市場で「{kw}」を探す</a>'
        link_log_entries.append({
            "keyword": kw,
            "source": keyword_sources[i] if i < len(keyword_sources) else "unknown",
            "amazon_url": amazon_url,
            "rakuten_url": rakuten_url,
        })

    # 楽天API商品カードの生成（末尾セクション一番上に追加）
    # カスケード検索: キーワードを優先順位順に辿り、関連性フィルタ通過した最大3商品を収集
    title_for_card = (title_match.group(1).strip() if title_match else "post")
    api_keywords = _rakuten_api_keywords(gemini_products, keywords_to_use, prompt_type, kemono_params)
    collected = _rakuten_collect(api_keywords, prompt_type, max_products=3)
    rakuten_cards_html = "".join(
        _generate_rakuten_card(product, kw, title_for_card) for kw, product in collected
    )
    if rakuten_cards_html:
        card_div_open = '<div class="product-card">'
        card_count = rakuten_cards_html.count(card_div_open)
        rakuten_cards_html = f'\n<div class="product-cards">{rakuten_cards_html}\n</div>'
        print(f"   🖼️ 楽天API商品カードを末尾セクションに {card_count} 枚追加")

    # 複数キーワードがある場合はセクションを分割
    sections = ""
    if len(keywords_to_use) > 1:
        # 1つ目のキーワードはメインCTAとして強調
        kw0 = keywords_to_use[0]
        encoded_kw0 = urllib.parse.quote(kw0)
        main_amazon = (
            f"https://www.amazon.co.jp/s?k={encoded_kw0}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )
        sections = f"""
<div style="background: linear-gradient(135deg, #fef3c7, #fde68a); border: 2px solid #f59e0b; border-radius: 12px; padding: 16px 20px; margin: 16px 0; text-align: center;">
<p style="font-size: 1.1em; font-weight: bold; margin: 0 0 12px 0;">🔥 「{kw0}」の今すぐチェックできるおすすめアイテム</p>
<a href="{main_amazon}" style="display: inline-block; background: #f59e0b; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 1em;">Amazonで確認する →</a>
</div>"""

    affiliate_section = f"""

---

### 📚 テーマ関連のおすすめアイテム・書籍
この記事のテーマに関連する作品や人気アイテムをチェック！{rakuten_cards_html}{sections}{links_html}

<small style="color: #64748b;">※ 当サイトはアフィリエイト広告（Amazonアソシエイト・楽天アフィリエイト等）を利用して収益を得ています。</small>
"""

    # リンク生成ログの保存
    if file_timestamp:
        title_match_log = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
        article_title = title_match_log.group(1).strip() if title_match_log else ""
        _save_affiliate_link_log(file_timestamp, prompt_type, article_title, link_log_entries)

    return content.strip() + "\n" + affiliate_section



# --------------------------------------------------
# 2-pass 生成: 下書きの精製
# プロンプトは scripts/prompts/refine_tech.txt, refine_story.txt に分離


def refine_content(draft: str, prompt_type: str):
    """
    下書き記事を2回目のGemini API呼び出しで精製する。
    技術記事と物語で異なる精製プロンプトを使用する。
    返り値: (refined_content, model_name) のタプル。
    失敗時は (draft, None) を返す。
    """
    if prompt_type in ("kemono_story", "novel", "story"):
        refine_template = load_prompt_template("refine_story")
    else:
        refine_template = load_prompt_template("refine_tech")
    refine_prompt = refine_template + f"\n\n【下書き】\n{draft}"

    try:
        print("✨ 2-pass 精製中...")
        response, model_name = generate_content_with_retry(refine_prompt)
        refined = response.text.strip()

        # コードブロック装飾の除外
        if refined.startswith("```"):
            lines = refined.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            refined = "\n".join(lines)

        print("✨ 精製完了")
        return (refined.strip(), model_name)
    except Exception as e:
        print(f"⚠️ 精製パスでエラーが発生しました: {e}")
        print("⚠️ 下書きのまま続行します")
        return (draft, None)


# --------------------------------------------------
# Gemini API 呼び出し
# --------------------------------------------------
def generate_content_with_retry(prompt):
    """Gemini APIを呼び出して (response, model_name) のタプルを返す。"""
    max_retries = 3
    for model_name in MODELS_TO_TRY:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Gemini API ({model_name}) リクエスト中... (試行 {attempt}/{max_retries})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return (response, model_name)
            except errors.APIError as e:
                err_str = str(e)
                if "404" in err_str or "NOT_FOUND" in err_str:
                    break
                if attempt < max_retries:
                    time.sleep(5 * (2 ** (attempt - 1)))
                else:
                    break
            except Exception:
                if attempt < max_retries:
                    time.sleep(5 * (2 ** (attempt - 1)))
                else:
                    break
    raise RuntimeError("すべてのモデルおよび再試行が失敗しました。")


# --------------------------------------------------
# トレンドトピック注入ヘルパー
# --------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_DIR = os.path.join(PROJECT_DIR, "data", "topics")
TOPICS_JSON_PATH = os.path.join(TOPICS_DIR, "latest.json")

def _check_topics_ttl(data: dict) -> bool:
    """
    TTL検証: fetched_at から経過時間が ttl_hours を超えているかチェック。
    超過時はTrueを返し、警告を出力する。
    """
    fetched_at_str = data.get("fetched_at", "")
    if not fetched_at_str:
        print("[topics] fetched_at が存在しません。TTL検証をスキップします。")
        return False

    try:
        fetched_at = datetime.fromisoformat(fetched_at_str)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone(timedelta(hours=9)))
        now = datetime.now(timezone(timedelta(hours=9)))
        ttl_hours = data.get("ttl_hours", 24)
        elapsed = (now - fetched_at).total_seconds() / 3600
        if elapsed > ttl_hours:
            print(f"[topics] 注意: トピックスデータが {elapsed:.1f} 時間前（TTL {ttl_hours}h を超過）です。最新データを取得してください。")
            return True
    except Exception as e:
        print(f"[topics] TTL検証でエラーが発生しました: {e}")
    return False


def _check_per_source_ttl(data: dict, categories: list[str]) -> dict[str, bool]:
    """
    Per-source TTL検証: sources の各エントリの fetched_at をチェック。

    要求カテゴリのトピックを持たない source の扱い:
    - トピックを持つ source（他カテゴリ専属: pokemon 系等）: 対象外として False（期限切れ扱いしない）
    - トピック 0 件の source（完全失敗・未収集）: 従来どおり期限切れ True
    戻り値: {source_name: is_expired} ディクショナリ
    """
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    ttl_hours = data.get("ttl_hours", 24)
    sources = data.get("sources", {})
    by_category = data.get("by_category", {})
    expired = {}

    for src_name, src_data in sources.items():
        src_topics = src_data.get("topics", [])
        src_cats = set(t.get("category", "other") for t in src_topics)
        if not src_cats & set(categories):
            if src_cats:
                # 他カテゴリ専属の source は本チェックの対象外（自動fetchのトリガーにしない）
                expired[src_name] = False
                continue
            # トピック 0 件（完全失敗・未収集）は従来どおり期限切れ
            expired[src_name] = True
            continue
        fetched_at_str = src_data.get("fetched_at", "")
        if not fetched_at_str:
            expired[src_name] = True
            continue
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=JST)
            elapsed = (now - fetched_at).total_seconds() / 3600
            expired[src_name] = elapsed > ttl_hours
        except Exception:
            expired[src_name] = True

    return expired


def _auto_fetch_topics(prompt_type: str, categories: list[str], data: dict) -> dict | None:
    """
    指定カテゴリのトピックが不足している場合、fetch_topics.py を自動実行して最新データを取得。
    取得成功時は新しいデータdictを返し、失敗時はNoneを返す。
    """
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    ttl_hours = data.get("ttl_hours", 24)
    by_category = data.get("by_category", {})

    need_fetch = False
    for cat in categories:
        cat_items = by_category.get(cat, [])
        if len(cat_items) == 0:
            need_fetch = True
            break

    if not need_fetch:
        sources = data.get("sources", {})
        expired = _check_per_source_ttl(data, categories)
        for src, is_exp in expired.items():
            if is_exp:
                need_fetch = True
                break

    if not need_fetch:
        return None

    print(f"[topics] カテゴリ {categories} のデータが不足/期限切れです。自動取得を開始します。")
    try:
        result = subprocess.run(
            [sys.executable, "-u", os.path.join(PROJECT_DIR, "scripts", "fetch_topics.py"), "--prompt-type", prompt_type],
            capture_output=True, text=True, timeout=120, encoding="utf-8"
        )
        if result.returncode != 0:
            print(f"[topics] 自動取得失敗 (exit={result.returncode}): {result.stderr.strip()}")
            return None
        print(f"[topics] 自動取得完了: {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else 'ok'}")
    except subprocess.TimeoutExpired:
        print("[topics] 自動取得がタイムアウトしました")
        return None
    except Exception as e:
        print(f"[topics] 自動取得エラー: {e}")
        return None

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[topics] 自動取得後のJSON読み込み失敗: {e}")
        return None


# --------------------------------------------------
# Trend usage logging
# --------------------------------------------------
TREND_USAGE_DIR = "data/trend_usage_logs"

def _save_trend_usage_log(log_data: dict):
    """
    テンデントデータの使用状況を JSON ログとして保存する。
    候補プールの統計、フィルタ結果、選択されたトピックのメタデータを記録。
    """
    os.makedirs(TREND_USAGE_DIR, exist_ok=True)
    JST = timezone(timedelta(hours=9))
    timestamp = datetime.now(JST).strftime("%Y-%m-%d-%H%M%S")
    filepath = os.path.join(TREND_USAGE_DIR, f"{timestamp}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"[trend_log] 使用状況ログを保存: {filepath}")


# --------------------------------------------------
# Draft metadata tracking (2-pass 生成の追跡)
# --------------------------------------------------
DRAFTS_DIR = "data/drafts"


def _save_draft_metadata(
    file_timestamp: str,
    prompt_type: str,
    article_filename: str,
    draft_content: str,
    refined_content: str,
    pass1_model: str,
    pass1_duration: float,
    pass2_model: str,
    pass2_duration: float,
):
    """
    2-pass生成のメタデータを JSON として保存する。
    1回目（下書き）と2回目（精製）の内容・モデル・時間を記録。
    """
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    filepath = os.path.join(DRAFTS_DIR, f"{file_timestamp}.json")

    draft_char_count = len(draft_content)
    draft_line_count = draft_content.count("\n") + 1
    refined_char_count = len(refined_content)
    refined_line_count = refined_content.count("\n") + 1

    metadata = {
        "timestamp": file_timestamp,
        "prompt_type": prompt_type,
        "article_file": article_filename,
        "pass1": {
            "model": pass1_model,
            "duration_seconds": round(pass1_duration, 2),
            "content_char_count": draft_char_count,
            "content_line_count": draft_line_count,
            "content": draft_content,
        },
        "pass2": {
            "model": pass2_model,
            "duration_seconds": round(pass2_duration, 2),
            "content_char_count": refined_char_count,
            "content_line_count": refined_line_count,
            "content": refined_content,
        },
        "diff_stats": {
            "char_count_change": refined_char_count - draft_char_count,
            "line_count_change": refined_line_count - draft_line_count,
            "char_count_change_percent": round(
                (refined_char_count - draft_char_count) / draft_char_count * 100, 2
            ) if draft_char_count else 0,
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"[draft_meta] 2-passメタデータを保存: {filepath}")


# --------------------------------------------------
# Affiliate link generation log
# --------------------------------------------------
AFFILIATE_LINKS_DIR = "data/affiliate_logs"


def _save_affiliate_link_log(
    file_timestamp: str,
    prompt_type: str,
    article_title: str,
    keywords: list[dict],
):
    """
    アフィリエイト末尾セクションのキーワード・URL生成ログをJSON保存する。
    keywords: [{"keyword": str, "source": str, "amazon_url": str, "rakuten_url": str}, ...]
    """
    os.makedirs(AFFILIATE_LINKS_DIR, exist_ok=True)
    filepath = os.path.join(AFFILIATE_LINKS_DIR, f"{file_timestamp}.json")
    log_data = {
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "file_timestamp": file_timestamp,
        "prompt_type": prompt_type,
        "article_title": article_title,
        "keywords": keywords,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"[affiliate_log] リンク生成ログを保存: {filepath}")


# --------------------------------------------------
# Log / metadata cleanup (time-based)
# --------------------------------------------------
LOG_CLEANUP_DAYS = 30
LOG_CLEANUP_DIRS = [
    DRAFTS_DIR,
    TREND_USAGE_DIR,
    AFFILIATE_LINKS_DIR,
    os.path.join("data", "prompt_logs"),
]
_LOG_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})\.")


def _cleanup_old_logs(days: int = LOG_CLEANUP_DAYS) -> int:
    """
    ログ・メタデータディレクトリから `days` 日より古いファイルを削除する。
    ファイル名内のタイムスタンプ（%Y-%m-%d-%H%M%S）を基準とする。
    これらはパイプラインから読み戻されない監査ログのため削除して安全。
    タイムスタンプ形式に合わないファイルは削除対象外（安全側）。
    削除したファイル数を返す。
    """
    cutoff = datetime.now(timezone(timedelta(hours=9))) - timedelta(days=days)
    removed = 0
    for dir_path in LOG_CLEANUP_DIRS:
        if not os.path.isdir(dir_path):
            continue
        for name in os.listdir(dir_path):
            if name == ".gitkeep":
                continue
            full = os.path.join(dir_path, name)
            if not os.path.isfile(full):
                continue
            m = _LOG_TS_RE.match(name)
            if not m:
                continue
            try:
                file_time = datetime.strptime(m.group(1), "%Y-%m-%d-%H%M%S").replace(
                    tzinfo=timezone(timedelta(hours=9))
                )
            except ValueError:
                continue
            if file_time < cutoff:
                try:
                    os.remove(full)
                    removed += 1
                except OSError as e:
                    print(f"[cleanup] 削除に失敗: {full}: {e}")
    if removed:
        print(f"[cleanup] 古いログファイル {removed} 件を削除（{days}日前）")
    return removed


def _append_trending_topics(
    ng_instruction: str,
    prompt_type: str,
    target_genres: list[str] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    """
    data/topics/latest.json が存在する場合、prompt_type に応じたカテゴリの
    トレンドタイトルを選択して ng_instruction の末尾へ付加する。
    target_genres が指定されている場合、事前スコアリング結果で
    ジャンル適合度の高い項目を優先選択する。
    Per-source TTL で期限切れのカテゴリがある場合は自動再取得を試みる。
    第2要素としてアフィリエイト用のトレンドキーワードリストを返す。
    第3要素として frontmatter 用のソースURLリストを返す。
    第4要素として生成情報セクション用のクリーンなトレンドタイトルリスト
    （"{title}（{source}）" 形式）を返す。
    ファイルが存在しない場合は元の ng_instruction と空リストを返す。
    """
    if not os.path.exists(TOPICS_JSON_PATH):
        print(f"[topics] {TOPICS_JSON_PATH} が見つかりません。トレンド注入をスキップします。")
        _save_trend_usage_log({
            "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "prompt_type": prompt_type,
            "data_file": TOPICS_JSON_PATH,
            "skipped": "file_not_found",
            "selected": [],
            "affiliate_keywords": [],
            "trend_source_urls": [],
        })
        return ng_instruction, [], [], []

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[topics] JSON 読み込み失敗: {e}")
        _save_trend_usage_log({
            "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "prompt_type": prompt_type,
            "data_file": TOPICS_JSON_PATH,
            "skipped": f"json_parse_error: {e}",
            "selected": [],
            "affiliate_keywords": [],
            "trend_source_urls": [],
        })
        return ng_instruction, [], [], []

    # prompt_type に合わせてカテゴリを選択（カテゴリ厳格化）
    if prompt_type in ("kemono_story", "novel", "story"):
        categories = ["kemono"]
    elif prompt_type == "default":
        categories = ["tech"]
    else:
        categories = ["tech", "kemono"]

    # Per-source TTL 検証（グローバルTTLも確認）
    global_expired = _check_topics_ttl(data)
    if global_expired:
        print("[topics] グローバルTTL超過")
    expired = _check_per_source_ttl(data, categories)
    has_expired = any(expired.values())
    if has_expired:
        expired_names = [s for s, v in expired.items() if v]
        print(f"[topics] 期限切れ source: {', '.join(expired_names)}")

    # 期限切れの場合、自動再取得
    if has_expired:
        new_data = _auto_fetch_topics(prompt_type, categories, data)
        if new_data:
            data = new_data

    by_cat = data.get("by_category", {})
    selected_titles: list[str] = []
    affiliate_keywords: list[str] = []
    trend_source_urls: list[str] = []
    trend_topic_titles: list[str] = []
    story_mode = prompt_type in ("kemono_story", "novel", "story")

    # Log tracking variables
    log_raw_count = 0
    log_after_score = 0
    log_after_rating = 0
    selected_items: list[dict] = []

    # 全カテゴリから候補を収集
    candidates: list[dict] = []
    for cat in categories:
        for item in by_cat.get(cat, []):
            log_raw_count += 1
            # スコアしきい値フィルタ
            if item.get("score", 0) < MIN_SCORE_THRESHOLD:
                continue
            log_after_score += 1
            # カテゴリ厳格化: 物語モードでは e621 全投稿をインスピレーション注入から除外
            # e621 はキャラクター特徴集計にのみ使用し、ストーリーテーマのインスピレーションには不適切
            if story_mode and item.get("source") == "e621":
                continue
            log_after_rating += 1
            title = item.get("title", "").strip()
            if title:
                candidates.append(item)

    TREND_SELECT_COUNT = 2
    if target_genres:
        scores_data = _load_genre_scores()
        if scores_data:
            candidates = _filter_by_genre(candidates, target_genres, scores_data)
    if len(candidates) > TREND_SELECT_COUNT:
        candidates = random.sample(candidates[:TREND_SELECT_COUNT * 3], TREND_SELECT_COUNT)

    for item in candidates:
        title = item.get("title", "").strip()
        source = item.get("source", "")
        url = item.get("url", "")
        desc = (item.get("description") or "").strip()
        if title:
            line = f"[{source}] {title}"
            if desc:
                line += f" — {desc[:100]}"
            selected_titles.append(line)
            trend_topic_titles.append(f"{title}（{source}）" if source else title)
            if url:
                trend_source_urls.append(url)
            selected_items.append({
                "title": title,
                "source": source,
                "url": url,
                "score": item.get("score", 0),
                "category": item.get("category", ""),
                "rating": item.get("rating", ""),
                "description": desc[:200],
            })
        # アフィリエイトキーワードは全カテゴリから抽出
        kw = _extract_affiliate_keyword(title)
        if kw:
            affiliate_keywords.append(kw)

    # TTL 情報をログに記録
    ttl_hours = data.get("ttl_hours", 24)
    fetched_at = data.get("fetched_at", "")
    per_source_ttl = data.get("per_source_ttl", {})

    if fetched_at:
        try:
            JST = timezone(timedelta(hours=9))
            fetched_dt = datetime.fromisoformat(fetched_at)
            if fetched_dt.tzinfo is None:
                fetched_dt = fetched_dt.replace(tzinfo=JST)
            elapsed = (datetime.now(JST) - fetched_dt).total_seconds() / 3600
        except Exception:
            elapsed = -1
    else:
        elapsed = -1

    # Trend usage log を保存
    _save_trend_usage_log({
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "prompt_type": prompt_type,
        "data_file": TOPICS_JSON_PATH,
        "data_fetched_at": fetched_at,
        "global_ttl": {
            "ttl_hours": ttl_hours,
            "elapsed_hours": round(elapsed, 2) if elapsed >= 0 else None,
            "expired": global_expired,
        },
        "per_source_ttl": {src: info.get("expired", False) for src, info in per_source_ttl.items()},
        "auto_fetch": {
            "triggered": has_expired,
            "success": data is not None,
        },
        "candidate_pool": {
            "categories": categories,
            "total_raw": log_raw_count,
            "after_score_filter": log_after_score,
            "after_rating_filter": log_after_rating,
            "final_candidates": len(candidates),
        },
        "selected": selected_items,
        "affiliate_keywords": affiliate_keywords,
        "trend_source_urls": trend_source_urls[:10],
    })

    if not selected_titles:
        return ng_instruction, affiliate_keywords, trend_source_urls, trend_topic_titles

    trend_block = (
        "\n\n【参考：今日のトレンドトピック（インスピレーション源として活用してください）】\n"
        + "\n".join(f"- {t}" for t in selected_titles)
    )
    print(f"[topics] {len(selected_titles)} 件のトレンドをプロンプトに注入しました")
    if affiliate_keywords:
        print(f"[affiliate] {len(affiliate_keywords)} 件のトレンドキーワードを抽出しました")
    return ng_instruction + trend_block, affiliate_keywords, trend_source_urls, trend_topic_titles


def _build_generation_info_section(
    trend_topic_titles: list[str],
    prompt_type: str,
    kemono_params: dict,
    content: str,
) -> str:
    """
    記事本文末尾に追記する「生成情報」セクションの HTML を組立する。
    使用したトレンド情報（タイトル＋ソース）とキャラクターデータ
    （体型 / 世界設定 / 変身 / 関係性 / 追加設定 + キャラクタータグ）を表示する。
    h2〜h4 を使わない `<details>` 折りたたみ構造のため TOC には載らない。
    表示すべき内容が一切ない場合は空文字列を返す（セクション非表示）。
    """
    char1 = _extract_fm_field(content, "character_1")
    char2 = _extract_fm_field(content, "character_2")

    setting_rows: list[tuple[str, str]] = []
    if prompt_type == "kemono_story" and kemono_params:
        setting_rows.append(("体型", kemono_params.get("char_type", "")))
        setting_rows.append(("世界設定", kemono_params.get("world_setting", "")))
        transform_label = _KEMONO_TRANSFORM_LABEL.get(
            kemono_params.get("transform_key", "none"), "なし"
        )
        setting_rows.append(("変身", transform_label))
        setting_rows.append(("関係性", kemono_params.get("relationship_text", "")))
        if kemono_params.get("extra_key", "none") != "none":
            setting_rows.append(("追加設定", kemono_params.get("extra_tag", "")))

    if not trend_topic_titles and not setting_rows and not char1 and not char2:
        return ""

    parts: list[str] = [
        '<details class="gen-info">',
        '  <summary class="gen-info-summary">🤖 生成情報</summary>',
        '  <div class="gen-info-body">',
        '    <p class="gen-info-note">この記事はAIパイプラインによる自動生成記事です。</p>',
    ]

    if trend_topic_titles:
        items = "\n".join(f"      <li>{html.escape(t)}</li>" for t in trend_topic_titles)
        parts += [
            '    <div class="gen-info-block">',
            '      <p class="gen-info-block-title">使用したトレンド情報</p>',
            f'      <ul class="gen-info-list">\n{items}\n      </ul>',
            '    </div>',
        ]

    data_rows: list[str] = []
    for label, value in setting_rows:
        if value:
            data_rows.append(
                f'      <div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>'
            )
    if char1:
        data_rows.append(f'      <div><dt>キャラクター1</dt><dd>{html.escape(char1)}</dd></div>')
    if char2:
        data_rows.append(f'      <div><dt>キャラクター2</dt><dd>{html.escape(char2)}</dd></div>')
    if data_rows:
        parts += [
            '    <div class="gen-info-block">',
            '      <p class="gen-info-block-title">キャラクターデータ</p>',
            '      <dl class="gen-info-dl">',
            "\n".join(data_rows),
            '      </dl>',
            '    </div>',
        ]

    parts += ['  </div>', '</details>']
    return "\n".join(parts)


def _extract_affiliate_keyword(title: str) -> str | None:
    """
    トレンドタイトルからアフィリエイト検索用のキーワードを1つ抽出する。
    購買意欲のある検索語になるよう、固有名詞・製品名・技術名を優先。
    品質フィルタは inject_affiliate_links 側で実施するため、ここでは粗抽出。
    """
    # e621 などのタイトルは除外
    if title.startswith("e621"):
        return None
    # GitHub リポジトリ形式 "owner/repo: description" → repo名側を抽出
    if ":" in title:
        before_colon = title.split(":", 1)[0].strip()
        after_colon = title.split(":", 1)[1].strip()
        # "owner/repo" 形式の場合、repo名を抽出
        if "/" in before_colon:
            parts = before_colon.split("/")
            repo_name = parts[-1].strip()
            # repo名が意味のある名前（2-20文字）の場合使用
            if 2 <= len(repo_name) <= 20:
                return repo_name
        # 説明側が長すぎる場合は短縮
        if after_colon and len(after_colon) > 0:
            title = after_colon
    # 長すぎる場合は主要語を抽出
    if len(title) > 50:
        words = title.split()
        # 固有名詞候補（大文字始まり）を優先
        capitalized = [w for w in words if w[0].isupper() if len(w) > 1]
        if capitalized:
            title = " ".join(capitalized[:3])
        else:
            title = " ".join(words[:4])
    # 意味のあるキーワードか判定（2文字以上）
    cleaned = re.sub(r'[^\w\s\u3000-\u9fff]', ' ', title).strip()
    if len(cleaned) < 2:
        return None
    return cleaned[:30]


# --------------------------------------------------
# product_recommendations パーサー
# --------------------------------------------------
def extract_product_recommendations(content: str) -> list[dict]:
    """
    Frontmatter から product_recommendations YAML ブロックを抽出・パースする。
    例:
      product_recommendations:
        - name: "商品名"
          category: "書籍"
          price_range: "1000円台"
    """
    block_match = re.search(
        r'^product_recommendations:\s*\n((?:\s*-\s+.*\n?)+)',
        content,
        re.MULTILINE,
    )
    if not block_match:
        return []

    block = block_match.group(1)
    products = []
    current = {}
    for line in block.splitlines():
        item_match = re.match(r'^\s+-\s+name:\s*["\']?(.*?)["\']?\s*$', line)
        if item_match:
            if current:
                products.append(current)
            current = {"name": item_match.group(1).strip()}
            continue
        cat_match = re.match(r'^\s+category:\s*["\']?(.*?)["\']?\s*$', line)
        if cat_match and current:
            current["category"] = cat_match.group(1).strip()
            continue
        price_match = re.match(r'^\s+price_range:\s*["\']?(.*?)["\']?\s*$', line)
        if price_match and current:
            current["price_range"] = price_match.group(1).strip()
            continue

    if current and "name" in current:
        products.append(current)

    return products


# --------------------------------------------------
# 商品カード HTML 生成
# --------------------------------------------------
def generate_product_cards(products: list[dict], title: str) -> str:
    """
    商品リストから商品カード風のHTMLブロックを生成。
    各カードは商品名・カテゴリ・価格帯・Amazon/楽天検索リンクを含む。
    """
    if not products:
        return ""

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")
    utm_content = urllib.parse.quote(title[:50])

    cards_html = ""
    for prod in products:
        name = prod.get("name", "").strip()
        if not name:
            continue

        category = prod.get("category", "商品")
        price = prod.get("price_range", "")
        encoded_kw = urllib.parse.quote(name)

        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        # カテゴリに応じたアイコン
        cat_icons = {
            "書籍": "📚",
            "フィギュア": "🎎",
            "ゲーム": "🎮",
            "ソフトウェア": "💻",
            "ガジェット": "🔧",
            "グッズ": "🎁",
        }
        icon = cat_icons.get(category, "📦")

        price_html = ""
        if price:
            price_html = f'<div class="pc-price">{price}</div>'

        cards_html += f"""
<div class="product-card">
  <div class="pc-icon">{icon}</div>
  <div class="pc-info">
    <div class="pc-name">{name}</div>
    <div class="pc-category">{category}</div>
    {price_html}
  </div>
  <div class="pc-links">
    <a href="{amazon_url}" target="_blank" rel="noopener noreferrer nofollow" class="pc-btn pc-btn-amazon">Amazon</a>
    <a href="{rakuten_url}" target="_blank" rel="noopener noreferrer nofollow" class="pc-btn pc-btn-rakuten">楽天</a>
  </div>
</div>"""

    return f'\n<div class="product-cards">\n{cards_html}\n</div>\n'


def process_product_cards(content: str) -> str:
    """
    Frontmatter の product_recommendations をパースし、記事末尾に
    商品カードHTMLブロックを挿入する（アフィリエイトセクションの手前）。
    """
    products = extract_product_recommendations(content)
    if not products:
        return content

    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "post"

    cards_html = generate_product_cards(products, title)
    if not cards_html:
        return content

    print(f"🛍️ 商品カードを {len(products)} 件生成")

    # product_recommendations ブロックを Frontmatter から完全に削除
    # 改訂: インデントされた継続行をすべてキャッチ（[-:] 制限を撤廃）
    content = re.sub(
        r'^product_recommendations:\s*\n(?:[ \t].*\n?)*',
        '',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # アフィリエイトセクションの手前に挿入
    aff_marker = "### 📚 テーマ関連のおすすめアイテム"
    if aff_marker in content:
        content = content.replace(
            aff_marker,
            cards_html + "\n\n" + aff_marker,
        )
    else:
        # アフィリエイトセクションがない場合は記事末尾に追加
        content = content.strip() + "\n\n" + cards_html

    return content


# --------------------------------------------------
# SEOメタ記述の検証・補正
# --------------------------------------------------
def _extract_first_sentence_from_body(content: str) -> str:
    """本文から最初の文を抽出する"""
    body = _extract_article_body(content).strip()
    if not body:
        return ""
    # Skip heading lines
    for line in body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("!["):
            # Find first sentence ending with 。 or .
            for end_char in ["。", "."]:
                idx = line.find(end_char)
                if idx != -1:
                    return line[:idx + 1]
            return line
    return ""


def _validate_description(desc: str, content: str = "") -> str:
    """記述が80〜120文字の範囲内に収まるように調整する"""
    if not desc:
        return desc
    desc = desc.strip()
    if len(desc) >= MIN_DESC_LEN and len(desc) <= MAX_DESC_LEN:
        return desc
    if len(desc) > MAX_DESC_LEN:
        truncated = desc[:MAX_DESC_LEN - 3].rstrip() + "..."
        return truncated
    # Short description: extend with first sentence from article body
    sentence = _extract_first_sentence_from_body(content)
    if sentence:
        extended = desc + " " + sentence
        while len(extended) < MIN_DESC_LEN:
            next_ext = extended + " " + sentence
            if len(next_ext) > MAX_DESC_LEN:
                break
            extended = next_ext
        return extended[:MAX_DESC_LEN].rstrip() + ("..." if len(extended) > MAX_DESC_LEN else "")
    return desc


def _extract_fm_field(content: str, field: str) -> str:
    """Frontmatterから指定フィールドの値を抽出する"""
    match = re.search(r'^' + field + r':\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    if match and match.group(1):
        return match.group(1).strip()
    return ""


def _extract_fm_tags(content: str) -> list:
    """Frontmatterの tags フィールドからタグリストを抽出する"""
    match = re.search(r'^tags:\s*\[([^\]]*)\]', content, re.MULTILINE)
    if match:
        return [t.strip().strip('"\'') for t in match.group(1).split(",") if t.strip()]
    return []


def _get_body_after_fm(content: str) -> str:
    """Frontmatter (--- ... ---) の後の本文を返す"""
    fm_match = re.search(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
    if fm_match:
        return content[fm_match.end():]
    return content


def _extract_faq_pairs(content: str) -> list[dict]:
    """
    記事本文からFAQパターンを抽出してFAQPage schema用のリストを返す。
    検出パターン:
      1. 「Q: ... A: ...」または「Q:...A:...」のブロック
      2. 疑問符（？/？）で終わる見出し + 続くパラグラフ
    """
    body = _get_body_after_fm(content)
    if not body:
        return []

    pairs = []

    # Pattern 1: Q:/A: blocks (line-by-line parsing)
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r'^[Qq][\u3002.::\uff1a]\s*(.+)$', line)
        if m:
            question_lines = [m.group(1)]
            i += 1
            answer_lines = []
            while i < len(lines):
                next_line = lines[i].strip()
                am = re.match(r'^[Aa][\u3002.::\uff1a]\s*(.*)$', next_line)
                if am:
                    answer_lines.append(am.group(1))
                    i += 1
                    break
                if next_line:
                    question_lines.append(next_line)
                i += 1
            question = "\n".join(question_lines).strip().rstrip("：？")
            answer = "\n".join(answer_lines).strip()
            if question and answer and len(question) >= 5 and len(answer) >= 10:
                pairs.append({"question": question, "answer": answer})
            continue
        i += 1

    # Pattern 2: Heading ending with question mark + following paragraph
    if not pairs:
        sections = re.split(r'\n##\s+', body)
        for section in sections:
            s_lines = section.strip().split("\n")
            if not s_lines:
                continue
            heading = s_lines[0].strip()
            if heading.startswith(("Q:", "Q：", "q:", "q：", "A:", "A：")):
                continue
            if not heading.endswith("？") and not heading.endswith("?"):
                continue
            para = "\n".join(s_lines[1:]).strip()
            if para and len(heading) >= 5 and len(para) >= 10:
                pairs.append({"question": heading.rstrip("？?"), "answer": para})
            if len(pairs) >= 10:
                break

    return pairs[:10]


def _extract_speakable_text(content: str) -> str:
    """
    記事本文の最初の意味のあるパラグラフを抽出してSpeakable schema用テキストを返す。
    見出しや画像キャプションをスキップして本文パラグラフのみを対象とする。
    """
    body = _get_body_after_fm(content)
    if not body:
        return ""

    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("![") or stripped.startswith("<"):
            continue
        if stripped.startswith("["):
            continue
        text = stripped.rstrip("。.").strip()
        if len(text) >= 20:
            return text[:300]

    return ""


def _compose_smart_situation(content: str) -> str:
    """
    image_promptがない記事用に title/description/tags から
    適切な画像シチュエーションを自動生成する。
    """
    title = _extract_fm_field(content, "title")
    desc = _extract_fm_field(content, "description")
    tags = _extract_fm_tags(content)

    # 物語系（kemono_storyなど）はデフォルトのきもーるシチュエーションを使用
    prompt_type = _extract_fm_field(content, "prompt_type")
    if prompt_type in ("kemono_story", "novel", "story"):
        return DEFAULT_SITUATION

    # 技術記事用: タイトルと説明からキーワードを抽出
    keywords = []
    if title:
        keywords.append(title[:50])
    if desc:
        keywords.append(desc[:80])

    # タグから補足キーワード
    tag_keywords = {
        "AI": "artificial intelligence, neural network, glowing brain",
        "Tech": "technology, circuit board, digital",
        "Python": "python, coding, programming",
        "JavaScript": "javascript, web development, browser",
        "Web": "web, internet, globe",
        "ゲーム": "game, controller, pixel art",
        "ゲーム実況": "game, controller, streaming",
        "映画": "movie, cinema, film reel",
        "アニメ": "anime, manga, illustration",
    }
    for tag in tags:
        for tk, kv in tag_keywords.items():
            if tk in tag:
                keywords.append(kv)

    if keywords:
        return ", ".join(keywords[:5])
    return DEFAULT_SITUATION


# --------------------------------------------------
# 重複YAMLキーの修復
# --------------------------------------------------
def _fix_duplicate_yaml_keys(fm_text: str) -> str:
    """
    重複するYAMLキーを検出し、キャラクター定義のようなキーを character_N にリネーム。
    例: 少年: "..." と 少年: "..." → character_1: "..." と character_2: "..."
    """
    lines = fm_text.split("\n")
    seen_keys = {}
    result = []
    char_counter = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("- "):
            result.append(line)
            continue

        match = re.match(r'^([A-Za-z\u3000-\u9fff]+)\s*:\s*', stripped)
        if not match:
            result.append(line)
            continue

        key = match.group(1)

        if key not in seen_keys:
            seen_keys[key] = 1
            if _is_character_like_key(key, stripped):
                char_counter += 1
                new_key = f"character_{char_counter}"
                result.append(re.sub(r'^(\S+?)\s*:', f'{new_key}:', stripped))
                print(f"[WARN] キャラクターキー {key} → {new_key} にリネーム")
            else:
                result.append(line)
        else:
            seen_keys[key] += 1
            if _is_character_like_key(key, stripped):
                char_counter += 1
                new_key = f"character_{char_counter}"
                result.append(re.sub(r'^(\S+?)\s*:', f'{new_key}:', stripped))
                print(f"[WARN] 重複キー {key} → {new_key} にリネーム")
            else:
                result.append(f"# duplicate removed: {stripped}")
                print(f"[WARN] 重複キー {key} を削除")

    return "\n".join(result)


def _is_character_like_key(key: str, line: str) -> bool:
    """
    キーがキャラクター定義（少年, 少女, 男性, 女性, character_Nなど）に
    該当するか判定。値に「1boy」「1girl」「anthro」などのタグが含まれる場合もCharacterとみなす。
    """
    character_types = {"少年", "少女", "男性", "女性", "男", "女", "boy", "girl"}
    if key in character_types:
        return True
    if re.match(r'^character_\d+$', key):
        return False
    value_part = line.split(":", 1)[1].strip().strip("\"'")
    character_tags = {"1boy", "1girl", "2boy", "2girl", "anthro", "wolf", "fox", "cat", "dog", "bear", "leopard", "panther", "dragon", "tiger", "lion", "rabbit", "deer", "otter", "panda", "koala", "fox", "hyena", "jackal", "coyote", "lynx", "bobcat"}
    value_lower = value_part.lower()
    for tag in character_tags:
        if tag in value_lower:
            return True
    return False


# --------------------------------------------------
# Frontmatter YAML 検証・修復
# --------------------------------------------------
def validate_and_fix_frontmatter(content: str) -> str:
    """
    Frontmatter (--- ... ---) の YAML を PyYAML で検証し、
    解析失敗時に破損したブロックを安全に削除して再検証する。
    """
    open_fm = content.find("---")
    if open_fm < 0:
        return content

    close_fm = content.find("\n---", open_fm + 3)
    if close_fm < 0:
        return content

    fm_text = content[open_fm + 3:close_fm]

    # 0. 重複キーチェック（PyYAMLは重複キーでエラーを出さないので常に実行）
    fixed_fm = _fix_duplicate_yaml_keys(fm_text)
    if fixed_fm != fm_text:
        fm_text = fixed_fm
        new_content = content[:open_fm + 3] + fm_text + content[close_fm:]
        return new_content

    try:
        yaml.safe_load(fm_text)
        return content
    except yaml.YAMLError:
        pass

    # 1. product_recommendations ブロックを削除して再検証
    prod_idx = fm_text.find("product_recommendations")
    if prod_idx >= 0:
        before = fm_text[:prod_idx].rstrip("\n")
        cleaned_fm = before + "\n"
        try:
            yaml.safe_load(cleaned_fm)
            new_content = content[:open_fm + 3] + cleaned_fm + content[close_fm:]
            print("[WARN] 破損した product_recommendations を削除して Frontmatter を修復しました")
            return new_content
        except yaml.YAMLError:
            fm_text = cleaned_fm

    # 2. 既知の破損パターンを正規表現で削除
    fm_text = re.sub(r"\n\s{0,8}-\s+name:.*", "", fm_text)
    fm_text = re.sub(r"\n\s{0,8}category:.*", "", fm_text)
    fm_text = re.sub(r"\n\s{0,8}price_range:.*", "", fm_text)
    try:
        yaml.safe_load(fm_text)
        new_content = content[:open_fm + 3] + fm_text + content[close_fm:]
        print("[WARN] 破損した Frontmatter を正規表現で修復しました")
        return new_content
    except yaml.YAMLError:
        pass

    # 3. 最終手段: インデントされた孤線（親キーのないインデント行）をすべて削除
    cleaned_fm = re.sub(r"\n[ \t]{2,}[^ \t].*", "", fm_text)
    try:
        yaml.safe_load(cleaned_fm)
        new_content = content[:open_fm + 3] + cleaned_fm + content[close_fm:]
        print("[WARN] 破損した Frontmatter のインデント孤線を削除して修復しました")
        return new_content
    except yaml.YAMLError:
        pass

    print("[ERROR] Frontmatter YAML の修復に失敗しました")
    return content


# --------------------------------------------------
# slug リダイレクトの追跡
# --------------------------------------------------
SLUG_REDIRECTS_FILE = "data/slug-redirects.json"

def _load_slug_redirects():
    if not os.path.exists(SLUG_REDIRECTS_FILE):
        return {}
    try:
        with open(SLUG_REDIRECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_slug_redirects(redirects):
    os.makedirs(os.path.dirname(SLUG_REDIRECTS_FILE), exist_ok=True)
    with open(SLUG_REDIRECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(redirects, f, ensure_ascii=False, indent=2)

def _get_existing_slugs(posts_dir="src/content/posts"):
    slugs = set()
    if not os.path.exists(posts_dir):
        return slugs
    for filepath in glob.glob(os.path.join(posts_dir, "*.md")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                c = f.read()
        except Exception:
            continue
        slug_m = re.search(r'^slug:\s*["\']?(.*?)["\']?$', c, re.MULTILINE)
        if slug_m and slug_m.group(1).strip():
            slugs.add(slug_m.group(1).strip())
    return slugs

def _resolve_slug_collision(slug, existing_slugs):
    redirects = _load_slug_redirects()
    if slug not in existing_slugs:
        return slug, False
    counter = 2
    unique_slug = f"{slug}-{counter}"
    while unique_slug in existing_slugs:
        counter += 1
        unique_slug = f"{slug}-{counter}"
    redirects[slug] = unique_slug
    _save_slug_redirects(redirects)
    print(f"🔗 slug競合を検出: {slug} → {unique_slug} (リダイレクト記録)")
    return unique_slug, True

# --------------------------------------------------
# 自動内部リンクの挿入
# --------------------------------------------------
def _load_posts_for_links(posts_dir="src/content/posts"):
    result = []
    if not os.path.exists(posts_dir):
        return result
    for filepath in glob.glob(os.path.join(posts_dir, "*.md")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                c = f.read()
        except Exception:
            continue
        title_m = re.search(r'^title:\s*["\']?(.*?)["\']?$', c, re.MULTILINE)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        slug_m = re.search(r'^slug:\s*["\']?(.*?)["\']?$', c, re.MULTILINE)
        slug = slug_m.group(1).strip() if slug_m else ""
        if not slug:
            base = os.path.basename(filepath)
            slug = base.replace("-auto-post.md", "").replace(".md", "").lower()
        tags_m = re.search(r'^tags:\s*\[([^\]]*)\]', c, re.MULTILINE)
        tags = []
        if tags_m:
            tags = [t.strip().strip('"\'') for t in tags_m.group(1).split(",") if t.strip()]
        result.append({"title": title, "slug": slug, "tags": tags})
    return result


def _existing_link_spans(content):
    spans = []
    for m in re.finditer(r'!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)', content):
        spans.append((m.start(), m.end()))
    return spans


def inject_internal_links(content, posts_dir="src/content/posts", max_links=5):
    posts = _load_posts_for_links(posts_dir)
    if not posts:
        return content
    fm_end = content.find("---\n", 4)
    if fm_end == -1:
        body_start = 0
    else:
        body_start = fm_end + 4
    body = content[body_start:]
    link_spans = _existing_link_spans(body)
    replacements = []
    for post in posts:
        title = post["title"]
        slug = post["slug"]
        if len(title) < 3:
            continue
        pattern = re.escape(title)
        for m in re.finditer(pattern, body):
            pos = m.start()
            length = len(title)
            overlap = False
            for s, e in link_spans:
                if pos < e and pos + length > s:
                    overlap = True
                    break
            if overlap:
                continue
            url = f"{BASE_URL}/posts/{slug}"
            link_md = f"[{title}]({url})"
            replacements.append((pos, pos + length, link_md))
            if len(replacements) >= max_links:
                break
        if len(replacements) >= max_links:
            break
    if not replacements:
        return content
    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, replacement in replacements:
        body = body[:start] + replacement + body[end:]
    return content[:body_start] + body


# --------------------------------------------------
# メイン処理
# --------------------------------------------------
def generate_post():

    # 日本時間（JST = UTC+9）の定義
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)

    pub_date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    # 1. プロンプトタイプ決定と同系統の重複防止設定
    prompt_type = os.environ.get("PROMPT_TYPE", "default")
    recent_titles = get_recent_titles_by_type(prompt_type)
    recent_metas = get_recent_meta_by_type(prompt_type)

    if recent_titles:
        past_topics_text = "\n".join([f"- {t}" for t in recent_titles])
        if prompt_type in ("kemono_story", "novel", "story"):
            ng_instruction = (
                f"【直近の執筆作品（テーマ・展開被り防止）】\n"
                f"直近で以下の物語を作成済みです。これらとシチュエーションや展開が極力被らないよう、新しいテーマで作成してください:\n"
                f"{past_topics_text}"
            )
        else:
            ng_instruction = f"【重要：重複の禁止】\n以下のタイトル・テーマは作成済みです:\n{past_topics_text}"
    else:
        ng_instruction = ""

    # 1.2. キャラクター・テーマ被り防止の追加指示
    if recent_metas and prompt_type in ("kemono_story", "novel", "story"):
        char_lines = []
        for meta in recent_metas:
            entries = []
            if "character_1" in meta:
                entries.append(f"キャラ1: {meta['character_1']}")
            if "character_2" in meta:
                entries.append(f"キャラ2: {meta['character_2']}")
            if "art_style" in meta:
                entries.append(f"アートスタイル: {meta['art_style']}")
            if "tags" in meta:
                entries.append(f"タグ: {meta['tags']}")
            if entries:
                entries_joined = "\n  ".join(entries)
                title = meta.get('title', '(不明)')
                char_lines.append(f"「{title}」\n  " + entries_joined)
        if char_lines:
            chars_joined = "\n".join(char_lines)
            ng_instruction += (
                f"\n\n【キャラクター・テーマ被り防止】\n"
                f"以下のキャラクター設定・テーマは直近で使用済みです。"
                f"同じ組み合わせや非常に類似した設定を使わず、新しいキャラクター・テーマで作成してください:\n"
                f"{chars_joined}"
            )

    # 1.5. 世界設定を先に決定（ジャンルベースのトレンド選択に使用）
    kemono_params = _randomize_kemono_params() if prompt_type == "kemono_story" else {}
    target_genres = WORLD_SETTING_GENRE_MAP.get(kemono_params.get("world_setting_key", ""), []) or None

    # 1.6. 収集済みトレンドトピックをプロンプトに注入（ジャンル適合度で優先選択）
    ng_instruction, trend_keywords, trend_source_urls, trend_topic_titles = _append_trending_topics(
        ng_instruction, prompt_type, target_genres=target_genres
    )

    # 2. テキスト記事の生成
    template = load_prompt_template(prompt_type)
    prompt = template.format(
        ng_instruction=ng_instruction,
        pub_date_str=pub_date_str,
        character_features_instruction=_load_character_features(target_genres=target_genres),
        **kemono_params
    )

    # 使用プロンプトの保存（追跡性確保）
    prompt_logs_dir = os.path.join("data", "prompt_logs")
    os.makedirs(prompt_logs_dir, exist_ok=True)
    prompt_path = os.path.join(prompt_logs_dir, f"{file_timestamp}.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"📝 プロンプト保存: {prompt_path}")

    pass1_start = time.time()
    response, pass1_model = generate_content_with_retry(prompt)
    pass1_duration = time.time() - pass1_start
    content = response.text.strip()

    # コードブロック装飾の除外
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    # Frontmatterが存在しない場合はデフォルトを付与（Geminiが---を出力しなかった場合の保険）
    if "---" not in content:
        content = f'---\ntitle: "Auto Post"\npubDate: "{pub_date_str}"\ndescription: ""\ntags: []\n---\n\n' + content
        print("[WARN] Frontmatterが検出されなかったためデフォルトを付与しました")

    # 2.5 2-pass 精製: 下書きを精製して質を高める
    draft_content = content
    pass2_start = time.time()
    content, pass2_model = refine_content(content, prompt_type)
    pass2_duration = time.time() - pass2_start

    # 2-pass 生成のメタデータを保存（効果測定用）
    _save_draft_metadata(
        file_timestamp=file_timestamp,
        prompt_type=prompt_type,
        article_filename=f"{file_timestamp}-auto-post.md",
        draft_content=draft_content,
        refined_content=content,
        pass1_model=pass1_model,
        pass1_duration=pass1_duration,
        pass2_model=pass2_model,
        pass2_duration=pass2_duration,
    )

    # 3. 記事本文からキャラクター設定と画像用シチュエーションプロンプトを抽出して画像生成
    characters = extract_character_prompts(content)
    if characters:
        print(f"👤 検出されたキャラクター設定 ({len(characters)}体):")
        for k, v in characters.items():
            print(f"   - {k}: {v}")
    else:
        print("👤 キャラクター設定は検出されませんでした（単発シチュエーションで生成します）")

    image_filename = f"{file_timestamp}-header.png"
    # 記事レベルのbase seedを生成（同じ記事内の画像でスタイルを一貫させる）
    article_seed = random.randint(0, 2**31 - 1)
    print(f"🎲 記事のbase seed: {article_seed}")
    dynamic_situation = extract_image_prompt(content)
    if dynamic_situation == DEFAULT_SITUATION:
        smart_situation = _compose_smart_situation(content)
        if smart_situation != DEFAULT_SITUATION:
            dynamic_situation = smart_situation
            print(f"💡 image_prompt なし → 自動生成シチュエーション: {dynamic_situation}")
    print(f"💡 抽出されたヘッダー用シチュエーション: {dynamic_situation}")

    article_art_style = extract_art_style(content)
    print(f"🎨 記事のアートスタイル: {article_art_style}")

    full_image_prompt = compose_image_prompt(dynamic_situation, characters, article_art_style)
    print(f"🎨 ヘッダー画像合成プロンプト: {full_image_prompt}")
    image_url = generate_and_save_image(full_image_prompt, image_filename, article_seed)

    # 4. Frontmatterの調整 (image_prompt行を実際の画像URL image: "..." に置換または挿入、prompt_typeの記録)
    if image_url:
        if re.search(r'^image_prompt:.*$', content, re.MULTILINE):
            content = re.sub(
                r'^image_prompt:.*$', 
                f'image: "{image_url}"', 
                content, 
                flags=re.MULTILINE
            )
        elif "---" in content:
            content = content.replace("---", f"---\nimage: \"{image_url}\"", 1)

    # SEOスラッグの検証・生成: slug フィールドがない、または無効な場合はタイトルから生成
    slug_match = re.search(r'^slug:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    if not slug_match or not slug_match.group(1).strip():
        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
        raw_title = title_match.group(1).strip() if title_match else file_timestamp
        # 日本語→ローマ字風スラッグの簡易生成（全角→半角＋アルファベット・数字・ハイフンのみ）
        import unicodedata
        normalized = unicodedata.normalize('NFKC', raw_title)
        slug_chars = []
        for ch in normalized:
            if ch.isascii() and ch.isalnum():
                slug_chars.append(ch.lower())
            elif ch.isascii() and ch in ' -':
                slug_chars.append('-')
            elif '\u3041' <= ch <= '\u3096':  # ひらがな
                code = ord(ch) - ord('\u3041')
                a = code // 26
                i = code % 26
                if a < 10:
                    slug_chars.append(chr(ord('a') + a))
                    if i in (8, 10, 12, 14, 16, 18, 20, 22, 24):
                        slug_chars.append('u')
                elif a == 10:
                    slug_chars.append('n')
                elif a == 11:
                    slug_chars.append('y')
                    slug_chars.append(chr(ord('a') + i))
                else:
                    slug_chars.append(chr(ord('a') + (a - 1)))
            elif '\u30A1' <= ch <= '\u30F6':  # カタカナ
                code = ord(ch) - ord('\u30A1')
                a = code // 26
                i = code % 26
                if a < 10:
                    slug_chars.append(chr(ord('a') + a))
                    if i in (8, 10, 12, 14, 16, 18, 20, 22, 24):
                        slug_chars.append('u')
                elif a == 10:
                    slug_chars.append('n')
                elif a == 11:
                    slug_chars.append('y')
                    slug_chars.append(chr(ord('a') + i))
                else:
                    slug_chars.append(chr(ord('a') + (a - 1)))
            # 漢字・他の文字はスキップ
        slug = re.sub(r'-+', '-', ''.join(slug_chars)).strip('-')[:60]
        if slug and "---" in content:
            content = content.replace("---", f"---\nslug: \"{slug}\"", 1)
            print(f"🔗 スラッグを自動生成: {slug}")

    # slug競合の検出・解決: 既存記事と同じslugがあればユニークに調整してリダイレクトを記録
    if slug_match and slug_match.group(1).strip():
        final_slug = slug_match.group(1).strip()
    else:
        final_slug = slug
    if final_slug:
        existing = _get_existing_slugs()
        final_slug, _ = _resolve_slug_collision(final_slug, existing)
        if final_slug and "---" in content:
            slug_line = rf'^slug:\s*["\']?(.*?)["\']?$'
            content = re.sub(slug_line, f'slug: "{final_slug}"', content, count=1, flags=re.MULTILINE)

    # 系統情報（prompt_type）をFrontmatterに付与（次回以降の同系統判定の精度向上）
    if not re.search(r'^prompt_type:.*$', content, re.MULTILINE) and "---" in content:
        content = content.replace("---", f"---\nprompt_type: \"{prompt_type}\"", 1)

    # ストーリー系: スクリプト決定パラメータ（構造化データ）からtagsを生成してfrontmatterに書き込む
    if prompt_type == "kemono_story" and kemono_params:
        tags_list = _build_kemono_tags(kemono_params)
        # 安全策: タグ内の / はAstro [tag].astro ルート区切りと衝突するため置換
        tags_list = [t.replace("/", "・") for t in tags_list]
        tags_yaml = ", ".join(f'"{t}"' for t in tags_list)
        content = re.sub(r'^tags:.*$', f'tags: [{tags_yaml}]', content, count=1, flags=re.MULTILINE)
        print(f"🏷️  tagsをスクリプト値で設定: {tags_list}")

    # トレンド参照URLをFrontmatterに記録（出典追跡用）
    if trend_source_urls and "---" in content:
        sources_yaml = "\n".join(f"  - {url}" for url in trend_source_urls[:10])
        sources_block = f"trend_sources:\n{sources_yaml}"
        if not re.search(r'^trend_sources:', content, re.MULTILINE):
            content = content.replace("---", f"---\n{sources_block}", 1)

    # 5. 本文内画像の抽出・生成とMarkdown置換
    content = process_inline_images(content, file_timestamp, characters, max_images=MAX_INLINE_IMAGES, art_style=article_art_style, base_seed=article_seed)

    # 5.3 本文内の [character_N] プレースホルダーを置換
    content = replace_character_placeholders(content, characters)

    # 5.4 本文内アフィリエイトプレースホルダーの実リンク置換
    content = process_inline_affiliates(content)

    # 5.45 比較表内商品プレースホルダーの実リンク置換
    content = process_inline_products(content)

    # 5.47 楽天API用Gemini商品名を抽出（process_product_cardsがfrontmatterから除去するため先に取得）
    gemini_product_names = [
        p.get("name", "") for p in extract_product_recommendations(content) if p.get("name")
    ]

    # 5.48 product_recommendations → 商品カードHTMLの生成と挿入
    content = process_product_cards(content)

    # 5.5 アフィリエイト（おすすめ商品・書籍検索リンク）ブロックの自動挿入
    skw = _kemono_affiliate_keywords(kemono_params) if prompt_type == "kemono_story" and kemono_params else None
    content = inject_affiliate_links(content, trend_keywords=trend_keywords, script_keywords=skw, file_timestamp=file_timestamp, gemini_products=gemini_product_names, kemono_params=kemono_params)

    # 5.55 自動内部リンクの挿入
    content = inject_internal_links(content)

    # 5.58 FAQPage schema: 本文からQ&Aパターンを抽出してfrontmatterに記録
    faq_pairs = _extract_faq_pairs(content)
    if faq_pairs and "---" in content:
        faq_json = json.dumps(faq_pairs, ensure_ascii=False)
        safe_faq = faq_json.replace("'", "\\'")
        if not re.search(r'^faq:', content, re.MULTILINE):
            content = content.replace("---", f"---\nfaq: '{faq_json}'", 1)
        print(f"📋 FAQPage schema: {len(faq_pairs)}件のQ&Aペアを抽出")

    # 5.59 Speakable schema: 本文の最初のパラグラフをfrontmatterに記録
    speakable = _extract_speakable_text(content)
    if speakable and "---" in content:
        safe_speakable = speakable.replace("\\", "\\\\").replace('"', '\\"')
        if not re.search(r'^speakable:', content, re.MULTILINE):
            content = content.replace("---", f'---\nspeakable: "{safe_speakable}"', 1)
        print(f"🎤 Speakable schema: 冒頭テキストを抽出 ({len(speakable)}文字)")

    # 5.6 Frontmatter YAML の最終検証・修復
    content = validate_and_fix_frontmatter(content)

    # 5.7 SEOメタ記述の文字数検証・補正
    desc = _extract_fm_field(content, "description")
    if desc:
        corrected = _validate_description(desc, content)
        if corrected != desc:
            safe_corrected = corrected.replace("\\", "\\\\")
            content = re.sub(
                r'^description:\s*["\']?(.*?)["\']?$',
                f'description: "{safe_corrected}"',
                content,
                count=1,
                flags=re.MULTILINE,
            )
            print(f"📝 記述を補正: {len(desc)}→{len(corrected)}文字")

    # 5.8 本文末尾に生成情報セクションを追記（トレンド情報＋キャラクターデータ）
    gen_section = _build_generation_info_section(
        trend_topic_titles, prompt_type, kemono_params, content
    )
    if gen_section:
        content = content.rstrip() + "\n\n" + gen_section + "\n"
        print(f"🤖 生成情報セクションを追記: {len(trend_topic_titles)}件のトレンド情報")

    # 6. 保存
    output_dir = "src/content/posts"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{file_timestamp}-auto-post.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"🎉 記事が正常に生成されました: {filepath}")

    # 7. 古いログのクリーンアップ（期間ベースで N 日前のファイルを削除）
    _cleanup_old_logs()


if __name__ == "__main__":
    generate_post()