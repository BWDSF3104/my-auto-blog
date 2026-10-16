---
description: タスク完了処理（Status 行更新 + tsv 参照行削除 + レポート）
---

次のタスクを完了処理する:

$ARGUMENTS

手順:
1. リクエストから `--task` の値（パス / date-slug / slug）を導出する。曖昧な場合は `docs/ai/tasks/` の候補を列挙してユーザーに確認する。
2. まず dry-run を実行:
   `python maintenance/task_manager.py end --task <task>`
3. 出力を確認し問題なければ、同じコマンドに `--apply` を付けて再実行する（スクリプトがタスクファイルと `current-task.tsv` を git add する）。
4. レポートに列挙された未チェックの「完了時 Memory Bank 操作」項目（known-issues の mv・backlog の削除など）を実行する（判定はエージェント）。
5. タスクファイルの「Verification」セクションを記入する。
6. commit を行う場合: スクリプトが staging していない他ファイルを `git add` し、`docs/ai/workflows.md` に従って commit（メッセージ作成）/ push する。
