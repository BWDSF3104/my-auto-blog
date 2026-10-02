# AI Memory Bank ガイド

docs/ai/ は git 追跡対象。変更履歴は git commit に委ね、docs/ai/ は「なぜ変えたか」の文脈を記録する。

更新タイミングは git commit 前。Memory Bank の変更はコード変更と同じ commit に含める。プロジェクト知識・状態・判断が変化した場合のみ更新する（コード変更 ≒ Memory Bank 更新ではない）。

## ファイル一覧

| ファイル | 役割 | 更新タイミング | 必須 |
|----------|------|---------------|------|
| `current-task.md` | アクティブタスクへの参照（ファイルパス、ステータス、Next Action のみ） | タスク開始時に参照行を追加。各チェックポイントでステータス・Next Action を更新。タスク完了時または中断時に参照行を削除 | ✅ |
| `tasks/*.md` | タスクの個別ファイル（1タスク1ファイル方式、アクティブ・完了問わず） | タスク開始時に `docs/ai/tasks/YYYY-MM-DD-short-name.md` として作成。完了時は Status を更新 | ✅ |
| `plans.md` | 計画書 | タスク開始前に Active Plans に記録（実装・調査問わず）。完了時は Completed Plans に意図・背景を1行記録 | ✅ |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除（変更履歴は git commit に委ねる） | ✅ |
| `known-issues.md` | 既知問題リスト | 新規問題発見時、問題解決時のステータス更新（解決済はアーカイブへ移動） | ✅ |
| `decisions.md` | 設計判断ログ | 構造・データフロー・新しい統合の設計判断。Decision / Reason / Rejected Alternatives を記録 | ✅ |
| `architecture.md` | アーキテクチャ図 | decisions.md に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |

- 完了したバグは `known-issues.md` のアーカイブへ移動
- `development-notes.md` は削除済み。詳細な実装履歴は git log で確認可能

## アーカイブルール

ファイルが膨張しないよう、完了したエントリは対応する `-archive.md` ファイルへ移動する。

| 本体ファイル | アーカイブファイル | 閾値 | 移動内容 |
|-------------|-------------------|------|---------|
| `plans.md` | `plans-archive.md` | Completed Plans が6件以上 | 古い Completed Plans エントリを移動 |
| `known-issues.md` | `known-issues-archive.md` | 解決済が1件以上 | 解決済エントリを即時移動 |
| `decisions.md` | `decisions-archive.md` | 15件以上 | 古い決定エントリを移動 |

- `current-task.md` はアクティブなタスクのみ保持。完了したタスクは `tasks/` へ個別ファイルとして移動
- `tasks/` のファイル名: `YYYY-MM-DD-short-name.md` 形式
- `Completed Plans` は直近5件まで `plans.md` に保持
- `Completed Plans` の追加は常に上部（prepend）。並び順=追加順=コミット順となり、git log の確認不要
- アーカイブのタイミング: 新規タスク開始時、または閾値超過時に実行
- アーカイブファイルは git 追跡対象

## Long-running Agent Tasks

- Before starting any task, read `docs/ai/current-task.md` if it exists.
- Before starting a planned change, read the relevant `plans.md` and `backlog.md` entries.
- After completing a meaningful step, update `docs/ai/current-task.md`.
- After a successful build/test checkpoint, record the result in `current-task.md`.
- If the task is interrupted, leave `current-task.md` in a resumable state.
- Never assume previous conversation context is still available after compaction.
- Important decisions must be recorded in `decisions.md`.
- Important unresolved problems must be recorded in `known-issues.md`.
- Do not start the next planned item until the current item's build/test completion criteria are satisfied.
- **After git commit & push**: Update `docs/ai/current-task.md` — set `Status` to `完了`, clear `Next Action`, and record the commit hash in the completed checklist.

## Recovery After Interruption

When resuming an interrupted task:

1. Read `docs/ai/current-task.md`.
2. Check `git status`.
3. Check `git diff`.
4. Verify the last recorded build/test status.
5. Continue from the `Next Action` in `current-task.md`.
6. Do not discard existing changes unless explicitly instructed.
