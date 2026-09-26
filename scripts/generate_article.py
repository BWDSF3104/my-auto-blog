import os
import glob
import re
import datetime
import time
from google import genai
from google.genai import errors

# 1. APIキーの設定確認
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

# クライアントの初期化
client = genai.Client(api_key=GEMINI_API_KEY)

# 利用可能な有効モデルの優先リスト
MODELS_TO_TRY = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite"
]

# 過去の生成済み記事タイトルを取得する関数（被り防止用）
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

# プロンプトファイルを外部から読み込む関数
def load_prompt_template(prompt_type="default"):
    prompt_path = os.path.join("scripts", "prompts", f"{prompt_type}.txt")
    
    # 指定のプロンプトがない場合はdefault.txtをフォールバックとして利用
    if not os.path.exists(prompt_path):
        print(f"⚠️ 指定されたプロンプト '{prompt_type}' が見つかりません。'default.txt' を使用します。")
        prompt_path = os.path.join("scripts", "prompts", "default.txt")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# 自動リトライ＆アクティブモデルへのフォールバック関数
def generate_content_with_retry(prompt):
    max_retries = 3

    for model_name in MODELS_TO_TRY:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Gemini API ({model_name}) へ記事生成をリクエスト中... (試行 {attempt}/{max_retries})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response

            except errors.APIError as e:
                err_str = str(e)
                if "404" in err_str or "NOT_FOUND" in err_str:
                    print(f"⚠️ モデル {model_name} は利用不可(404)です。次のモデルへ切り替えます。")
                    break

                print(f"⚠️ APIエラーが発生しました ({model_name}): {e}")
                if attempt < max_retries:
                    wait_time = 5 * (2 ** (attempt - 1))
                    print(f"🕒 {wait_time}秒間待機して再試行します...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ モデル {model_name} でのリトライ上限に達しました。次のモデルを試します。")

            except Exception as e:
                print(f"予期せぬエラー: {e}")
                break

    raise RuntimeError("すべてのモデルおよび再試行が失敗しました。")

def generate_post():
    now = datetime.datetime.now()
    pub_date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    # 重複回避用の過去タイトルリスト取得
    existing_titles = get_existing_titles()
    if existing_titles:
        past_topics_text = "\n".join([f"- {t}" for t in existing_titles[-30:]])
        ng_instruction = f"""
【重要：重複の禁止】
以下のタイトル・テーマはすでに作成済みです。これらと内容や切り口が重複しない、完全に新しいテーマ・トピックを選定してください。
--- すでに存在する記事 ---
{past_topics_text}
---------------------------
"""
    else:
        ng_instruction = ""

    # 環境変数から使用するプロンプト種別を取得（デフォルトは 'default'）
    prompt_type = os.environ.get("PROMPT_TYPE", "default")
    template = load_prompt_template(prompt_type)

    # テンプレート内の変数を置換
    prompt = template.format(
        ng_instruction=ng_instruction,
        pub_date_str=pub_date_str
    )

    response = generate_content_with_retry(prompt)
    content = response.text.strip()

    # コードブロック装飾の除外処理
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    output_dir = "src/content/posts"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{file_timestamp}-auto-post.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"記事が正常に生成されました ({prompt_type}): {filepath}")

if __name__ == "__main__":
    generate_post()