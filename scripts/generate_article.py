import os
import glob
import html
import json
import random
from dotenv import load_dotenv
load_dotenv()
import re
from datetime import datetime, timezone, timedelta
import sys
import time
from google import genai
from google.genai import errors

# Windows コンソールで cp932 → UTF-8 変換エラーを防ぐ
# （パイプ時はstdioがロケールcp932にフォールバックし、絵文字等非収録文字でUnicodeEncodeErrorになる）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --------------------------------------------------
# 設定
# --------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables.")

# 定数・パス・重み・パターン等の静的設定は article/config.py へ集約。
# env 読取りは load_dotenv()（上）の後に評価されるため、ここで読み込む。
from article.config import *  # noqa: F401,F403
from article.meta import (
    _cleanup_old_logs,
    _extract_fm_field,
    _save_affiliate_link_log,
    _save_draft_metadata,
    _save_trend_usage_log,
    get_existing_posts,
    get_recent_meta_by_type,
    get_recent_titles_by_type,
)
from article.slug_links import (
    _existing_link_spans,
    _get_existing_slugs,
    _load_posts_for_links,
    _load_slug_redirects,
    _resolve_slug_collision,
    _save_slug_redirects,
    inject_internal_links,
)
from article.image import (
    _build_kemono_tags,
    _generate_image_pollinations,
    _is_valid_kemono_combination,
    _parse_image_prompt_targets,
    _randomize_kemono_params,
    _save_as_avif,
    compose_image_prompt,
    extract_art_style,
    extract_character_prompts,
    extract_image_prompt,
    generate_and_save_image,
    process_inline_images,
    replace_character_placeholders,
)
from article.affiliate import (
    _extract_affiliate_keyword,
    _extract_article_body,
    _extract_article_keywords,
    _find_table_end_line,
    _generate_rakuten_card,
    _improve_keyword,
    _is_affiliate_bad_keyword,
    _is_github_repo_name,
    _kemono_affiliate_keywords,
    _rakuten_api_keywords,
    _rakuten_collect,
    _rakuten_first_phrase,
    _rakuten_is_relevant,
    _rakuten_load_cache,
    _rakuten_save_cache,
    _rakuten_search,
    extract_product_recommendations,
    generate_product_cards,
    inject_affiliate_links,
    process_inline_affiliates,
    process_inline_products,
    process_product_cards,
)
from article.trends import (
    _append_trending_topics,
    _auto_fetch_topics,
    _check_per_source_ttl,
    _check_topics_ttl,
    _filter_by_genre,
    _load_genre_scores,
)
from article.frontmatter import (
    _compose_smart_situation,
    _extract_faq_pairs,
    _extract_first_sentence_from_body,
    _extract_fm_tags,
    _extract_speakable_text,
    _fix_duplicate_yaml_keys,
    _get_body_after_fm,
    _generate_ascii_slug,
    _is_character_like_key,
    _validate_description,
    validate_and_fix_frontmatter,
)

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


def _is_affiliate_excluded(cp: str) -> bool:
    if cp in _AF_EXCLUDE_CPS:
        return True
    if any(cp.startswith(p) for p in _AF_EXCLUDE_CP_PATTERNS):
        return True
    if any(cp.endswith(p) for p in _AF_EXCLUDE_CP_PATTERNS):
        return True
    return False


def _select_character_features(target_genres: list[str] | None = None) -> dict | None:
    """e621 から集計したキャラクター特徴を読み込み、プロンプト注入・生成情報表示に使用する参考データを選出する。
    投稿データからランダムに2投稿選出（版権重複時は再抽選）してキャラクタープロファイルを生成。
    版権は選出投稿から抽出し、不足分を集計結果から補完（アフィリエイト不適格は除外）。
    target_genres 指定時は、事前スコアリング結果でジャンル適合度の高い版権を優先する。
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

    # 投稿からランダムに2つ選出（版権重複時は再抽選）
    selected = _select_two_posts(posts, max_retries=10)

    # 集計結果からベース版権を確保（アフィリエイト不適格は除外）
    aggregate_copyrights = sorted(aggregates.get("copyrights", {}).items(), key=lambda x: -x[1])
    all_valid_cps = [cp for cp, _ in aggregate_copyrights if not _is_affiliate_excluded(cp)]
    if target_genres:
        scores_data = _load_genre_scores()
        cp_scores = {c["name"]: c.get("scores") for c in scores_data.get("copyrights", []) if c.get("scores")}
        def _cp_genre_score(cp: str) -> float:
            s = cp_scores.get(cp)
            if not s:
                return -1
            return max(s.get(g, 0) for g in target_genres)
        all_valid_cps.sort(key=_cp_genre_score, reverse=True)
    base_copyrights = all_valid_cps[:10]

    # 選出投稿から版権を抽出（アフィリエイト不適格は除外）
    post_copyrights = []
    for post in selected:
        for cp in post.get("copyrights", []):
            if not _is_affiliate_excluded(cp) and cp not in post_copyrights:
                post_copyrights.append(cp)

    # 選出投稿の版権を先頭に、不足分を集計ベースで補完
    all_copyrights = list(post_copyrights)
    for cp in base_copyrights:
        if cp not in all_copyrights:
            all_copyrights.append(cp)

    copyright_names = ", ".join(c for c in all_copyrights[:8]) if all_copyrights else "-"

    # 人気artistを抽出（unknown_artistは既に除外済み）
    aggregate_artists = sorted(aggregates.get("artists", {}).items(), key=lambda x: -x[1])
    artist_names = ", ".join(a for a, _ in aggregate_artists[:8]) if aggregate_artists else "-"

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


def _select_two_posts(posts: list[dict], max_retries: int = 10) -> list[dict]:
    """投稿リストからランダムに2つ選出。版権が重複する場合は再抽選。"""
    import random

    if len(posts) < 2:
        return list(posts)

    # 最初の投稿をランダム選択
    first = random.choice(posts)
    first_copyrights = set(first.get("copyrights", []))

    # 2つ目の投稿を版権重複なしで選択
    for _ in range(max_retries):
        second = random.choice(posts)
        second_copyrights = set(second.get("copyrights", []))
        if not (first_copyrights & second_copyrights):
            return [first, second]

    # 再試行しても重複回避できない場合は最初の2投稿を返す
    return posts[:2]


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


def _gen_info_setting_rows(prompt_type: str, kemono_params: dict) -> list[tuple[str, str]]:
    """kemono_story のキャラクター設定行（体型 / 世界設定 / 変身 / 関係性 / 追加設定）を組立する。"""
    if prompt_type != "kemono_story" or not kemono_params:
        return []
    setting_rows: list[tuple[str, str]] = []
    setting_rows.append(("体型", kemono_params.get("char_type", "")))
    setting_rows.append(("世界設定", kemono_params.get("world_setting", "")))
    transform_label = _KEMONO_TRANSFORM_LABEL.get(
        kemono_params.get("transform_key", "none"), "なし"
    )
    setting_rows.append(("変身", transform_label))
    setting_rows.append(("関係性", kemono_params.get("relationship_text", "")))
    if kemono_params.get("extra_key", "none") != "none":
        setting_rows.append(("追加設定", kemono_params.get("extra_tag", "")))
    return setting_rows


def _gen_info_trend_block(trend_topic_titles: list[str]) -> list[str]:
    """「使用したトレンド情報」ブロックの HTML 行を組立する。"""
    items = "\n".join(f"      <li>{html.escape(t)}</li>" for t in trend_topic_titles)
    return [
        '    <div class="gen-info-block">',
        '      <p class="gen-info-block-title">使用したトレンド情報</p>',
        f'      <ul class="gen-info-list">\n{items}\n      </ul>',
        '    </div>',
    ]


def _gen_info_char_data_block(
    setting_rows: list[tuple[str, str]], char1: str, char2: str
) -> list[str]:
    """「キャラクターデータ」ブロックの HTML 行を組立する（行がなければ空リスト）。"""
    data_rows: list[str] = []
    for label, value in setting_rows:
        if value:
            data_rows.append(
                f'      <div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>'
            )
    if char1:
        data_rows.append(f'      <div><dt>キャラクター1</dt><dd>{html.escape(char1)}</dd></div>')
    if char2:
        data_rows.append(f'      <div><dt>キャラクター2</dt><dd>{html.escape(char2)}</dd></div>')
    if not data_rows:
        return []
    return [
        '    <div class="gen-info-block">',
        '      <p class="gen-info-block-title">キャラクターデータ</p>',
        '      <dl class="gen-info-dl">',
        "\n".join(data_rows),
        '      </dl>',
        '    </div>',
    ]


def _gen_info_e621_updated_label(e621_info: dict) -> str:
    """e621 データの updated_at を表示ラベルへ整形する（UTC 優先、破損時は原文）。"""
    updated_at = str(e621_info.get("updated_at", "unknown"))
    try:
        dt = datetime.fromisoformat(updated_at)
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return updated_at


def _gen_info_e621_block(e621_info: dict) -> list[str]:
    """「参考キャラクターデータ（e621）」ブロックの HTML 行を組立する。"""
    e621_rows: list[str] = []
    for i, post in enumerate(e621_info["posts"], 1):
        species = ", ".join(post.get("species", [])) or "-"
        colors = ", ".join(post.get("colors", [])) or "-"
        physical = ", ".join(post.get("physical", [])[:8]) or "-"
        characters = ", ".join(post.get("characters", [])) or "-"
        post_copyrights = ", ".join(cp for cp in post.get("copyrights", []) if not _is_affiliate_excluded(cp)) or "-"
        detail = "<br>".join([
            f"種族: {html.escape(species)}",
            f"色: {html.escape(colors)}",
            f"身体的特徴: {html.escape(physical)}",
            f"参照: {html.escape(characters)}",
            f"作品: {html.escape(post_copyrights)}",
        ])
        e621_rows.append(f'      <div><dt>参考キャラクター{i}</dt><dd>{detail}</dd></div>')
    e621_rows.append(
        f'      <div><dt>人気版権</dt><dd>{html.escape(e621_info.get("copyrights", "-"))}</dd></div>'
    )
    e621_rows.append(
        f'      <div><dt>人気artist</dt><dd>{html.escape(e621_info.get("artists", "-"))}</dd></div>'
    )
    updated_label = _gen_info_e621_updated_label(e621_info)
    e621_rows.append(
        f'      <div><dt>データ</dt><dd>{html.escape(updated_label)}'
        f"（{e621_info.get('total_posts', 0)}投稿を分析）</dd></div>"
    )
    return [
        '    <div class="gen-info-block">',
        '      <p class="gen-info-block-title">参考キャラクターデータ（e621）</p>',
        '      <dl class="gen-info-dl">',
        "\n".join(e621_rows),
        '      </dl>',
        '    </div>',
    ]


def _build_generation_info_section(
    trend_topic_titles: list[str],
    prompt_type: str,
    kemono_params: dict,
    content: str,
    e621_info: dict | None = None,
) -> str:
    """
    記事本文末尾に追記する「生成情報」セクションの HTML を組立する。
    使用したトレンド情報（タイトル＋ソース）とキャラクターデータ
    （体型 / 世界設定 / 変身 / 関係性 / 追加設定 + キャラクタータグ）、
    さらに e621 から使用した参考キャラクターデータ
    （参考キャラクター / 人気版権 / 人気artist / データ時点）を表示する。
    e621 データは kemono_story プロンプトのみで実際に使われるため、kemono_story 記事のみ表示。
    h2〜h4 を使わない `<details>` 折りたたみ構造のため TOC には載らない。
    表示すべき内容が一切ない場合は空文字列を返す（セクション非表示）。
    """
    char1 = _extract_fm_field(content, "character_1")
    char2 = _extract_fm_field(content, "character_2")

    setting_rows = _gen_info_setting_rows(prompt_type, kemono_params)
    show_e621 = bool(e621_info) and prompt_type == "kemono_story"

    if not trend_topic_titles and not setting_rows and not char1 and not char2 and not show_e621:
        return ""

    parts: list[str] = [
        '<details class="gen-info">',
        '  <summary class="gen-info-summary">🤖 生成情報</summary>',
        '  <div class="gen-info-body">',
        '    <p class="gen-info-note">この記事はAIパイプラインによる自動生成記事です。</p>',
    ]

    if trend_topic_titles:
        parts += _gen_info_trend_block(trend_topic_titles)

    char_data_block = _gen_info_char_data_block(setting_rows, char1, char2)
    if char_data_block:
        parts += char_data_block

    if show_e621:
        parts += _gen_info_e621_block(e621_info)

    parts += ['  </div>', '</details>']
    return "\n".join(parts)


# --------------------------------------------------
# メイン処理
# --------------------------------------------------
def build_ng_instruction(prompt_type, recent_titles, recent_metas):
    if recent_titles:
        past_topics_text = "\n".join([f"- {t}" for t in recent_titles])
        if prompt_type in ("kemono_story", "novel", "story"):
            ng_instruction = (
                f"【直近の執筆作品（テーマ・展開被り防止）】\n"
                f"直近で以下の物語を作成済みです。これらとシチュエーションや展開が極力被らないよう、新しいテーマで作成してください:\n"
                f"{past_topics_text}"
            )
        else:
            ng_instruction = f"【重要：重複の禁止】\n以下のタイトル・テーマは作成済みです:\n{past_topics_text}"
    else:
        ng_instruction = ""

    # 1.2. キャラクター・テーマ被り防止の追加指示
    if recent_metas and prompt_type in ("kemono_story", "novel", "story"):
        char_lines = []
        for meta in recent_metas:
            entries = []
            if "character_1" in meta:
                entries.append(f"キャラ1: {meta['character_1']}")
            if "character_2" in meta:
                entries.append(f"キャラ2: {meta['character_2']}")
            if "art_style" in meta:
                entries.append(f"アートスタイル: {meta['art_style']}")
            if "tags" in meta:
                entries.append(f"タグ: {meta['tags']}")
            if entries:
                entries_joined = "\n  ".join(entries)
                title = meta.get('title', '(不明)')
                char_lines.append(f"「{title}」\n  " + entries_joined)
        if char_lines:
            chars_joined = "\n".join(char_lines)
            ng_instruction += (
                f"\n\n【キャラクター・テーマ被り防止】\n"
                f"以下のキャラクター設定・テーマは直近で使用済みです。"
                f"同じ組み合わせや非常に類似した設定を使わず、新しいキャラクター・テーマで作成してください:\n"
                f"{chars_joined}"
            )
    return ng_instruction


def resolve_kemono(prompt_type):
    # 1.5. 世界設定を先に決定（ジャンルベースのトレンド選択に使用）
    kemono_params = _randomize_kemono_params() if prompt_type == "kemono_story" else {}
    target_genres = WORLD_SETTING_GENRE_MAP.get(kemono_params.get("world_setting_key", ""), []) or None
    return kemono_params, target_genres


def build_prompt(prompt_type, ng_instruction, pub_date_str, file_timestamp, kemono_params, target_genres):
    # 2. テキスト記事の生成
    # e621 参考データは1回選出し、プロンプト注入と生成情報表示の両方で同一データを使用
    template = load_prompt_template(prompt_type)
    e621_info = _select_character_features(target_genres=target_genres)
    prompt = template.format(
        ng_instruction=ng_instruction,
        pub_date_str=pub_date_str,
        character_features_instruction=_format_character_features_instruction(e621_info),
        **kemono_params
    )

    # 使用プロンプトの保存（追跡性確保）
    prompt_logs_dir = os.path.join("data", "prompt_logs")
    os.makedirs(prompt_logs_dir, exist_ok=True)
    prompt_path = os.path.join(prompt_logs_dir, f"{file_timestamp}.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"📝 プロンプト保存: {prompt_path}")
    return prompt, e621_info


def generate_content(prompt, prompt_type, file_timestamp, pub_date_str):
    pass1_start = time.time()
    response, pass1_model = generate_content_with_retry(prompt)
    pass1_duration = time.time() - pass1_start
    content = response.text.strip()

    # コードブロック装飾の除外
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    # Frontmatterが存在しない場合はデフォルトを付与（Geminiが---を出力しなかった場合の保険）
    if "---" not in content:
        content = f'---\ntitle: "Auto Post"\npubDate: "{pub_date_str}"\ndescription: ""\ntags: []\n---\n\n' + content
        print("[WARN] Frontmatterが検出されなかったためデフォルトを付与しました")

    # 2.5 2-pass 精製: 下書きを精製して質を高める
    draft_content = content
    pass2_start = time.time()
    content, pass2_model = refine_content(content, prompt_type)
    pass2_duration = time.time() - pass2_start

    # 2-pass 生成のメタデータを保存（効果測定用）
    _save_draft_metadata(
        file_timestamp=file_timestamp,
        prompt_type=prompt_type,
        article_filename=f"{file_timestamp}-auto-post.md",
        draft_content=draft_content,
        refined_content=content,
        pass1_model=pass1_model,
        pass1_duration=pass1_duration,
        pass2_model=pass2_model,
        pass2_duration=pass2_duration,
    )
    return content


def build_header_image(content, file_timestamp, article_seed):
    # 3. 記事本文からキャラクター設定と画像用シチュエーションプロンプトを抽出して画像生成
    characters = extract_character_prompts(content)
    if characters:
        print(f"👤 検出されたキャラクター設定 ({len(characters)}体):")
        for k, v in characters.items():
            print(f"   - {k}: {v}")
    else:
        print("👤 キャラクター設定は検出されませんでした（単発シチュエーションで生成します）")

    image_filename = f"{file_timestamp}-header.png"
    dynamic_situation = extract_image_prompt(content)
    if dynamic_situation == DEFAULT_SITUATION:
        smart_situation = _compose_smart_situation(content)
        if smart_situation != DEFAULT_SITUATION:
            dynamic_situation = smart_situation
            print(f"💡 image_prompt なし → 自動生成シチュエーション: {dynamic_situation}")
    print(f"💡 抽出されたヘッダー用シチュエーション: {dynamic_situation}")

    article_art_style = extract_art_style(content)
    print(f"🎨 記事のアートスタイル: {article_art_style}")

    full_image_prompt = compose_image_prompt(dynamic_situation, characters, article_art_style)
    print(f"🎨 ヘッダー画像合成プロンプト: {full_image_prompt}")
    image_url = generate_and_save_image(full_image_prompt, image_filename, article_seed)
    return image_url, characters, article_art_style


def _apply_slug_field(content, file_timestamp):
    # SEOスラッグの検証・生成: slug フィールドがない、または無効な場合はタイトルから生成
    slug_match = re.search(r'^slug:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    final_slug = slug_match.group(1).strip() if slug_match and slug_match.group(1).strip() else ""
    if not final_slug:
        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
        raw_title = title_match.group(1).strip() if title_match else file_timestamp
        final_slug = _generate_ascii_slug(raw_title)
        if final_slug and "---" in content:
            content = content.replace("---", f'---\nslug: "{final_slug}"', 1)
            print(f"🔗 スラッグを自動生成: {final_slug}")

    # slug競合の検出・解決: 既存記事と同じslugがあればユニークに調整してリダイレクトを記録
    if final_slug:
        existing = _get_existing_slugs()
        final_slug, _ = _resolve_slug_collision(final_slug, existing)
        if final_slug and "---" in content:
            slug_line = rf'^slug:\s*["\']?(.*?)["\']?$'
            content = re.sub(slug_line, f'slug: "{final_slug}"', content, count=1, flags=re.MULTILINE)
    return content


def apply_frontmatter_fields(content, image_url, prompt_type, kemono_params, trend_source_urls, file_timestamp):
    # 4. Frontmatterの調整 (image_prompt行を実際の画像URL image: "..." に置換または挿入、prompt_typeの記録)
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

    # SEOスラッグの検証・生成＋競合解決
    content = _apply_slug_field(content, file_timestamp)

    # 系統情報（prompt_type）をFrontmatterに付与（次回以降の同系統判定の精度向上）
    if not re.search(r'^prompt_type:.*$', content, re.MULTILINE) and "---" in content:
        content = content.replace("---", f"---\nprompt_type: \"{prompt_type}\"", 1)

    # ストーリー系: スクリプト決定パラメータ（構造化データ）からtagsを生成してfrontmatterに書き込む
    if prompt_type == "kemono_story" and kemono_params:
        tags_list = _build_kemono_tags(kemono_params)
        # 安全策: タグ内の / はAstro [tag].astro ルート区切りと衝突するため置換
        tags_list = [t.replace("/", "・") for t in tags_list]
        tags_yaml = ", ".join(f'"{t}"' for t in tags_list)
        content = re.sub(r'^tags:.*$', f'tags: [{tags_yaml}]', content, count=1, flags=re.MULTILINE)
        print(f"🏷️  tagsをスクリプト値で設定: {tags_list}")

    # トレンド参照URLをFrontmatterに記録（出典追跡用）
    if trend_source_urls and "---" in content:
        sources_yaml = "\n".join(f"  - {url}" for url in trend_source_urls[:10])
        sources_block = f"trend_sources:\n{sources_yaml}"
        if not re.search(r'^trend_sources:', content, re.MULTILINE):
            content = content.replace("---", f"---\n{sources_block}", 1)
    return content


def postprocess_content(content, file_timestamp, characters, article_art_style, article_seed, prompt_type, kemono_params, trend_keywords):
    # 5. 本文内画像の抽出・生成とMarkdown置換
    content = process_inline_images(content, file_timestamp, characters, max_images=MAX_INLINE_IMAGES, art_style=article_art_style, base_seed=article_seed)

    # 5.3 本文内の [character_N] プレースホルダーを置換
    content = replace_character_placeholders(content, characters)

    # 5.4 本文内アフィリエイトプレースホルダーの実リンク置換
    content = process_inline_affiliates(content)

    # 5.45 比較表内商品プレースホルダーの実リンク置換
    content = process_inline_products(content)

    # 5.47 楽天API用Gemini商品名を抽出（process_product_cardsがfrontmatterから除去するため先に取得）
    gemini_product_names = [
        p.get("name", "") for p in extract_product_recommendations(content) if p.get("name")
    ]

    # 5.48 product_recommendations → 商品カードHTMLの生成と挿入
    content = process_product_cards(content)

    # 5.5 アフィリエイト（おすすめ商品・書籍検索リンク）ブロックの自動挿入
    skw = _kemono_affiliate_keywords(kemono_params) if prompt_type == "kemono_story" and kemono_params else None
    content = inject_affiliate_links(content, trend_keywords=trend_keywords, script_keywords=skw, file_timestamp=file_timestamp, gemini_products=gemini_product_names, kemono_params=kemono_params)

    # 5.55 自動内部リンクの挿入
    content = inject_internal_links(content)
    return content


def apply_seo_schemas(content):
    # 5.58 FAQPage schema: 本文からQ&Aパターンを抽出してfrontmatterに記録
    faq_pairs = _extract_faq_pairs(content)
    if faq_pairs and "---" in content:
        faq_json = json.dumps(faq_pairs, ensure_ascii=False)
        if not re.search(r'^faq:', content, re.MULTILINE):
            content = content.replace("---", f"---\nfaq: '{faq_json}'", 1)
        print(f"📋 FAQPage schema: {len(faq_pairs)}件のQ&Aペアを抽出")

    # 5.59 Speakable schema: 本文の最初のパラグラフをfrontmatterに記録
    speakable = _extract_speakable_text(content)
    if speakable and "---" in content:
        safe_speakable = speakable.replace("\\", "\\\\").replace('"', '\\"')
        if not re.search(r'^speakable:', content, re.MULTILINE):
            content = content.replace("---", f'---\nspeakable: "{safe_speakable}"', 1)
        print(f"🎤 Speakable schema: 冒頭テキストを抽出 ({len(speakable)}文字)")
    return content


def finalize_and_save(content, file_timestamp, trend_topic_titles, prompt_type, kemono_params, e621_info):
    # 5.6 Frontmatter YAML の最終検証・修復
    content = validate_and_fix_frontmatter(content)

    # 5.7 SEOメタ記述の文字数検証・補正
    desc = _extract_fm_field(content, "description")
    if desc:
        corrected = _validate_description(desc, content)
        if corrected != desc:
            safe_corrected = corrected.replace("\\", "\\\\")
            content = re.sub(
                r'^description:\s*["\']?(.*?)["\']?$',
                f'description: "{safe_corrected}"',
                content,
                count=1,
                flags=re.MULTILINE,
            )
            print(f"📝 記述を補正: {len(desc)}→{len(corrected)}文字")

    # 5.8 本文末尾に生成情報セクションを追記（トレンド情報＋キャラクターデータ＋e621参考データ）
    gen_section = _build_generation_info_section(
        trend_topic_titles, prompt_type, kemono_params, content, e621_info
    )
    if gen_section:
        content = content.rstrip() + "\n\n" + gen_section + "\n"
        print(f"🤖 生成情報セクションを追記: {len(trend_topic_titles)}件のトレンド情報")

    # 6. 保存
    output_dir = "src/content/posts"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{file_timestamp}-auto-post.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"🎉 記事が正常に生成されました: {filepath}")

    # 7. 古いログのクリーンアップ（期間ベースで N 日前のファイルを削除）
    _cleanup_old_logs()
    return content


def generate_post():

    # 日本時間（JST = UTC+9）の定義
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)

    pub_date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    prompt_type = os.environ.get("PROMPT_TYPE", "default")
    recent_titles = get_recent_titles_by_type(prompt_type)
    recent_metas = get_recent_meta_by_type(prompt_type)
    ng_instruction = build_ng_instruction(prompt_type, recent_titles, recent_metas)

    kemono_params, target_genres = resolve_kemono(prompt_type)

    # 1.6. 収集済みトレンドトピックをプロンプトに注入（ジャンル適合度で優先選択）
    ng_instruction, trend_keywords, trend_source_urls, trend_topic_titles = _append_trending_topics(
        ng_instruction, prompt_type, target_genres=target_genres
    )

    prompt, e621_info = build_prompt(
        prompt_type, ng_instruction, pub_date_str, file_timestamp, kemono_params, target_genres
    )

    # 2. テキスト記事の生成（2-pass: 下書き → 精製）
    content = generate_content(prompt, prompt_type, file_timestamp, pub_date_str)

    # 記事レベルのbase seedを生成（同じ記事内の画像でスタイルを一貫させる）
    article_seed = random.randint(0, 2**31 - 1)
    print(f"🎲 記事のbase seed: {article_seed}")
    image_url, characters, article_art_style = build_header_image(content, file_timestamp, article_seed)

    # 4. Frontmatterの調整（image / slug / prompt_type / tags / trend_sources）
    content = apply_frontmatter_fields(
        content, image_url, prompt_type, kemono_params, trend_source_urls, file_timestamp
    )

    # 5. 本文の事後処理（本文内画像・プレースホルダー・アフィリエイト・商品カード・内部リンク）
    content = postprocess_content(
        content, file_timestamp, characters, article_art_style, article_seed,
        prompt_type, kemono_params, trend_keywords,
    )

    # 5.58-5.59 SEOスキーマ（FAQPage / Speakable）
    content = apply_seo_schemas(content)

    # 5.6-7. 最終検証・生成情報追記・保存・ログクリーンアップ
    finalize_and_save(content, file_timestamp, trend_topic_titles, prompt_type, kemono_params, e621_info)


if __name__ == "__main__":
    generate_post()

