"""記事末尾の「生成情報」セクション HTML 組立。

generate_article.py から分離（Phase 7）。
- 使用したトレンド情報 / キャラクターデータ / e621 参考キャラクターデータ
- h2〜h4 を使わない <details> 折りたたみ構造（TOC に載らない）
- 表示すべき内容が一切ない場合は空文字列（セクション非表示）
"""

import html
from datetime import datetime, timezone

from article.config import *  # noqa: F401,F403
from article.characters import _is_affiliate_excluded
from article.meta import _extract_fm_field


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
