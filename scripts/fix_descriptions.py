"""既存記事のdescriptionが80文字未満のものを本文から補正する。

独立スクリプトとして単体実行前提。生成パイプラインには組み込まない。
"""

import os
import re
import sys

POSTS_DIR = "src/content/posts"
MIN_DESC_LEN = 80
MAX_DESC_LEN = 120


def _extract_fm_field(content: str, field: str) -> str:
    """Frontmatterから指定フィールドの値を抽出する"""
    match = re.search(
        r"^" + field + r":\s*[\"']?(.*?)[\"']?\s*$",
        content,
        re.MULTILINE,
    )
    if match and match.group(1):
        return match.group(1).strip()
    return ""


def _extract_body(content: str) -> str:
    """Frontmatterの外側（本文）を抽出する"""
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return ""


def _extract_first_sentences(body: str, min_length: int) -> str:
    """本文から先頭の文を抽出してmin_length文字以上になるまで連結する"""
    text = body.strip()
    # 見出し、画像、引用符を除外
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("![") or line.startswith(">"):
            continue
        lines.append(line)

    if not lines:
        return ""

    # 各ラインから文（。や.で区切られた単位）を抽出
    sentences = []
    for line in lines:
        # 日本語の句点または英語のピリオドで分割
        for end_char in ["。", "."]:
            idx = line.find(end_char)
            if idx != -1:
                sentences.append(line[: idx + 1])
                line = line[idx + 1:].strip()
        if line.strip():
            sentences.append(line.strip())

    result = ""
    for s in sentences:
        if not result:
            result = s
        else:
            result = result + " " + s
        if len(result) >= min_length:
            break

    return result


def fix_description(content: str) -> tuple:
    """descriptionが80文字未満の場合、本文から補正する。
    Returns (new_content, was_fixed, old_desc, new_desc)
    """
    desc = _extract_fm_field(content, "description")
    if not desc or len(desc) >= MIN_DESC_LEN:
        return content, False, desc, desc

    body = _extract_body(content)
    extension = _extract_first_sentences(body, MIN_DESC_LEN)

    if not extension:
        return content, False, desc, desc

    # description + 本文の文 を連結
    extended = desc + " " + extension

    # MAX_DESC_LEN 超過なら切り詰め
    if len(extended) > MAX_DESC_LEN:
        extended = extended[: MAX_DESC_LEN - 3].rstrip() + "..."

    # description行を置換
    safe_desc = extended.replace("\\", "\\\\").replace('"', '\\"')
    new_content = re.sub(
        r'^description:\s*["\']?(.*?)(?<!\\)["\']?\s*$',
        f'description: "{safe_desc}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    return new_content, True, desc, extended


def main():
    if not os.path.isdir(POSTS_DIR):
        print(f"[ERROR] {POSTS_DIR} が見つかりません")
        sys.exit(1)

    fixed = 0
    skipped = 0
    errors = 0

    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".md"):
            continue

        fpath = os.path.join(POSTS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content, was_fixed, old_desc, new_desc = fix_description(content)

            if was_fixed:
                print(f"[FIX] {fname}: {len(old_desc)} -> {len(new_desc)} chars")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                fixed += 1
            else:
                desc = _extract_fm_field(content, "description")
                if desc:
                    skipped += 1
                else:
                    print(f"[WARN] {fname}: descriptionフィールドなし")
                    skipped += 1

        except Exception as e:
            print(f"[ERROR] {fname}: {e}")
            errors += 1

    print(f"\n完了: {fixed}件修正, {skipped}件スキップ, {errors}件エラー")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
