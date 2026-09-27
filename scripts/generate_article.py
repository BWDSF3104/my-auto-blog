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
def process_inline_images(content: str, file_timestamp: str, max_images: int = MAX_INLINE_IMAGES) -> str:
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
        full_prompt = f"{BASE_QUALITY_PROMPT}, {raw_prompt}"

        print(f"🎨 本文挿絵 {idx}/{min(len(matches), max_images)} 生成開始: {raw_prompt}")
        image_url = generate_and_save_image(full_prompt, filename)

        if image_url:
            # 成功時: 前後に空行を入れてMarkdown画像タグに置換
            replacement = f"\n\n![{raw_prompt}]({image_url})\n\n"
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

    # 3. 記事本文から画像用シチュエーションプロンプトを抽出して画像生成
    image_filename = f"{file_timestamp}-header.png"
    dynamic_situation = extract_image_prompt(content)
    print(f"💡 抽出されたシチュエーション: {dynamic_situation}")

    full_image_prompt = f"{BASE_QUALITY_PROMPT}, {dynamic_situation}"
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
    content = process_inline_images(content, file_timestamp, max_images=MAX_INLINE_IMAGES)

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