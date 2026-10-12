"""Gemini API クライアントと 2-pass 記事生成（下書き精製）。

generate_article.py から分離（Phase 7）。
- Gemini クライアント実体（client）
- プロンプトテンプレート読み込み（load_prompt_template）
- 2-pass 生成: refine_content / generate_content_with_retry
"""

import os
import time

from google import genai
from google.genai import errors

from article.config import *  # noqa: F401,F403

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)


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
