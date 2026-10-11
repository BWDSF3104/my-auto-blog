import glob
import json
import os
import re
from datetime import datetime, timedelta, timezone

from article.config import (
    AFFILIATE_LINKS_DIR,
    DRAFTS_DIR,
    LOG_CLEANUP_DAYS,
    LOG_CLEANUP_DIRS,
    TREND_USAGE_DIR,
    _LOG_TS_RE,
)


def _extract_fm_field(content: str, field: str) -> str:
    """Frontmatterから指定フィールドの値を抽出する"""
    match = re.search(r'^' + field + r':\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    if match and match.group(1):
        return match.group(1).strip()
    return ""


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


def _save_draft_metadata(
    file_timestamp: str,
    prompt_type: str,
    article_filename: str,
    draft_content: str,
    refined_content: str,
    pass1_model: str,
    pass1_duration: float,
    pass2_model: str,
    pass2_duration: float,
):
    """
    2-pass生成のメタデータを JSON として保存する。
    1回目（下書き）と2回目（精製）の内容・モデル・時間を記録。
    """
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    filepath = os.path.join(DRAFTS_DIR, f"{file_timestamp}.json")

    draft_char_count = len(draft_content)
    draft_line_count = draft_content.count("\n") + 1
    refined_char_count = len(refined_content)
    refined_line_count = refined_content.count("\n") + 1

    metadata = {
        "timestamp": file_timestamp,
        "prompt_type": prompt_type,
        "article_file": article_filename,
        "pass1": {
            "model": pass1_model,
            "duration_seconds": round(pass1_duration, 2),
            "content_char_count": draft_char_count,
            "content_line_count": draft_line_count,
            "content": draft_content,
        },
        "pass2": {
            "model": pass2_model,
            "duration_seconds": round(pass2_duration, 2),
            "content_char_count": refined_char_count,
            "content_line_count": refined_line_count,
            "content": refined_content,
        },
        "diff_stats": {
            "char_count_change": refined_char_count - draft_char_count,
            "line_count_change": refined_line_count - draft_line_count,
            "char_count_change_percent": round(
                (refined_char_count - draft_char_count) / draft_char_count * 100, 2
            ) if draft_char_count else 0,
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"[draft_meta] 2-passメタデータを保存: {filepath}")


def _save_affiliate_link_log(
    file_timestamp: str,
    prompt_type: str,
    article_title: str,
    keywords: list[dict],
):
    """
    アフィリエイト末尾セクションのキーワード・URL生成ログをJSON保存する。
    keywords: [{"keyword": str, "source": str, "amazon_url": str, "rakuten_url": str}, ...]
    """
    os.makedirs(AFFILIATE_LINKS_DIR, exist_ok=True)
    filepath = os.path.join(AFFILIATE_LINKS_DIR, f"{file_timestamp}.json")
    log_data = {
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "file_timestamp": file_timestamp,
        "prompt_type": prompt_type,
        "article_title": article_title,
        "keywords": keywords,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"[affiliate_log] リンク生成ログを保存: {filepath}")


def _cleanup_old_logs(days: int = LOG_CLEANUP_DAYS) -> int:
    """
    ログ・メタデータディレクトリから `days` より古いファイルを削除する。
    ファイル名内のタイムスタンプ（%Y-%m-%d-%H%M%S）を基準とする。
    これらはパイプラインから読み戻されない監査ログのため削除して安全。
    タイムスタンプ形式に合わないファイルは削除対象外（安全側）。
    削除したファイル数を返す。
    """
    cutoff = datetime.now(timezone(timedelta(hours=9))) - timedelta(days=days)
    removed = 0
    for dir_path in LOG_CLEANUP_DIRS:
        if not os.path.isdir(dir_path):
            continue
        for name in os.listdir(dir_path):
            if name == ".gitkeep":
                continue
            full = os.path.join(dir_path, name)
            if not os.path.isfile(full):
                continue
            m = _LOG_TS_RE.match(name)
            if not m:
                continue
            try:
                file_time = datetime.strptime(m.group(1), "%Y-%m-%d-%H%M%S").replace(
                    tzinfo=timezone(timedelta(hours=9))
                )
            except ValueError:
                continue
            if file_time < cutoff:
                try:
                    os.remove(full)
                    removed += 1
                except OSError as e:
                    print(f"[cleanup] 削除に失敗: {full}: {e}")
    if removed:
        print(f"[cleanup] 古いログファイル {removed} 件を削除（{days}日前）")
    return removed
