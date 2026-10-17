---
description: 新規タスク開始（タスクファイル作成 + current-task.tsv 参照行追加）
---

次のリクエストから AI Memory Bank の新規タスクを開始する:

$ARGUMENTS

手順:
1. リクエストから導出すること:
   - short-name: 小文字英数字とハイフンのみ（例 `task-slash-commands`）
   - タスク名: タスクファイルの `#` 見出し用の短い名称
   - backlog 参照（`P<N> #<N>`）・next action: 該当する場合
2. 実行する（既定で反映される。スクリプトがタスクファイルと `current-task.tsv` を git add する）:
   `python maintenance/task_manager.py add --slug <short-name> --title "<タスク名>" [--backlog "P<N> #<N>"] [--next-action "<next action>"]`
   書き込みなしのプレビューが必要な場合のみ `--dry-run` を付ける。
3. 生成されたタスクファイルの「意図 / 背景」などを edit ツールで記入する（日本語本文を CLI 引数に渡さない）。
4. `python maintenance/archive_memory_bank.py`（dry-run）を実行し、出力を確認して問題なければ `--apply` を付けて再実行する。
5. 結果（タスクファイルパス・tsv 行・アーカイブ結果）を報告する。git commit / push は行わない。
