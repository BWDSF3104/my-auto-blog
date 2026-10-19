"""e621 キャラクター特徴の参考データ選出とプロンプト指示文整形。

generate_article.py から分離（Phase 7）。
- character_features.json からの参考投稿選出（_select_character_features / _select_two_posts）
- 版権 / artist の抽出（_filter_valid_copyrights / _extract_post_copyrights / _extract_top_artists）
- プロンプト注入指示文の生成（_format_character_features_instruction / _load_character_features）
"""

import json
import os

from article.config import *  # noqa: F401,F403
from article.trends import _load_genre_scores


def _is_affiliate_excluded(cp: str) -> bool:
    if cp in _AF_EXCLUDE_CPS:
        return True
    if any(cp.startswith(p) for p in _AF_EXCLUDE_CP_PATTERNS):
        return True
    if any(cp.endswith(p) for p in _AF_EXCLUDE_CP_PATTERNS):
        return True
    return False


def _cp_genre_score(cp: str, cp_scores: dict, target_genres: list[str]) -> float:
    """版権のジャンル適合スコア（target_genres の最大値、無スコア時は -1）を返す。"""
    s = cp_scores.get(cp)
    if not s:
        return -1
    return max(s.get(g, 0) for g in target_genres)


def _filter_valid_copyrights(aggregates: dict, target_genres: list[str] | None = None) -> list[str]:
    """集計版権を件数降順に並べアフィリエイト不適格を除外し、
    target_genres 指定時はジャンル適合度で優先する。最大10件を返す。"""
    aggregate_copyrights = sorted(aggregates.get("copyrights", {}).items(), key=lambda x: -x[1])
    valid_cps = [cp for cp, _ in aggregate_copyrights if not _is_affiliate_excluded(cp)]
    if target_genres:
        scores_data = _load_genre_scores()
        cp_scores = {c["name"]: c.get("scores") for c in scores_data.get("copyrights", []) if c.get("scores")}
        valid_cps.sort(key=lambda cp: _cp_genre_score(cp, cp_scores, target_genres), reverse=True)
    return valid_cps[:10]


def _extract_post_copyrights(selected: list[dict]) -> list[str]:
    """選出投稿から版権を抽出する（アフィリエイト不適格は除外・重複排除）。"""
    post_copyrights = []
    for post in selected:
        for cp in post.get("copyrights", []):
            if not _is_affiliate_excluded(cp) and cp not in post_copyrights:
                post_copyrights.append(cp)
    return post_copyrights


def _extract_top_artists(aggregates: dict) -> str:
    """人気artistを抽出し（unknown_artistは既に除外済み）上位1件のカンマ結合文字列を返す。
    同件数時は投稿数降順・次いで名前順。"""
    aggregate_artists = sorted(
        aggregates.get("artists", {}).items(), key=lambda x: (-x[1], x[0])
    )
    return (
        ", ".join(a for a, _ in aggregate_artists[:POPULAR_ARTIST_LIMIT])
        if aggregate_artists
        else "-"
    )


def _select_two_posts(posts: list[dict]) -> list[dict]:
    """投稿リストから異なる投稿を乱数で2つ抽選する。
    同一投稿の重複は構造的に不可能（random.sample）。
    作品（コピーライト）の重複時の再抽選はしない。"""
    import random

    if len(posts) < 2:
        return list(posts)

    return random.sample(posts, 2)


def _select_character_features(target_genres: list[str] | None = None) -> dict | None:
    """e621 から集計したキャラクター特徴を読み込み、プロンプト注入・生成情報表示に使用する参考データを選出する。
    投稿データから異なる2投稿を乱数抽選してキャラクタープロファイルを生成。
    人気作品：選出投稿の作品を上位1-2件。両投稿とも作品がない場合は、
    集計ベースの上位1-2件（target_genres 指定時は事前スコアリングで高スコア優先）にフォールバック。
    character_features.json が無い・読み取り不能・投稿データが空の場合は None を返す。
    """
    features_path = os.path.join("data", "character_features.json")
    if not os.path.exists(features_path):
        print("  [char-features] character_features.json が見つかりません（注入スキップ）")
        return None

    try:
        with open(features_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [char-features] 読み取り失敗: {e}（注入スキップ）")
        return None

    posts = data.get("posts", [])
    aggregates = data.get("aggregates", data)

    if not posts:
        print("  [char-features] 投稿データが空です（注入スキップ）")
        return None

    # 投稿から異なる2投稿を乱数抽選（作品重複時の再抽選なし）
    selected = _select_two_posts(posts)

    # 選出投稿から版権を抽出（アフィリエイト不適格は除外・重複排除）
    post_copyrights = _extract_post_copyrights(selected)

    # 人気作品：選出投稿に作品があればその上位N、なければ集計上位N（スコア順）にフォールバック
    if post_copyrights:
        copyright_names = ", ".join(post_copyrights[:POPULAR_CPS_LIMIT])
    else:
        base_copyrights = _filter_valid_copyrights(aggregates, target_genres)
        copyright_names = (
            ", ".join(base_copyrights[:POPULAR_CPS_LIMIT])
            if base_copyrights
            else "-"
        )

    # 人気artistを抽出（unknown_artistは既に除外済み）
    artist_names = _extract_top_artists(aggregates)

    return {
        "updated_at": data.get("updated_at", "unknown"),
        "total_posts": data.get("total_posts_analyzed", 0),
        "raw_posts": len(posts),
        "posts": selected,
        "copyrights": copyright_names,
        "artists": artist_names,
    }


def _format_character_features_instruction(info: dict | None) -> str:
    """e621 キャラクター特徴の参考データ（_select_character_features の戻り値）から、
    kemono_story プロンプトに注入する指示文を生成する。None の場合は空文字列。"""
    if not info:
        return ""

    lines = [
        "",
        "【キャラクター特徴のトレンドデータ（参考）】",
        "",
    ]

    # 各投稿からキャラクタープロファイルを生成
    for i, post in enumerate(info["posts"], 1):
        species = ", ".join(post.get("species", [])) or "-"
        colors = ", ".join(post.get("colors", [])) or "-"
        physical = ", ".join(post.get("physical", [])[:8]) or "-"
        characters = ", ".join(post.get("characters", [])) or "-"
        post_copyrights = ", ".join(cp for cp in post.get("copyrights", []) if not _is_affiliate_excluded(cp)) or "-"
        lines.append(f"・参考キャラクター{i}:")
        lines.append(f"  種族: {species}")
        lines.append(f"  色: {colors}")
        lines.append(f"  身体的特徴: {physical}")
        lines.append(f"  参照: {characters}")
        lines.append(f"  作品: {post_copyrights}")
        lines.append("")

    lines.append(f"・人気版権: {info['copyrights']}")
    lines.append(f"・人気artist: {info['artists']}")
    lines.append("")
    lines.append("アフィリエイトの製品推薦では、人気版権・キャラクターの公式グッズまたはトレンドに関連するゲーム・書籍・グッズを推奨してください。")

    print(f"  [char-features] 注入: updated_at={info['updated_at']}, posts={info['total_posts']} (raw:{info['raw_posts']}), selected={len(info['posts'])}, copyrights={len(info['copyrights'])}, artists={len(info['artists'])}")

    return "\n".join(lines)


def _load_character_features(target_genres: list[str] | None = None) -> str:
    """e621 から集計したキャラクター特徴を読み込んで、プロンプト用の指示文を生成する。
    投稿データからランダムに2投稿選出（版権重複時は再抽選）してキャラクタープロファイルを生成。
    版権は選出投稿から抽出し、不足分を集計結果から補完（アフィリエイト不適格は除外）。
    target_genres 指定時は、事前スコアリング結果でジャンル適合度の高い版権を優先する。
    """
    return _format_character_features_instruction(_select_character_features(target_genres))
