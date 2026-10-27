# 2026-10-13: e621 physical_features から anthro 形態・体位タグの除外

**Status**: 完了（2026-10-13）
**Next Action**: なし

## 概要

ユーザー調査: キャラクター体型決定で使う e621 タグはフィルタされているか、と確認したところ、
`_PHYSICAL_EXCLUDE_TAGS`（`scripts/fetch_topics.py`）が除外するのは性別・体型バリアント
（`male_anthro` / `female_anthro` / `muscular_anthro` / `young_anthro`）のみで、
素の `anthro` 系タグが physical_features へ漏れていた。
現行 `data/character_features.json` で `anthro: 22`（physical 最多タグ）、
`biped: 4`、`humanoid_hands: 2`、`semi-anthro` / `human_on_anthro` / `clothed_anthro` /
`fully_clothed_anthro` が各 1 件確認。Python 側ランダム体型パラメータ（`_randomize_kemono_params`）
と競合し得るため、ユーザー指示でこれらも除外するよう修正。

## 変更内容

- `scripts/fetch_topics.py`:
  - `_PHYSICAL_EXCLUDE_TAGS` に「形態・体位（anthro/立ち姿勢）」グループとして 8 タグ追加:
    `anthro`, `semi-anthro`, `human_on_anthro`, `clothed_anthro`, `fully_clothed_anthro`,
    `biped`, `quadruped`（予防的追加、現在データに無い）, `humanoid_hands`
- `scripts/tests/test_fetch_topics.py`:
  - `_is_physical_excluded` を import 追加
  - `TestIsPhysicalExcluded` 新規（6テスト）: anthro 形態系除外 / 体位系除外 /
    humanoid_hands 除外 / 既存性別・体型タグ回帰 / パターン除外（from_/looking_/_background）/
    通常タグ（ears・tail・claws 等）は除外されない

## 影響

- 次回 `fetch_topics.py` 実行で再収集時に `character_features.json` が書き換わり、
  physical_features から上記 8 タグが消える（現行ファイルは上書きされるまで旧値のまま）
- kemono_story プロンプトの「身体的特徴」行から形態・体位タグがなくなる
- `clothed` / `clothing` 等の衣服タグは対象外（除外リスト未登録のまま。今回は anthro 形態系のみに限定）

## Verification

- `python -m pytest scripts/tests/ -v` → 381 passed（約7秒、新規6テスト含む）
- `scripts/tests/test_fetch_topics.py` 単独 → 55 passed（約3秒）
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要
