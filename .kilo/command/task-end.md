---
description: タスク完了処理（Status 行更新 + tsv 参照行削除 + レポート）
---

次のタスクを完了処理する:

$ARGUMENTS

手順:
1. リクエストから `--task` の値（パス / date-slug / slug）を導出する。曖昧な場合は `docs/ai/tasks/` の候補を列挙してユーザーに確認する。
2. 実行する（既定で反映される。スクリプトがタスクファイルと `current-task.tsv` を git add する）:
   `python maintenance/task_manager.py end --task <task>`
   書き込みなしのプレビューが必要な場合のみ `--dry-run` を付ける。
3. レポートに列挙された未チェックの「完了時 Memory Bank 操作」項目（known-issues の mv・backlog の削除など）を実行する（判定はエージェント）。
4. タスクファイルの「Verification」セクションを記入する。
5. commit を行う場合: スクリプトが staging していない他ファイルを `git add` し、`docs/ai/workflows.md` に従って commit（メッセージ作成）/ push する。
