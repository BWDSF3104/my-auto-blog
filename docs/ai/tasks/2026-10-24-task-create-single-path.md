# タスクファイル作成単一経路ルール強化

**Status**: 進行中
**Date**: 2026-10-24
**Next Action**: AGENTS.md / memory-bank-guide.md / .kilo/command/task-add.md へ禁止条項・修正例条項を追加

## 意図 / 背景

タスクファイル作成についてのルール記載を確認した結果、現行ルール（AGENTS.md / memory-bank-guide.md / slash コマンド）は「`task_manager.py add` を実行せよ」という**肯定的な指示のみ**で、write/edit ツールによるタスクファイル直接作成を禁止する**禁止条項**がない。そのために「task-add スクリプトを使わずにタスクファイルを作成してしまう」事例が生じた。今回のルール強化では、タスクファイル作成・`current-task.tsv` 参照行追加を「スクリプト単一経路」と明示し、直接作成の禁止条項と、経路外作成を発見した場合の修正手順（`known-issues/` 記録 + tsv 参照行同期）を記述する。

## 調査結果 / 変更内容

（記入）

## Verification

（記入）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
