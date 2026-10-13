"""article.image — 画像生成・kemono パラメータ・内部画像処理。

generate_article.py の画像関連関数を移設したモジュール。
kemono パラメータ生成（_randomize_kemono_params / _build_kemono_tags）、
HuggingFace / Pollinations による画像生成、画像プロンプト合成、
本文内画像の抽出・置換を担当する。
"""

import os
import random
import re
import time
import urllib.parse

import requests
from PIL import Image
import pillow_avif
from gradio_client import Client

from article.config import *  # noqa: F401,F403



def _is_valid_kemono_combination(transform, relationship, extra):
    """無効な組み合わせをフィルタ。
    自分同士の設定（clone / dark_persona）では、性転換なしの異性愛は成立しない。"""
    if extra in ("clone", "dark_persona") and relationship == "hetero" and "tsf" not in transform:
        return False
    return True


def _weighted_pick(weights: list):
    """重み付きリストから1つの値を抽選する。"""
    return random.choices(
        [v[0] for v in weights],
        weights=[v[1] for v in weights],
        k=1,
    )[0]


def _randomize_kemono_params():
    """kemono_story プロンプト用のランダムパラメータを重み付き選択で生成する。
    バリデーションに失敗した場合は再試行（最大100回）。
    char_count は常に2（clone/dark_persona でも同じ外見の2人が登場するため solo にならない）。"""
    for _ in range(100):
        char_types = _weighted_pick(CHAR_TYPE_WEIGHTS)
        world_setting = _weighted_pick(WORLD_SETTING_WEIGHTS)
        transform = _weighted_pick(TRANSFORM_WEIGHTS)
        relationship = _weighted_pick(RELATIONSHIP_WEIGHTS)
        extra = _weighted_pick(EXTRA_SETTING_WEIGHTS)
        if _is_valid_kemono_combination(transform, relationship, extra):
            break
    else:
        transform = "none"
        extra = "none"

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
        "char_count": 2,
        "char_count_desc": random.choice(_KEMONO_CHAR_COUNT_DESC_2),
        "character2_rule": _KEMONO_CHARACTER2_RULES[extra],
    }


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


def _extract_artist_name(art_style: str) -> tuple[str, str]:
    """art_style から artist 名（"by artist_name"形式）を抽出する。
    (artist_name, style_without_artist) を返す。"""
    artist_match = re.search(r'\s*by\s+([\w-]+)\s*$', art_style)
    if not artist_match:
        return "", art_style
    return "by " + artist_match.group(1), art_style[:artist_match.start()].rstrip(', ')


def _collect_prompt_targets(raw_prompt: str, characters: dict[str, str]) -> tuple[list[str], dict[str, str], str]:
    """[character_1, ...] 括弧区間を解析して (target_chars, per_char_tags, shared_tags) に集約する。
    ターゲット未指定時は character_1（なければ先頭キー）へフォールバック。"""
    bracket_contents = re.findall(r'\[(.*?)\]', raw_prompt)
    target_chars: list[str] = []
    per_char_tags: dict[str, str] = {}
    shared_tags = ""

    for tag_content in bracket_contents:
        parsed_targets, parsed_tags, parsed_shared = _parse_image_prompt_targets(tag_content, characters)
        for key in parsed_targets:
            if key not in target_chars:
                target_chars.append(key)
        for key, tags in parsed_tags.items():
            per_char_tags[key] = f"{per_char_tags[key]}, {tags}".strip(", ") if key in per_char_tags else tags
        if parsed_shared and not shared_tags:
            shared_tags = parsed_shared

    if not target_chars:
        if "character_1" in characters:
            target_chars.append("character_1")
        elif characters:
            target_chars.append(next(iter(characters.keys())))

    return target_chars, per_char_tags, shared_tags


def _compute_count_tag(selected_char_prompts: list[str]) -> str:
    """全体カウントタグ（2boys, 1boy and 1girl, 2characters等）を計算する。"""
    boys_count = sum(1 for p in selected_char_prompts if re.search(r'\b(1boy|boy|male)\b', p, re.IGNORECASE))
    girls_count = sum(1 for p in selected_char_prompts if re.search(r'\b(1girl|girl|female)\b', p, re.IGNORECASE))
    total_count = len(selected_char_prompts)

    if boys_count == total_count:
        return f"{total_count}boys"
    if girls_count == total_count:
        return f"{total_count}girls"
    if boys_count > 0 and girls_count > 0 and (boys_count + girls_count == total_count):
        return f"{boys_count}boy{'s' if boys_count > 1 else ''}, {girls_count}girl{'s' if girls_count > 1 else ''}"
    return f"{total_count}characters"


def _strip_single_count_tags(selected_char_prompts: list[str]) -> list[str]:
    """各キャラ定義先頭から単独カウントタグ（1boy, 1girl等）を除去して整理する。"""
    return [
        re.sub(r'^\s*(?:1boy|1girl|1other|male|female)\s*,\s*', '', p, flags=re.IGNORECASE).strip()
        for p in selected_char_prompts
    ]


def _build_char_block(target_chars: list[str], per_char_tags: dict[str, str], shared_tags: str, cleaned_char_descs: list[str]) -> str:
    """表情/ポーズタグを各キャラの直後に配置（全キャラ同一の場合は1回だけ出力）。
    shared_tags がある場合は末尾に追加する。"""
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
    return char_block


def _finalize_prompt_parts(parts: list[str], clean_situation: str, artist_name: str, style_without_artist: str) -> str:
    """situation/artist/品質タグ/スタイル を順に付加して結合する（Illustrious 公式順序）。"""
    if clean_situation:
        parts.append(clean_situation)
    if artist_name:
        parts.append(artist_name)
    parts.append(BASE_QUALITY_PROMPT)
    if style_without_artist:
        parts.append(style_without_artist)
    return ", ".join(parts)


def compose_image_prompt(raw_prompt: str, characters: dict[str, str], art_style: str = DEFAULT_ART_STYLE) -> str:
    """
    指定された画像プロンプト（シチュエーション文）から登場キャラクター [character_1, ...] を解析し、
    被写体数 + キャラクター外見 + 表情/ポーズ + シチュエーション + artist名 + 品質タグ + アートスタイル を合成する。
    表情/ポーズは各キャラクター外見の直後に配置（全キャラ同一の場合は1回だけ出力）。
    Illustrious系の公式トレーニング順序に準拠（person count → character → situation → artist → quality → style）。
    """
    raw_prompt = raw_prompt.strip().strip('"\'"\"')
    artist_name, style_without_artist = _extract_artist_name(art_style)
    target_chars, per_char_tags, shared_tags = _collect_prompt_targets(raw_prompt, characters)
    clean_situation = re.sub(r'\[[^\]]*\]', '', raw_prompt).strip().strip(', ')

    # 選択されたキャラのプロンプトリスト
    selected_char_prompts = [characters[k] for k in target_chars if k in characters]

    # キャラ定義が無い場合（技術記事など）
    if not selected_char_prompts:
        return _finalize_prompt_parts([], clean_situation, artist_name, style_without_artist)

    # 1人の場合
    if len(selected_char_prompts) == 1:
        char_desc = selected_char_prompts[0]
        parts = [char_desc]
        char_tags = per_char_tags.get(target_chars[0], "") if target_chars else ""
        if not char_tags:
            char_tags = shared_tags
        if char_tags:
            parts.append(char_tags)
        return _finalize_prompt_parts(parts, clean_situation, artist_name, style_without_artist)

    # 2人以上: 全体カウントタグ + キャラブロック
    count_tag = _compute_count_tag(selected_char_prompts)
    cleaned_char_descs = _strip_single_count_tags(selected_char_prompts)
    char_block = _build_char_block(target_chars, per_char_tags, shared_tags, cleaned_char_descs)
    parts = [count_tag, char_block]
    return _finalize_prompt_parts(parts, clean_situation, artist_name, style_without_artist)


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
