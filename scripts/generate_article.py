import os
import glob
import re
import datetime
from google import genai  # 最新の標準SDK

# 1. APIキーの設定確認
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

# クライアントの初期化
client = genai.Client(api_key=GEMINI_API_KEY)

# 過去の生成済み記事タイトルを取得する関数（被り防止用）
def get_existing_titles(posts_dir="src/pages/posts"):
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

def generate_post():
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d")

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

    prompt = f"""
あなたはWeb技術・AI分野に精通したプロのライターです。
最新のWeb開発、プログラミング、またはAI技術に関する実用的な解説記事を1つ作成してください。

{ng_instruction}

【出力フォーマット指定】
必ず以下のYAML Frontmatterヘッダー形式から始めてください。
余計な挨拶文や ```markdown などのコードブロック囲みは含めないでください。

---
title: "記事のタイトル"
pubDate: "{today_str}"
description: "記事の短い要約（80〜120文字程度）"
author: "AI Writer"
tags: ["Tech", "AI"]
---

# 記事のタイトル

## はじめに
（導入文）

## 詳細解説
（具体例やコード例、メリットなどを分かりやすく解説）

## まとめ
（全体のまとめ）
"""

    print("Gemini API (gemini-3.6-flash) へ記事生成をリクエスト中...")
    
    # 最新モデル gemini-3.6-flash を指定
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
    )
    content = response.text.strip()

    # 余分なコードブロック装飾の除外処理
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    output_dir = "src/pages/posts"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{today_str}-auto-post.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"記事が正常に生成されました: {filepath}")

if __name__ == "__main__":
    generate_post()