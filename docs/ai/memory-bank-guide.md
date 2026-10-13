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

新規タスク開始時に実行する。正常運用時のコンテキスト消費を最小化する。

### 容量上限（超過時はその場で圧縮）

| ファイル | 上限 | 超過時の処理 |
|---------|------|-------------|
| `current-task.md` | 3 KB | 完了タスクの参照行を削除（詳細は `tasks/` に既記） |
| `plans.md` | 5 KB | Completed Plans の古いエントリを `plans-archive.md` へ移動 |
| `decisions.md` | 15 KB | 古いエントリを `decisions-archive.md` へ移動 |
| `known-issues.md` | 3 KB | 解決済を `known-issues-archive.md` へ移動 |

### 形式ルール

- `current-task.md`: 1タスク1行（ファイルパス・ステータス・Next Action のみ）。完了タスクは参照行を削除
- `decisions.md`（アクティブ）: 各エントリは `Decision` + `Reason` の2フィールドのみ。`Rejected Alternatives` / `Impact` はアーカイブ時に付与
- `plans.md` Completed Plans: 各エントリ150文字以下（意図・背景のみ）
- `tasks/` ファイル名: `YYYY-MM-DD-short-name.md`

### クリーンアップ（新規タスク開始時に実行）

1. `current-task.md`: 完了・中断済みの参照行を削除
2. `decisions.md`: 10件超過分を `decisions-archive.md` へ移動（フル4フィールドで）
3. `plans.md`: Completed Plans 5件超過分を `plans-archive.md` へ移動
4. `tasks/`: Status `完了` + 日付が14日以上経過したファイルを `tasks/archive/` へ移動
5. `verification/`: 機能ディレクトリ毎に直近2ランのみ保持、それ以前を削除
6. `tmp/`: 全ファイルを削除

- `Completed Plans` の追加は常に上部（prepend）。並び順=追加順=コミット順
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
- **タスク完了時（git commit 前）**: `docs/ai/current-task.md` の `Status` を `完了` に更新し、`Next Action` をクリアする。Memory Bank の変更はコード変更と同じ commit に含める。

## Recovery After Interruption

When resuming an interrupted task:

1. Read `docs/ai/current-task.md`.
2. Check `git status`.
3. Check `git diff`.
4. Verify the last recorded build/test status.
5. Continue from the `Next Action` in `current-task.md`.
6. Do not discard existing changes unless explicitly instructed.
