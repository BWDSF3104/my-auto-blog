import os
import glob
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
MAX_INLINE_IMAGES = int(os.environ.get("MAX_INLINE_IMAGES", "2"))
MIN_SCORE_THRESHOLD = int(os.environ.get("MIN_SCORE_THRESHOLD", "0"))

# 画像プロンプトの固定ベース・フォールバック指定 (Nova-Furry-XL向け)
# SFWタグを常に付与して安全な画像生成を強制
# アートスタイルは記事ごとにFrontmatterのart_styleで決定（BASE_QUALITY_PROMPTには含めない）
BASE_QUALITY_PROMPT = "masterpiece, best quality, very aesthetic, ultra-detailed, absurdres, newest, furry, safe for work"
DEFAULT_ART_STYLE = "anime style, illustration, cel shading, vibrant colors"
DEFAULT_SITUATION = "dragon, blueeyes, white scale, sitting at desk with laptop, tech room"

# kemono_story プロンプトのPython側ランダム化設定
# 各項目の重み付き選択でテーマの多様性を確保
CHAR_TYPE_WEIGHTS = [
    ("anthro", 30),
    ("semi-anthro", 20),
    ("feral", 20),
    ("anthro+semi-anthro", 10),
    ("anthro+feral", 10),
    ("semi-anthro+feral", 10),
]

WORLD_SETTING_WEIGHTS = [
    ("fantasy", 35),
    ("sf", 20),
    ("slice_of_life", 25),
    ("fantasy+sf", 20),
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


def _is_valid_kemono_combination(transform, relationship, extra):
    """無効な組み合わせをフィルタ"""
    if extra == "clone" and relationship == "hetero" and "tsf" not in transform:
        return False
    return True


_KEMONO_WORLD_TEXT = {
    "fantasy": "ファンタジー",
    "sf": "SF",
    "slice_of_life": "日常",
    "fantasy+sf": "ファンタジーとSF",
}

_KEMONO_TRANSFORM_TEXT = {
    "none": "",
    "tf": "、TF(変身・変形)",
    "tsf": "、TSF（性転換フィクション）",
    "tf+tsf": "、TF・TSF",
}

_KEMONO_RELATIONSHIP_TEXT = {
    "partnership": "相棒関係",
    "yaoi": "同性愛（男性同士の恋愛）",
    "yuri": "百合（女性同士の恋愛）",
    "hetero": "異性愛",
}

_KEMONO_EXTRA_TEXT = {
    "none": "",
    "clone": "、クローンによる自分同士",
    "rival": "、ライバル関係",
}

_KEMONO_CHAR_COUNT_DESC_1 = ["クローン"]
_KEMONO_CHAR_COUNT_DESC_2 = ["バディ", "ライバル", "カップル"]


def _randomize_kemono_params():
    """kemono_story プロンプト用のランダムパラメータを重み付き選択で生成する。
    バリデーションに失敗した場合は再試行（最大100回）。
    char_count=1 は extra=clone の時のみに制限。"""
    for _ in range(100):
        char_type = random.choices(
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
        "char_type": char_type.replace("+", "・"),
        "world_setting": _KEMONO_WORLD_TEXT[world_setting],
        "transform_text": _KEMONO_TRANSFORM_TEXT[transform],
        "relationship_text": _KEMONO_RELATIONSHIP_TEXT[relationship],
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


def _generate_image_pollinations(prompt: str, output_filename: str) -> str:
    """Pollinations.ai をフォールバック画像生成として使用"""
    save_dir = os.path.join("public", "images")
    os.makedirs(save_dir, exist_ok=True)

    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?model=flux&width=896&height=512&seed={int(time.time())}"

    print(f"🌐 Pollinations.ai 画像生成中: {url[:120]}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    output_filename_tmp = os.path.splitext(output_filename)[0] + ".jpg"
    temp_path = os.path.join(save_dir, output_filename_tmp)
    with open(temp_path, "wb") as f:
        f.write(resp.content)

    return _save_as_avif(temp_path, output_filename)


def generate_and_save_image(prompt: str, output_filename: str) -> str:
    """HF Space APIを呼び出して画像を生成し、public/images/ にAVIF形式で保存してURLパスを返す。
    HF 失敗時は Pollinations.ai にフォールバック。
    IMAGE_PROVIDER=pollinations の場合は HF をスキップして直接 Pollinations を使用。"""
    save_dir = os.path.join("public", "images")
    os.makedirs(save_dir, exist_ok=True)

    gitkeep_path = os.path.join(save_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        open(gitkeep_path, 'w').close()

    # IMAGE_PROVIDER=pollinations の場合は HF をスキップ
    if IMAGE_PROVIDER == "pollinations":
        print("🌐 IMAGE_PROVIDER=pollinations: 直接 Pollinations.ai を使用します。")
        try:
            return _generate_image_pollinations(prompt, output_filename)
        except Exception as e:
            print(f"⚠️ Pollinations.ai 画像生成失敗: {e}")
            print("⚠️ 画像生成を断念し、画像なしで記事のみ出力します。")
            return ""

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🎨 画像生成開始 (試行 {attempt}/{max_retries}): {prompt}")
            hf_client = Client(HF_SPACE_ID, token=HF_TOKEN)

            temp_image_path = hf_client.predict(
                prompt,
                "nsfw, worst quality, bad anatomy, deformed, bad hands, missing fingers, extra digits, fewer digits, cropped, very displeasing, ugly, jpeg artifacts, signature, watermark, username",
                18,
                5.0,
                896,
                512,
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
        return _generate_image_pollinations(prompt, output_filename)
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


def _load_character_features() -> str:
    """e621 から集計したキャラクター特徴を読み込んで、プロンプト用の指示文を生成する。"""
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

    # 各カテゴリから上位10件を抽出
    species = sorted(data.get("species", {}).items(), key=lambda x: -x[1])[:10]
    colors = sorted(data.get("colors", {}).items(), key=lambda x: -x[1])[:10]
    physical = sorted(data.get("physical_features", {}).items(), key=lambda x: -x[1])[:10]
    characters = sorted(data.get("characters", {}).items(), key=lambda x: -x[1])[:10]
    copyrights = sorted(data.get("copyrights", {}).items(), key=lambda x: -x[1])[:10]

    if not species and not colors and not physical and not characters and not copyrights:
        print("  [char-features] データが空です（注入スキップ）")
        return ""

    updated_at = data.get("updated_at", "unknown")
    total_posts = data.get("total_posts_analyzed", 0)
    print(f"  [char-features] 注入: updated_at={updated_at}, posts={total_posts}, species={len(species)}, colors={len(colors)}, physical={len(physical)}, characters={len(characters)}, copyrights={len(copyrights)}")

    # 種族名を日本語風に変換（例: wolf -> wolf/狼, fox -> fox/狐）
    species_names = ", ".join(f"{s[0]}" for s in species)
    color_names = ", ".join(f"{c[0]}" for c in colors)
    physical_names = ", ".join(f"{p[0]}" for p in physical[:8])
    character_names = ", ".join(f"{c[0]}" for c in characters[:8]) if characters else "-"
    copyright_names = ", ".join(f"{c[0]}" for c in copyrights[:8]) if copyrights else "-"

    lines = [
        "",
        "【キャラクター特徴のトレンドデータ（参考）】",
        "以下のトレンドデータは e621 の人気作品から抽出されたキャラクター特徴です。物語のキャラクター設定に参考にしてください。",
        "",
        f"・人気種族: {species_names}",
        f"・人気色: {color_names}",
        f"・身体的特徴: {physical_names}",
        f"・人気キャラクター: {character_names}",
        f"・人気版権: {copyright_names}",
        "",
        "これらの特徴を組み合わせると、コミュニティで人気のあるキャラクターの外見が作れます。ただし、既存のキャラクターをコピーするのではなく、これらの要素を参考に独自のキャラクターを作成してください。",
        "アフィリエイトの製品推薦では、人気版権やキャラクターを活用した公式グッズ、フィギュア、関連商品を優先的に推奨してください。",
    ]

    return "\n".join(lines)


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
def compose_image_prompt(raw_prompt: str, characters: dict[str, str], art_style: str = DEFAULT_ART_STYLE) -> str:
    """
    指定された画像プロンプト（シチュエーション文）から登場キャラクター [character_1, ...] を解析し、
    BASE_QUALITY_PROMPT + アートスタイル + キャラクター外見 + シチュエーション を合成する。
    """
    raw_prompt = raw_prompt.strip().strip('"\'“”')
    
    # 括弧 [character_1, ...] の検出 (複数対応)
    bracket_contents = re.findall(r'\[(.*?)\]', raw_prompt)
    target_chars = []
    clean_situation = re.sub(r'\[[^\]]*\]', '', raw_prompt).strip().strip(', ')

    for tag_content in bracket_contents:
        # タグ内のキャラ指定を分割して解析 (カンマや空白等)
        parts = re.split(r'[,&、\s]+', tag_content)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            num_match = re.search(r'\d+', part)
            if num_match:
                char_key = f"character_{num_match.group(0)}"
                if char_key in characters and char_key not in target_chars:
                    target_chars.append(char_key)
            else:
                for k in characters:
                    if part.lower() in k.lower() and k not in target_chars:
                        target_chars.append(k)

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
        parts = [BASE_QUALITY_PROMPT, art_style]
        if clean_situation:
            parts.append(clean_situation)
        return ", ".join(parts)

    # 1人の場合
    if len(selected_char_prompts) == 1:
        char_desc = selected_char_prompts[0]
        parts = [BASE_QUALITY_PROMPT, art_style, char_desc]
        if clean_situation:
            parts.append(clean_situation)
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

    char_combined = ", ".join(cleaned_char_descs)
    parts = [BASE_QUALITY_PROMPT, art_style, count_tag, char_combined]
    if clean_situation:
        parts.append(clean_situation)

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
def process_inline_images(content: str, file_timestamp: str, characters: dict[str, str], max_images: int = MAX_INLINE_IMAGES, art_style: str = DEFAULT_ART_STYLE) -> str:
    """本文内の <!-- IMAGE_PROMPT: "..." --> を検出し、画像生成してMarkdown画像記法に置換する"""
    matches = list(INLINE_IMAGE_PATTERN.finditer(content))
    if not matches:
        return content

    print(f"📷 本文内画像プロンプトを {len(matches)} 箇所検出 (上限: {max_images} 枚)")

    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        raw_prompt = match.group(1).strip().strip('"\'“”')

        # 上限枚数を超えたタグは削除
        if idx > max_images:
            content = content.replace(full_tag, "", 1)
            continue

        filename = f"{file_timestamp}-inline-{idx}.png"
        full_prompt = compose_image_prompt(raw_prompt, characters, art_style)

        print(f"🎨 本文挿絵 {idx}/{min(len(matches), max_images)} 合成プロンプト: {full_prompt}")
        image_url = generate_and_save_image(full_prompt, filename)

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
    Amazon・楽天の検索リンクに置換する。
    """
    matches = list(INLINE_AFFILIATE_PATTERN.finditer(content))
    if not matches:
        return content

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")

    # 記事タイトルをUTM用に取り出す
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    utm_content = urllib.parse.quote((title_match.group(1).strip() if title_match else "post")[:50])

    print(f"🔗 本文内アフィリエイトプレースホルダーを {len(matches)} 箇所検出")

    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        keyword = match.group(1).strip()
        anchor = match.group(2).strip()
        encoded_kw = urllib.parse.quote(keyword)

        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        # 自然な文章内に埋め込む形式: 主にAmazonリンクをアンカーテキストとして、楽天はフッター注釈
        replacement = (
            f"[{anchor}]({amazon_url})"
            f" （[楽天もチェック]({rakuten_url})）"
        )
        content = content.replace(full_tag, replacement, 1)
        print(f"   🔗 アフィリエイトリンク {idx}: 「{anchor}」→ {keyword}")

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
    """
    matches = list(INLINE_AFF_PRODUCT_PATTERN.finditer(content))
    if not matches:
        return content

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")

    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    utm_content = urllib.parse.quote((title_match.group(1).strip() if title_match else "post")[:50])

    print(f"🛒 比較表内商品プレースホルダーを {len(matches)} 箇所検出")

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
    "kemono": "ケモノ 図鑑",
    "pokemon": "ポケモン 公式",
    "novel": "ライトノベル おすすめ",
    "fantasy": "ファンタジー 小説",
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
        # 物語系: 関連作品・グッズ
        return f"{kw} 関連作品"

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


def _extract_article_keywords(content: str, max_kw: int = 2) -> list[str]:
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


def inject_affiliate_links(content: str, trend_keywords: list[str] = None) -> str:
    """
    記事末尾にAmazon・楽天のアフィリエイト検索リンクブロックを自動挿入する。

    キーワード優先順位:
    1. 記事本文から抽出したテーマキーワード（tags + 本文先頭）
    2. trend_keywords（GitHubリポジトリ名は除外）
    3. tags / title のフォールバック

    改善点:
    - キーワード品質のフィルタリングと改善
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

    # 1. 記事本文からテーマキーワードを抽出（最優先）
    article_kw = _extract_article_keywords(content, max_kw=2)
    for kw in article_kw:
        if _is_affiliate_bad_keyword(kw):
            continue
        improved = _improve_keyword(kw, prompt_type)
        keywords_to_use.append(improved)

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
        else:
            # 最終フォールバック
            if prompt_type in ("kemono_story", "novel", "story"):
                keywords_to_use = ["ライトノベル おすすめ"]
            else:
                keywords_to_use = ["プログラミング 入門書"]

    # UTM トラッキングパラメータ
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    utm_content = urllib.parse.quote((title_match.group(1).strip() if title_match else "post")[:50])

    links_html = ""
    for kw in keywords_to_use:
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
この記事のテーマに関連する作品や人気アイテムをチェック！{sections}{links_html}

<small style="color: #64748b;">※ 当サイトはアフィリエイト広告（Amazonアソシエイト・楽天アフィリエイト等）を利用して収益を得ています。</small>
"""
    return content.strip() + "\n" + affiliate_section



# --------------------------------------------------
# 2-pass 生成: 下書きの精製
# プロンプトは scripts/prompts/refine_tech.txt, refine_story.txt に分離


def refine_content(draft: str, prompt_type: str) -> str:
    """
    下書き記事を2回目のGemini API呼び出しで精製する。
    技術記事と物語で異なる精製プロンプトを使用する。
    """
    if prompt_type in ("kemono_story", "novel", "story"):
        refine_template = load_prompt_template("refine_story")
    else:
        refine_template = load_prompt_template("refine_tech")
    refine_prompt = refine_template + f"\n\n【下書き】\n{draft}"

    try:
        print("✨ 2-pass 精製中...")
        response = generate_content_with_retry(refine_prompt)
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
        return refined.strip()
    except Exception as e:
        print(f"⚠️ 精製パスでエラーが発生しました: {e}")
        print("⚠️ 下書きのまま続行します")
        return draft


# --------------------------------------------------
# Gemini API 呼び出し
# --------------------------------------------------
def generate_content_with_retry(prompt):
    max_retries = 3
    for model_name in MODELS_TO_TRY:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Gemini API ({model_name}) リクエスト中... (試行 {attempt}/{max_retries})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response
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
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
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
    指定カテゴリのトピックを持たない source は有効期限切れとみなす。
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
            [sys.executable, "-u", os.path.join(PROJECT_DIR, "fetch_topics.py"), "--prompt-type", prompt_type],
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
TREND_USAGE_DIR = "data/trend_usage"

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


def _append_trending_topics(ng_instruction: str, prompt_type: str) -> tuple[str, list[str], list[str]]:
    """
    data/topics/latest.json が存在する場合、prompt_type に応じたカテゴリの
    トレンドタイトルを score 降順で選択して ng_instruction の末尾へ付加する。
    Per-source TTL で期限切れのカテゴリがある場合は自動再取得を試みる。
    第2要素としてアフィリエイト用のトレンドキーワードリストを返す。
    第3要素として frontmatter 用のソースURLリストを返す。
    ファイルが存在しない場合は元の ng_instruction と空リストを返す。
    """
    if not os.path.exists(TOPICS_JSON_PATH):
        print(f"[topics] {TOPICS_JSON_PATH} が見つかりません。トレンド注入をスキップします。")
        return ng_instruction, [], []

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[topics] JSON 読み込み失敗: {e}")
        return ng_instruction, [], []

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

    # 無作為に2件選択
    TREND_SELECT_COUNT = 2
    if len(candidates) > TREND_SELECT_COUNT:
        candidates = random.sample(candidates, TREND_SELECT_COUNT)

    for item in candidates:
        title = item.get("title", "").strip()
        source = item.get("source", "")
        url = item.get("url", "")
        if title:
            selected_titles.append(f"[{source}] {title}")
            if url:
                trend_source_urls.append(url)
            selected_items.append({
                "title": title,
                "source": source,
                "url": url,
                "score": item.get("score", 0),
                "category": item.get("category", ""),
                "rating": item.get("rating", ""),
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
        return ng_instruction, affiliate_keywords, trend_source_urls

    trend_block = (
        "\n\n【参考：今日のトレンドトピック（インスピレーション源として活用してください）】\n"
        + "\n".join(f"- {t}" for t in selected_titles)
    )
    print(f"[topics] {len(selected_titles)} 件のトレンドをプロンプトに注入しました")
    if affiliate_keywords:
        print(f"[affiliate] {len(affiliate_keywords)} 件のトレンドキーワードを抽出しました")
    return ng_instruction + trend_block, affiliate_keywords, trend_source_urls


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

    # 1.5. 収集済みトレンドトピックをプロンプトに注入（fetch_topics.py が生成した JSON を参照）
    ng_instruction, trend_keywords, trend_source_urls = _append_trending_topics(ng_instruction, prompt_type)

    # 2. テキスト記事の生成
    template = load_prompt_template(prompt_type)
    kemono_params = _randomize_kemono_params() if prompt_type == "kemono_story" else {}
    prompt = template.format(
        ng_instruction=ng_instruction,
        pub_date_str=pub_date_str,
        character_features_instruction=_load_character_features(),
        **kemono_params
    )


    response = generate_content_with_retry(prompt)
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
    content = refine_content(content, prompt_type)

    # 3. 記事本文からキャラクター設定と画像用シチュエーションプロンプトを抽出して画像生成
    characters = extract_character_prompts(content)
    if characters:
        print(f"👤 検出されたキャラクター設定 ({len(characters)}体):")
        for k, v in characters.items():
            print(f"   - {k}: {v}")
    else:
        print("👤 キャラクター設定は検出されませんでした（単発シチュエーションで生成します）")

    image_filename = f"{file_timestamp}-header.png"
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
    image_url = generate_and_save_image(full_image_prompt, image_filename)

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

    # トレンド参照URLをFrontmatterに記録（出典追跡用）
    if trend_source_urls and "---" in content:
        sources_yaml = "\n".join(f"  - {url}" for url in trend_source_urls[:10])
        sources_block = f"trend_sources:\n{sources_yaml}"
        if not re.search(r'^trend_sources:', content, re.MULTILINE):
            content = content.replace("---", f"---\n{sources_block}", 1)

    # 5. 本文内画像の抽出・生成とMarkdown置換
    content = process_inline_images(content, file_timestamp, characters, max_images=MAX_INLINE_IMAGES, art_style=article_art_style)

    # 5.3 本文内の [character_N] プレースホルダーを置換
    content = replace_character_placeholders(content, characters)

    # 5.4 本文内アフィリエイトプレースホルダーの実リンク置換
    content = process_inline_affiliates(content)

    # 5.45 比較表内商品プレースホルダーの実リンク置換
    content = process_inline_products(content)

    # 5.48 product_recommendations → 商品カードHTMLの生成と挿入
    content = process_product_cards(content)

    # 5.5 アフィリエイト（おすすめ商品・書籍検索リンク）ブロックの自動挿入
    content = inject_affiliate_links(content, trend_keywords=trend_keywords)

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

    # 6. 保存
    output_dir = "src/content/posts"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{file_timestamp}-auto-post.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"🎉 記事が正常に生成されました: {filepath}")

if __name__ == "__main__":
    generate_post()