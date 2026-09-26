import os
import datetime
import google.generativeai as genai

# 1. APIキーの設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

def generate_post():
    # 2. モデルの指定（高速かつ無料枠が十分な gemini-1.5-flash）
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    time_str = today.strftime("%Y-%m-%d %H:%M:%S")

    # 3. AIに渡す指示文（プロンプト）
    prompt = f"""
    あなたはWEBエンジニア兼技術ブロガーです。
    最新のWeb技術、AI、またはプログラミングに関する役立つ解説記事を1つ作成してください。

    【出力フォーマット指定】
    必ず以下のYAML Frontmatterヘッダー形式から始めてください。
    余計な挨拶文や ```markdown などのコードブロック囲みは含めないでください。

    ---
    title: "記事のタイトルをここに"
    pubDate: "{today_str}"
    description: "記事の短い要約（80〜120文字程度）"
    author: "AI Writer"
    tags: ["Tech", "AI"]
    ---

    # 記事のタイトル

    ## はじめに
    （導入文を詳しく記述）

    ## 主要なポイント・解説
    （具体的なコード例やメリットなどを解説）

    ## まとめ
    （全体のまとめ）
    """

    print("Gemini APIへ記事生成をリクエスト中...")
    response = model.generate_content(prompt)
    content = response.text.strip()

    # コードブロック（```）で囲まれて返ってきた場合の整形処理
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    # 4. AstroのコンテンツディレクトリにMarkdownとして保存
    output_dir = "src/pages/posts" # Astroの標準的なルーティング先
    os.makedirs(output_dir, exist_ok=True)
    
    # ユニークなファイル名を設定（例: 2026-09-27-post.md）
    filename = f"{today_str}-auto-post.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"記事が正常に生成されました: {filepath}")

if __name__ == "__main__":
    generate_post()