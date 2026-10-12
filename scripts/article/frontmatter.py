"""Frontmatter YAML 検証・修復と SEO メタ記述検証ヘルパー。

generate_article.py から分離（Phase 5）。
- SEO メタ記述（description / tags / FAQ / Speakable）の抽出・検証
- 重複 YAML キーの character_N へのリネーム
- PyYAML 検証失敗時の段階的 Frontmatter 修復
"""
import re

import yaml

from article.config import *  # noqa: F401,F403
from article.affiliate import _extract_article_body
from article.meta import _extract_fm_field


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
