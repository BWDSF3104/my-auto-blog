# 2026-10-13: e621 humanoid 系タグの species / physical 双方から除外

**Status**: 完了（2026-10-13）
**Next Action**: なし

## 概要

anthro 形態フィルタ（`2026-10-13-anthro-physical-filter.md`）の続き。
humanoid 系タグの確認時に、`humanoid_hands`（general→physical）のみ除外済みで、
species 側の `humanoid` / `animal_humanoid` / `dragon_humanoid` は「種族」行に表示され
フィルタされないと報告したところ、ユーザーから
「humanoid を含むなら除外対象。体型に影響が出るため」との指示を受けた。

`humanoid` 系タグは人型の体型を示し、Python 側ランダム体型パラメータ
（`_randomize_kemono_params`）と競合し得るため、species と physical_features の
**双方**から除外するよう修正。

## 変更内容

- `scripts/fetch_topics.py`:
  - 新規ヘルパー `_is_humanoid_tag(tag)`: `"humanoid" in tag` を返す
    （`humanoid` / `animal_humanoid` / `dragon_humanoid` / `humanoid_hands` すべてを網羅）
  - `_is_physical_excluded`: 先頭で `_is_humanoid_tag` をチェック（general 側の humanoid 除外）
    - 上記に包含されるため `humanoid_hands` を明示リスト `_PHYSICAL_EXCLUDE_TAGS` から削除（DRY）
  - `_aggregate_and_save_character_features`: species タグを `_is_humanoid_tag` でフィルタ
    （`post_species` と `species_counter` 双方に適用 → `posts[].species` と `aggregates.species` 両方から除外）
- `scripts/tests/test_fetch_topics.py`:
  - `_aggregate_and_save_character_features`, `_is_humanoid_tag` を import 追加
  - `TestIsHumanoidTag` 新規（4テスト）: humanoid 一致 / 後置系 / 前置系 / 非 humanoid
  - `TestAggregateHumanoidFilter` 新規（2テスト）:
    species の humanoid 系除外＋通常種族維持 / general の humanoid_hands が physical から除外

## 影響

- 次回 `fetch_topics.py` 実行で再収集時に `character_features.json` が書き換わり:
  - `posts[].species` と `aggregates.species` から `humanoid` / `animal_humanoid` / `dragon_humanoid` が消える
  - `physical_features` から `humanoid_hands` が消える（前回追加分の継続）
- kemono_story プロンプトの「種族」行から humanoid 系タグがなくなる
- 現行ファイルは上書きされるまで旧値のまま（`humanoid: 1` 等が残る）

## Verification

- `python -m pytest scripts/tests/ -q` → **387 passed**（6.92s、新規6テスト含む）
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要
