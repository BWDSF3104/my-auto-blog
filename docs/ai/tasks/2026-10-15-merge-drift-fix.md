# 2026-10-15: テレンドデータ `by_category`/`all` の merge 構造ドリフト修正

**Status**: 完了（2026-10-15）
**Date**: 2026-10-15

## 背景

backlog P3 #7 / `known-issues/KI-20261010-01-merge-drift.md`。`fetch_topics.py` の `build_output()` で `by_category` はカテゴリ単位継承、`all`/`sources` は source 単位継承のため構造が乖離し、`all` に存在しない旧トピックが `by_category` に恒常残存していた。2026-10-15 検証で `latest.json`（2026-10-14 収集分）に GitHub 2 件（`ivi-vink/Akkamon` score=2 / `Ahmadsadin36/pokedex` score=0）が全 10 タイムスタンプファイルにわたり再発確認。

## 変更内容

- `scripts/fetch_topics.py` `build_output()`: `by_category` のカテゴリ単位独立継承（`prev_by_category` 参照）を廃止。source 継承 → `NON_TREND_SOURCES` フィルタ後に `all`（`all_topics_merged`）から毎回再構築。`prev` の `by_category` は一切読まなくなる
- 意図的挙動変化: 収集カテゴリにも未収集 source の継承トピックが `by_category` に反映される（旧は fresh のみで上書き、`all` と乖離）。新設計では `by_category` ≡ `all` のカテゴリ分割
- `scripts/tests/test_fetch_topics.py`:
  - `test_by_category_uncollected_inherited` を修正 — 旧テストは `sources: {}` 状態で `by_category` 単体のみのトピック（= ドリフト状態そのもの）の継承を期待していたため、prev を `sources` 一貫状態（reddit 未収集 source 継承）へ修正。期待結果（未収集 source のトピックが by_category に残存）は不変
  - `test_by_category_drift_not_inherited` を新規追加 — prev の `by_category` にのみ存在するトピック（`all`/`sources` にない）は出力へ継承されないこと + 構造不変条件（`by_category` のフラット集合 == `all` の集合）
- `data/topics/*.json`（11 ファイル: 10 タイムスタンプ + `latest.json`）: ドリフト 2 件（GitHub `ivi-vink/Akkamon` / `Ahmadsadin36/pokedex`）を `by_category.pokemon` から一括除去（一次性・e621 分離時の前例に従う）
- `decisions/2026-10-15-by-category-rebuild-from-all.md` を新規作成

## Verification

- `python -m pytest scripts/tests/ -v` → **398 passed**（7.86s、`test_fetch_topics.py` 62 件含む・新規テスト `test_by_category_drift_not_inherited` PASS）
- ドリフト検証スクリプト（`C:\Users\fujim\AppData\Local\Temp\kilo\check_merge_drift.py`）: 除去前 `latest.json` 他 11 ファイル全て `by_category - all = 2` → 除去後全ファイル **drift=0**・`all - sources = 0`（`by_category`/`all`/`sources` 三者 73 件一致）
- 除去後 JSON 全ファイル parse 成功（スクリプト実行自体が parse を含む）・`git diff --stat` で各ファイル 14 行減（2 エントリ相当）のみを確認

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] `plans/2026-10-15-merge-drift-fix.md` を `plans/archive/` へ `mv`
- [x] `known-issues/KI-20261010-01-merge-drift.md` を `known-issues/archive/` へ `mv`
- [x] `backlog.md` の P3 #7 を削除
