"""トレンドトピックの TTL 検証・自動再取得・ジャンル事前スコアリング・プロンプト注入ヘルパー。

generate_article.py から分離（Phase 5）。
- トレンド JSON のグローバル / per-source TTL 検証
- 期限切れ時の fetch_topics.py 自動再取得
- ジャンル事前スコアリング（_load_genre_scores / _filter_by_genre）
- プロンプトへのトレンドブロック付加と利用ログ保存
"""
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from article.config import *  # noqa: F401,F403
from article.affiliate import _extract_affiliate_keyword
from article.meta import _save_trend_usage_log


def _load_genre_scores() -> dict:
    """data/genre_scores/topics.json を読み込む。存在しない・破損時は空 dict。"""
    if not os.path.exists(GENRE_SCORES_PATH):
        return {}
    try:
        with open(GENRE_SCORES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _filter_by_genre(items: list[dict], target_genres: list[str], scores_data: dict) -> list[dict]:
    """事前スコアリング結果でジャンル適合度の高い順にソートする。
    スコア未登録の項目は末尾に保持（除外しない）。"""
    topic_scores = {t["key"]: t.get("scores") for t in scores_data.get("topics", []) if t.get("scores")}
    def _genre_score(item: dict) -> float:
        url = item.get("url", item.get("title", ""))
        scores = topic_scores.get(url)
        if not scores:
            return -1
        return max(scores.get(g, 0) for g in target_genres)
    scored = [(it, _genre_score(it)) for it in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [it for it, _ in scored]

# --------------------------------------------------
# トレンドトピック注入ヘルパー
# --------------------------------------------------

def _check_topics_ttl(data: dict) -> bool:
    """
    TTL検証: fetched_at から経過時間が ttl_hours を超えているかチェック。
    超過時はTrueを返し、警告を出力する。
    """
    fetched_at_str = data.get("fetched_at", "")
    if not fetched_at_str:
        print("[topics] fetched_at が存在しません。TTL検証をスキップします。")
        return False

    try:
        fetched_at = datetime.fromisoformat(fetched_at_str)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone(timedelta(hours=9)))
        now = datetime.now(timezone(timedelta(hours=9)))
        ttl_hours = data.get("ttl_hours", 24)
        elapsed = (now - fetched_at).total_seconds() / 3600
        if elapsed > ttl_hours:
            print(f"[topics] 注意: トピックスデータが {elapsed:.1f} 時間前（TTL {ttl_hours}h を超過）です。最新データを取得してください。")
            return True
    except Exception as e:
        print(f"[topics] TTL検証でエラーが発生しました: {e}")
    return False


def _check_per_source_ttl(data: dict, categories: list[str]) -> dict[str, bool]:
    """
    Per-source TTL検証: sources の各エントリの fetched_at をチェック。

    要求カテゴリのトピックを持たない source の扱い:
    - トピックを持つ source（他カテゴリ専属: pokemon 系等）: 対象外として False（期限切れ扱いしない）
    - トピック 0 件の source（完全失敗・未収集）: 従来どおり期限切れ True
    戻り値: {source_name: is_expired} ディクショナリ
    """
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    ttl_hours = data.get("ttl_hours", 24)
    sources = data.get("sources", {})
    by_category = data.get("by_category", {})
    expired = {}

    for src_name, src_data in sources.items():
        src_topics = src_data.get("topics", [])
        src_cats = set(t.get("category", "other") for t in src_topics)
        if not src_cats & set(categories):
            if src_cats:
                # 他カテゴリ専属の source は本チェックの対象外（自動fetchのトリガーにしない）
                expired[src_name] = False
                continue
            # トピック 0 件（完全失敗・未収集）は従来どおり期限切れ
            expired[src_name] = True
            continue
        fetched_at_str = src_data.get("fetched_at", "")
        if not fetched_at_str:
            expired[src_name] = True
            continue
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=JST)
            elapsed = (now - fetched_at).total_seconds() / 3600
            expired[src_name] = elapsed > ttl_hours
        except Exception:
            expired[src_name] = True

    return expired


def _auto_fetch_topics(prompt_type: str, categories: list[str], data: dict) -> dict | None:
    """
    指定カテゴリのトピックが不足している場合、fetch_topics.py を自動実行して最新データを取得。
    取得成功時は新しいデータdictを返し、失敗時はNoneを返す。
    """
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    ttl_hours = data.get("ttl_hours", 24)
    by_category = data.get("by_category", {})

    need_fetch = False
    for cat in categories:
        cat_items = by_category.get(cat, [])
        if len(cat_items) == 0:
            need_fetch = True
            break

    if not need_fetch:
        sources = data.get("sources", {})
        expired = _check_per_source_ttl(data, categories)
        for src, is_exp in expired.items():
            if is_exp:
                need_fetch = True
                break

    if not need_fetch:
        return None

    print(f"[topics] カテゴリ {categories} のデータが不足/期限切れです。自動取得を開始します。")
    try:
        result = subprocess.run(
            [sys.executable, "-u", os.path.join(PROJECT_DIR, "scripts", "fetch_topics.py"), "--prompt-type", prompt_type],
            capture_output=True, text=True, timeout=120, encoding="utf-8"
        )
        if result.returncode != 0:
            print(f"[topics] 自動取得失敗 (exit={result.returncode}): {result.stderr.strip()}")
            return None
        print(f"[topics] 自動取得完了: {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else 'ok'}")
    except subprocess.TimeoutExpired:
        print("[topics] 自動取得がタイムアウトしました")
        return None
    except Exception as e:
        print(f"[topics] 自動取得エラー: {e}")
        return None

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[topics] 自動取得後のJSON読み込み失敗: {e}")
        return None


def _append_trending_topics(
    ng_instruction: str,
    prompt_type: str,
    target_genres: list[str] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    """
    data/topics/latest.json が存在する場合、prompt_type に応じたカテゴリの
    トレンドタイトルを選択して ng_instruction の末尾へ付加する。
    target_genres が指定されている場合、事前スコアリング結果で
    ジャンル適合度の高い項目を優先選択する。
    Per-source TTL で期限切れのカテゴリがある場合は自動再取得を試みる。
    第2要素としてアフィリエイト用のトレンドキーワードリストを返す。
    第3要素として frontmatter 用のソースURLリストを返す。
    第4要素として生成情報セクション用のクリーンなトレンドタイトルリスト
    （"{title}（{source}）" 形式）を返す。
    ファイルが存在しない場合は元の ng_instruction と空リストを返す。
    """
    if not os.path.exists(TOPICS_JSON_PATH):
        print(f"[topics] {TOPICS_JSON_PATH} が見つかりません。トレンド注入をスキップします。")
        _save_trend_usage_log({
            "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "prompt_type": prompt_type,
            "data_file": TOPICS_JSON_PATH,
            "skipped": "file_not_found",
            "selected": [],
            "affiliate_keywords": [],
            "trend_source_urls": [],
        })
        return ng_instruction, [], [], []

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[topics] JSON 読み込み失敗: {e}")
        _save_trend_usage_log({
            "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "prompt_type": prompt_type,
            "data_file": TOPICS_JSON_PATH,
            "skipped": f"json_parse_error: {e}",
            "selected": [],
            "affiliate_keywords": [],
            "trend_source_urls": [],
        })
        return ng_instruction, [], [], []

    # prompt_type に合わせてカテゴリを選択（カテゴリ厳格化）
    if prompt_type in ("kemono_story", "novel", "story"):
        categories = ["kemono"]
    elif prompt_type == "default":
        categories = ["tech"]
    else:
        categories = ["tech", "kemono"]

    # Per-source TTL 検証（グローバルTTLも確認）
    global_expired = _check_topics_ttl(data)
    if global_expired:
        print("[topics] グローバルTTL超過")
    expired = _check_per_source_ttl(data, categories)
    has_expired = any(expired.values())
    if has_expired:
        expired_names = [s for s, v in expired.items() if v]
        print(f"[topics] 期限切れ source: {', '.join(expired_names)}")

    # 期限切れの場合、自動再取得
    if has_expired:
        new_data = _auto_fetch_topics(prompt_type, categories, data)
        if new_data:
            data = new_data

    by_cat = data.get("by_category", {})
    selected_titles: list[str] = []
    affiliate_keywords: list[str] = []
    trend_source_urls: list[str] = []
    trend_topic_titles: list[str] = []
    story_mode = prompt_type in ("kemono_story", "novel", "story")

    # Log tracking variables
    log_raw_count = 0
    log_after_score = 0
    log_after_rating = 0
    selected_items: list[dict] = []

    # 全カテゴリから候補を収集
    candidates: list[dict] = []
    for cat in categories:
        for item in by_cat.get(cat, []):
            log_raw_count += 1
            # スコアしきい値フィルタ
            if item.get("score", 0) < MIN_SCORE_THRESHOLD:
                continue
            log_after_score += 1
            # カテゴリ厳格化: 物語モードでは e621 全投稿をインスピレーション注入から除外
            # e621 はキャラクター特徴集計にのみ使用し、ストーリーテーマのインスピレーションには不適切
            if story_mode and item.get("source") == "e621":
                continue
            log_after_rating += 1
            title = item.get("title", "").strip()
            if title:
                candidates.append(item)

    TREND_SELECT_COUNT = 2
    if target_genres:
        scores_data = _load_genre_scores()
        if scores_data:
            candidates = _filter_by_genre(candidates, target_genres, scores_data)
    if len(candidates) > TREND_SELECT_COUNT:
        candidates = random.sample(candidates[:TREND_SELECT_COUNT * 3], TREND_SELECT_COUNT)

    for item in candidates:
        title = item.get("title", "").strip()
        source = item.get("source", "")
        url = item.get("url", "")
        desc = (item.get("description") or "").strip()
        if title:
            line = f"[{source}] {title}"
            if desc:
                line += f" — {desc[:100]}"
            selected_titles.append(line)
            trend_topic_titles.append(f"{title}（{source}）" if source else title)
            if url:
                trend_source_urls.append(url)
            selected_items.append({
                "title": title,
                "source": source,
                "url": url,
                "score": item.get("score", 0),
                "category": item.get("category", ""),
                "rating": item.get("rating", ""),
                "description": desc[:200],
            })
        # アフィリエイトキーワードは全カテゴリから抽出
        kw = _extract_affiliate_keyword(title)
        if kw:
            affiliate_keywords.append(kw)

    # TTL 情報をログに記録
    ttl_hours = data.get("ttl_hours", 24)
    fetched_at = data.get("fetched_at", "")
    per_source_ttl = data.get("per_source_ttl", {})

    if fetched_at:
        try:
            JST = timezone(timedelta(hours=9))
            fetched_dt = datetime.fromisoformat(fetched_at)
            if fetched_dt.tzinfo is None:
                fetched_dt = fetched_dt.replace(tzinfo=JST)
            elapsed = (datetime.now(JST) - fetched_dt).total_seconds() / 3600
        except Exception:
            elapsed = -1
    else:
        elapsed = -1

    # Trend usage log を保存
    _save_trend_usage_log({
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "prompt_type": prompt_type,
        "data_file": TOPICS_JSON_PATH,
        "data_fetched_at": fetched_at,
        "global_ttl": {
            "ttl_hours": ttl_hours,
            "elapsed_hours": round(elapsed, 2) if elapsed >= 0 else None,
            "expired": global_expired,
        },
        "per_source_ttl": {src: info.get("expired", False) for src, info in per_source_ttl.items()},
        "auto_fetch": {
            "triggered": has_expired,
            "success": data is not None,
        },
        "candidate_pool": {
            "categories": categories,
            "total_raw": log_raw_count,
            "after_score_filter": log_after_score,
            "after_rating_filter": log_after_rating,
            "final_candidates": len(candidates),
        },
        "selected": selected_items,
        "affiliate_keywords": affiliate_keywords,
        "trend_source_urls": trend_source_urls[:10],
    })

    if not selected_titles:
        return ng_instruction, affiliate_keywords, trend_source_urls, trend_topic_titles

    trend_block = (
        "\n\n【参考：今日のトレンドトピック（インスピレーション源として活用してください）】\n"
        + "\n".join(f"- {t}" for t in selected_titles)
    )
    print(f"[topics] {len(selected_titles)} 件のトレンドをプロンプトに注入しました")
    if affiliate_keywords:
        print(f"[affiliate] {len(affiliate_keywords)} 件のトレンドキーワードを抽出しました")
    return ng_instruction + trend_block, affiliate_keywords, trend_source_urls, trend_topic_titles
