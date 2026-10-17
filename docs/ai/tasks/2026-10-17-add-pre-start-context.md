# task_manager add に開始前コンテキスト・Agent 指示の自動出力を追加

**Status**: 完了
**Date**: 2026-10-17

## 意図 / 背景

タスク開始時に行うべきだが `/task-add` に組み込まれていなかった項目（current-task.tsv 読取 / backlog エントリ読取 / memory-bank-guide 参照 / 実装着手禁止の明示 / git status 確認 / 進行中タスク確認）を、「スクリプトによる自動化 + 操作内容・Agent 向け指示のスクリプト出力」方針で吸収する。`task_manager.py add` が開始前コンテキストを自動収集し、`--- 開始前コンテキスト ---` / `--- Agent 指示 ---` ブロックとして出力する。警告は非ブロッキング。`archive_memory_bank.py` は `add` に内包させない（dry-run 既定の安全方針維持）。

## 調査結果 / 変更内容

`task_manager.py` に開始前コンテキストの自動収集と Agent 指示の出力を追加（方針: スクリプトによる自動化 + 操作内容・Agent 向け指示をスクリプトが出力）。

- `maintenance/task_manager.py`:
  - `_backlog_entry(root, ref)`: `--backlog "P<N> #<N>"` を `## P<N>` セクションの `| <N> |` 行にパースしてエントリ行を返す
  - `_pre_start_context(root, task_posix, args)`: 書き込み前に (1) `git status --porcelain`（失敗時は `working tree: unknown`）・(2) 他タスクの進行中行（task_file + next_action）・(3) backlog エントリ を収集。全項目読み取りのみ・非ブロッキング
  - `_agent_instructions(active_count)`: ガイド参照 / 他タスク進行中ならユーザー確認 / 意図・背景記入 / archive_memory_bank 実行（dry-run → --apply）/ 開始完了まで実装着手しない を番号付きで出力
  - `cmd_add`: 重複チェック後・書き込み前にコンテキスト収集し、出力末尾に `--- 開始前コンテキスト ---` と `--- Agent 指示 ---` ブロックを追加。モジュール docstring を更新
  - 意図的に `archive_memory_bank.py` を内包させない（dry-run 既定の安全方針維持）
- `maintenance/tests/test_task_manager.py`: 既存 3 件を更新（`add` は `git status --porcelain` を 1 回呼び出すため calls 期待値・monkeypatch 追加）+ 新 6 件（clean/進行中なし、他タスク進行中行出力、dirty 警告、git 不可時 unknown、backlog エントリ出力（同号の別セクション混入なし）、backlog 未発見警告）
- `.kilo/command/task-add.md`: 手順2 に「スクリプトは開始前コンテキスト + Agent 指示を出力する。出力に従って各項目を処理する（他タスク進行中はユーザーへ確認）」を追加

## Verification

- `pytest maintenance/tests/ -v` → **51 passed** in 1.08s（変更前 45 件 + 新 6 件）
- スモーク（`docs/ai/tmp/smoke-add-ctx` に一時リポジトリを作成し `--root` で実行、使用後 `kilo-safe-rmdir.cmd` で削除）:
  - clean tree: `working tree: clean` / `in-progress tasks: 1`（pokemon タスク + next_action 表示）/ backlog P2 #17 のエントリ行出力 / Agent 指示 5 件出力（他タスク確認行含む）
  - dirty tree: `working tree: dirty (3 path(s)):` + 警告行 / `in-progress tasks: 2`
- 実リポジトリで本タスク作成時に `add` を実行（旧出力・新機能対象外）— 新出力はスモークで検証
- `git diff` で全変更ファイルを確認（破損なし）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当なし）
- [ ] `backlog.md` の完了項目を削除（該当なし）
