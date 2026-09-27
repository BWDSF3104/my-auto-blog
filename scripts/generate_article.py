import os
import glob
import re
import datetime
import time
from PIL import Image
import pillow_avif
from google import genai
from google.genai import errors
from gradio_client import Client

# --------------------------------------------------
# 設定
# --------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

HF_TOKEN = os.environ.get("HF_TOKEN")

client = genai.Client(api_key=GEMINI_API_KEY)

MODELS_TO_TRY = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite"
]

HF_SPACE_ID = "blume/kemono-image-api"
BASE_URL = "/my-auto-blog"  # GitHub Pagesのベースパス
MAX_INLINE_IMAGES = int(os.environ.get("MAX_INLINE_IMAGES", "2"))

# 画像プロンプトの固定ベース・フォールバック指定 (Nova-Furry-XL向け)
BASE_QUALITY_PROMPT = "masterpiece, best quality, amazing quality, ultra-detailed, furry, anthro"
DEFAULT_SITUATION = "dragon, blueeyes, white scale, sitting at desk with laptop, tech room"

# 本文内画像プレースホルダーの正規表現 (例: <!-- IMAGE_PROMPT: "..." -->)
INLINE_IMAGE_PATTERN = re.compile(
    r'<!--\s*IMAGE_PROMPT:\s*(.*?)\s*-->',
    re.IGNORECASE
)


# --------------------------------------------------
# 画像生成関数
# --------------------------------------------------
def generate_and_save_image(prompt: str, output_filename: str) -> str:
    """HF Space APIを呼び出して画像を生成し、public/images/ にAVIF形式で保存してURLパスを返す"""
    save_dir = os.path.join("public", "images")
    os.makedirs(save_dir, exist_ok=True)
    
    gitkeep_path = os.path.join(save_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        open(gitkeep_path, 'w').close()

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🎨 画像生成開始 (試行 {attempt}/{max_retries}): {prompt}")
            hf_client = Client(HF_SPACE_ID, token=HF_TOKEN)
            
            temp_image_path = hf_client.predict(
                prompt,
                "worst quality, low quality, bad quality, bad anatomy, bad hands, missing fingers, extra digits, cropped, deformed",
                18,
                5.0,
                896,
                512,
                api_name="/predict"
            )
            
            # 拡張子を .avif に変更して保存パスを作成
            output_filename_avif = os.path.splitext(output_filename)[0] + ".avif"
            target_path = os.path.join(save_dir, output_filename_avif)
            
            # --- AVIF変換・保存処理 (リサイズなし) ---
            with Image.open(temp_image_path) as img:
                # 透過チャンネル（RGBA/P）がある場合はRGBに変換
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # quality=80 は画質をほぼ劣化させずに容量を軽量化できる推奨設定
                img.save(target_path, "AVIF", quality=80)
            
            print(f"🖼️ AVIF画像保存成功: {target_path}")
            
            return f"{BASE_URL}/images/{output_filename_avif}"

        except Exception as e:
            print(f"⚠️ 画像生成試行 {attempt} 失敗: {e}")
            if attempt < max_retries:
                time.sleep(15)

    print("⚠️ 画像生成を断念し、画像なしで記事のみ出力します。")
    return ""


# --------------------------------------------------
# 過去タイトル取得
# --------------------------------------------------
def get_existing_titles(posts_dir="src/content/posts"):
    titles = []
    if not os.path.exists(posts_dir):
        return titles
    
    md_files = glob.glob(os.path.join(posts_dir, "*.md"))
    for filepath in md_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
            if match:
                titles.append(match.group(1))
    return titles


# --------------------------------------------------
# プロンプト読み込み
# --------------------------------------------------
def load_prompt_template(prompt_type="default"):
    prompt_path = os.path.join("scripts", "prompts", f"{prompt_type}.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("scripts", "prompts", "default.txt")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


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
# プロンプト合成関数（複数キャラ対応）
# --------------------------------------------------
def compose_image_prompt(raw_prompt: str, characters: dict[str, str]) -> str:
    """
    指定された画像プロンプト（シチュエーション文）から登場キャラクター [character_1, ...] を解析し、
    BASE_QUALITY_PROMPT + キャラクター外見 + シチュエーション を合成する。
    """
    raw_prompt = raw_prompt.strip().strip('"\'“”')
    
    # 括弧 [character_1, ...] の検出
    bracket_match = re.search(r'\[(.*?)\]', raw_prompt)
    target_chars = []
    clean_situation = raw_prompt

    if bracket_match:
        tag_content = bracket_match.group(1)
        # 括弧部分をシチュエーションから除去
        clean_situation = raw_prompt.replace(bracket_match.group(0), "").strip().strip(', ')
        
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
        parts = [BASE_QUALITY_PROMPT]
        if clean_situation:
            parts.append(clean_situation)
        return ", ".join(parts)

    # 1人の場合
    if len(selected_char_prompts) == 1:
        char_desc = selected_char_prompts[0]
        parts = [BASE_QUALITY_PROMPT, char_desc]
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
    parts = [BASE_QUALITY_PROMPT, count_tag, char_combined]
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
def process_inline_images(content: str, file_timestamp: str, characters: dict[str, str], max_images: int = MAX_INLINE_IMAGES) -> str:
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
        full_prompt = compose_image_prompt(raw_prompt, characters)

        print(f"🎨 本文挿絵 {idx}/{min(len(matches), max_images)} 合成プロンプト: {full_prompt}")
        image_url = generate_and_save_image(full_prompt, filename)

        if image_url:
            # 成功時: 前後に空行を入れてMarkdown画像タグに置換
            alt_text = re.sub(r'\[.*?\]', '', raw_prompt).strip().strip(', ') or "Illustration"
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
                break
    raise RuntimeError("すべてのモデルおよび再試行が失敗しました。")


# --------------------------------------------------
# メイン処理
# --------------------------------------------------
def generate_post():
    now = datetime.datetime.now()
    pub_date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    # 1. 重複防止設定
    existing_titles = get_existing_titles()
    if existing_titles:
        past_topics_text = "\n".join([f"- {t}" for t in existing_titles[-30:]])
        ng_instruction = f"【重要：重複の禁止】\n以下のタイトル・テーマは作成済みです:\n{past_topics_text}"
    else:
        ng_instruction = ""

    # 2. テキスト記事の生成
    prompt_type = os.environ.get("PROMPT_TYPE", "default")
    template = load_prompt_template(prompt_type)
    prompt = template.format(
        ng_instruction=ng_instruction,
        pub_date_str=pub_date_str
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
    print(f"💡 抽出されたヘッダー用シチュエーション: {dynamic_situation}")

    full_image_prompt = compose_image_prompt(dynamic_situation, characters)
    print(f"🎨 ヘッダー画像合成プロンプト: {full_image_prompt}")
    image_url = generate_and_save_image(full_image_prompt, image_filename)

    # 4. Frontmatterの調整 (image_prompt行を実際の画像URL image: "..." に置換または挿入)
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

    # 5. 本文内画像の抽出・生成とMarkdown置換
    content = process_inline_images(content, file_timestamp, characters, max_images=MAX_INLINE_IMAGES)

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