# tmp/ クリーンの N 日保持

**Status**: 完了
**Date**: 2026-10-15

## 背景

`maintenance/archive_memory_bank.py` は `docs/ai/tmp/`（スクラッチ置き場）をタスク開始時に全削除するため、複数日にまたがる調査や equivalence run のスクラッチが失われる。ユーザー指示で「ある程度の期間は保持する」ように変更し、ルール（AGENTS.md / memory-bank-guide.md）を同時整備する。

## 調査結果 / 変更内容

- `maintenance/archive_memory_bank.py`:
  - `TMP_RETENTION_DAYS = 7` 定数を追加（既定の保持期間）
  - `build_plan()` に `tmp_retention_days: int = TMP_RETENTION_DAYS` 引数を追加
  - tmp/ 削除ロジックを「最更新 mtime が保持期間超過のエントリのみ削除」に変更
  - ディレクトリエントリは内部の再帰走査（`rglob`）による最更新 mtime で判定（ディレクトリ自身 mtime のみだとサブ配下の新しいファイル追加を検出できないため）
  - CLI に `--tmp-retention-days` オプションを追加（既定 7）
  - docstring の tmp/ 項目を保持期間ベースの記述に更新
- `maintenance/tests/test_archive_memory_bank.py`:
  - `make_tree` に tmp 内ネストディレクトリ（`old-sub/inner-old.txt`）と mtime 制御を追加
  - 既存テストを保持期間ベースの期待値に更新
  - 新規テスト 3 件追加:
    - `test_plan_tmp_dir_retained_when_nested_file_recent`（親は古い・サブ配下が新しい場合は保持）
    - `test_plan_tmp_retention_days_boundary`（保持期間ちょうど = 保持 / 1 日超過 = 削除）
    - `test_cli_tmp_retention_days_flag`（`--tmp-retention-days` 反映）
- ルール同期:
  - `AGENTS.md`: tmp/ の説明を「タスク開始時全削除」から「N 日（既定 7）保持」に更新
  - `docs/ai/memory-bank-guide.md`: ファイル一覧の tmp/ 行 + バッチクリーンアップ表を保持期間ベースに更新
  - `docs/ai/backlog.md`: P3 #12 に「N 日保持を実装済み」と注記更新
- `docs/ai/decisions/2026-10-15-tmp-retention.md`: 決定記録を作成（背景 / 選択肢 / 採用 / 影響）

## Verification

- `pytest maintenance/tests/ -v` → 15 passed
- `pytest scripts/tests/ -v` → 404 passed
- 実リポジトリ dry-run: `python maintenance/archive_memory_bank.py --date 2026-10-15`
  - `docs/ai/tmp/` の 2 件（`kilo-temp-inventory.tsv` / `inventory_kilo_temp.py`）が `keep (updated within 7d)` として保持
  - 0 actions（旧挙動なら両方を rm_file していた）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] `plans/` の該当ファイルを `plans/archive/` へ `mv`
- [x] `backlog.md` P3 #12 の注記を更新
