# `/task-add` / `/task-end` スラッシュコマンドと task_manager.py

**Status**: 進行中
**Date**: 2026-10-16

## 意図 / 背景

AI Memory Bank のタスク開始/終了の機械的作業を減らすため、Kilo スラッシュコマンド `/task-add` / `/task-end` と補助スクリプト `maintenance/task_manager.py` を新設する。2026-10-16 セッションで「どこまでがスクリプトで可能か」を検討し方針を提示した後、ユーザー指摘により slug 導出・git commit/push 担当・git diff レポートの 3 点を見直し決定した。

## 決定事項

### 構成と担当分割
1. スラッシュコマンド（`.kilo/command/task-add.md` / `task-end.md`）は薄いプロンプトラッパ。ロジックは全て `maintenance/task_manager.py` に集約（テスト可能）。
2. スクリプト（機械的）担当:
   - ファイル名組み立て `YYYY-MM-DD-<slug>.md`（slug 導出はしない）
   - 衝突チェック（既存タスクファイル / 重複 tsv 行）→ exit 1
   - 骨架ファイル生成（ガイドテンプレート + `**Next Action**:` 行）
   - `current-task.tsv` 行の追加/削除
   - Status 行（タスクファイル冒頭の `**Status**:` 行、ガイド `:71`）の regex 置換。置換前の値をレポート
   - レポート: `git status --porcelain` / `git diff --stat` / `git diff --cached --stat` + 期待ファイルリスト（タスクファイル / `docs/ai/current-task.tsv` / `docs/ai/backlog.md` / `docs/ai/known-issues/` 先頭一致）との照合による想定外ファイル警告。フル差分は出さない（cp932 パイプ出力の膨張・乱れ回避）
   - **staging**: スクリプト自身が作成・変更したファイル（タスクファイル + `current-task.tsv`）を `--apply` 時に `git add`（staging のみ）。`--no-git-add` でスキップ。staging 失敗は警告のみ（exit code はファイル操作の結果に依存）
3. エージェント（意味的）担当:
   - slug 導出（スクリプトの `--slug` 引数に渡す — ユーザー見直し）
   - 意図/背景の記述（骨架を edit ツールで埋める。CLI 引数に日本語本文を渡さない → PowerShell 5.1 クォーティング/エンコーディング問題回避）
   - Verification 記録
   - known-issues mv / backlog 削除の判定
   - スクリプトが判断できない**他ファイル**の `git add` + `git commit`（メッセージ作成）/ `git push`（workflows.md 手順）

### CLI 設計
- `python maintenance/task_manager.py add --slug <short-name> --title <タスク名> [--backlog "P2 #17"] [--next-action "..."] [--apply]`
- `python maintenance/task_manager.py end --task <パス|date-slug|slug> [--apply]`
- `add`: 骨架生成 + tsv 行追加。ファイル既存 or 重複 tsv 行なら exit 1。
- `end` の `--task` 解決ルール:
  1. パス（root 相対/絶対）として実在 → 使用
  2. `.md` 終端 → `docs/ai/tasks/` 内でファイル名完全一致
   3. それ以外 → slug 部（`YYYY-MM-DD-` プレフィックス除外）が値そのもの、または `<値>-` プレフィックス / `-<値>` サフィックス（ハイフン境界）の候補。候補 1 個 → 使用 / 複数 → exit 1 + 候補リスト / 0 個 → exit 1
  - 処理: Status 行 → `**Status**: 完了`（置換前値をレポート）+ tsv 行削除（無ければ note）+ レポート（未チェックの「完了時 Memory Bank 操作」項目を列挙。チェックボックスは書き換えない）。known-issues/backlog の編集は含めない。
- 引数なしモード（進行中 1 行を自動解決）は v1 スコープ外（進行中複数行で曖昧になる）。`note` / `status` サブコマンドも v1 スコープ外。

### 規約準拠
- argparse / dry-run 既定 + `--apply` / `--root`（`maintenance/archive_memory_bank.py` と同一。root 既定 = `Path(__file__).parent.parent`）
- TSV: UTF-8（BOM なし）・LF・`task_file` = posix パス・照合は `relative_to(root).as_posix()`
- Windows エンコーディング: import 直後に win32 ガード付き `sys.stdout.reconfigure(encoding="utf-8")` ブロック（先例: `2026-10-09-windows-console-encoding.md`）

### テストとスコープ
- `maintenance/tests/test_task_manager.py`（tmp_path 使用・外部 API 呼び出しなし）+ `pytest maintenance/tests/ -v`
- ルール同期: AGENTS.md / `docs/ai/memory-bank-guide.md` にコマンド参照を追記

### 実装順
1. `task_manager.py` + テスト（pytest）
2. `.kilo/command/task-add.md` / `task-end.md`
3. ルール同期

## 決定待ち（デフォルトで進める）

| # | 項目 | デフォルト（この方針で進める） |
|---|------|--------------------------------|
| O1 | `add` 骨架テンプレート内容 | ガイド `:68-92` テンプレート + `**Next Action**:` 行（実例ファイル準拠） |
| O2 | `--next-action` 反映先 | tsv 行の next_action 列と骨架 `**Next Action**:` 行の両方（未指定なら双方省略） |
| O3 | `/task-add` フロー | タスクファイル作成後に `archive_memory_bank.py` 実行（dry-run 確認後 apply） |
| O4 | pokemon タスクの tsv 行（進行中・J1〜J5 待ち） | そのまま維持し併存タスクとして扱う |

## Verification

- 2026-10-17: `pytest maintenance/tests/ -v` → 45 passed in 1.14s（archive_memory_bank 23 + task_manager 22）
- 2026-10-17: `python maintenance/task_manager.py add --slug smoke-dry-run --title "スモークテスト" --next-action "確認"`（dry-run）→ 出力確認 OK
- 2026-10-17: `python maintenance/task_manager.py end --task task-slash-commands`（dry-run）→ 出力確認 OK（porcelain 先頭行の先頭スペース保持修正後、`AGENTS.md` 警告が正しく表示されることを確認）
- 2026-10-17: `.kilo/command/task-add.md` / `task-end.md` 作成 → config_validation 成功

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
