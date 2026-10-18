# archive の git-add で gitignore 対象を staging から除外（KI-20261018-01）

**Status**: 完了
**Date**: 2026-10-18
**Backlog**: なし (KI-20261018-01)
**Next Action**: archive_memory_bank.py 修正・検証・タスクファイル更新

## 意図 / 背景

`KI-20261018-01`: `python maintenance/archive_memory_bank.py --apply` が `tmp/` のエントリ削除を含む場合、削除（ゴミ箱へ移動）自体は成功するのに、末尾の `git add -- docs/ai/tmp/<entry>` が「pathspec did not match」で失敗し exit 1 になる。`docs/ai/tmp/` は `.gitignore` の `tmp/` により全レベル gitignore 対象であり、tmp/ エントリは未追跡・git 管理外のため staging 対象ではない。

本タスク: `--apply` の git-add 手順で gitignore 対象パス（git check-ignore で事前判定）を staging 対象から除外し、クリーンアップ完了時にスクリプトが exit 0 になるようにする。

## 調査結果 / 変更内容

- `maintenance/archive_memory_bank.py`:
  - 新関数 `_git_ignored_paths(root, paths)` を追加: `git -C <root> check-ignore -q -- <rel>` を各パスで呼び、exit 0（gitignore 対象）の相対パスを `set[str]` で返す。check が失敗した場合（例: git repo 外、exit != 0）は除外しない（従来挙動へフォールバック）。
  - `execute_plan` の git-add ブロック: staging 対象（sorted(set)）から `_git_ignored_paths` で判定した gitignore 対象を除去し、残りにのみ `git_add` を呼び出す。全パスが gitignore 対象の場合は `git_add` を呼びわずに「skipped」と記録。除外したパスは git_add 結果の message に `staged (excluded gitignored: ...)` として報告。
  - モジュール docstring: git 手順に「gitignore 対象（untracked）は staging から除外」を記載。
- 既存の tracked 対象（tsv 書き換え、tasks 移動・削除、verification ラン削除）は gitignore 外のため staging 対象として従来どおり処理される（`git add` で削除もステージング可能）。

## Verification

- `py -3.15 -m pytest maintenance/tests/ -v` → **53 passed in 4.06s**（新テスト 2 件含む）
- `py -3.10 -m pytest scripts/tests/ -v` → **423 passed in 9.33s**（既存環境確認・本タスク無関心）
  - 注: `py -3.15` での `scripts/tests/` 収集不能は pillow-avif 非導入（バックログ P3 #11 前提）のため、本タスク起因ではない
- 自己テスト（実リポジトリ）: `docs/ai/tmp/ki01_selftest` に git repo + `.gitignore`（`tmp/`）+ gitignore 対象ディレクトリ `docs/ai/tmp/old`（mtime 2 日前）+ tsv 作成
  - dry-run: `git_add: would stage 2 path(s) on --apply`
  - `--apply`: tsv 削除・rm（selftest 内では `kilo-safe-rmdir.cmd` 未配置で rm 失敗のみ）→ **`[git_add] . 1 path(s) staged`**（gitignore 対象 `docs/ai/tmp/old` は staging 除外、元の「pathspec did not match」失敗なし）
- 本リポジトリ `python maintenance/archive_memory_bank.py --apply` → no-op・exit 0
- 自己テストリポジトリはゴミ箱へ移動済み

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（KI-20261018-01）
- [x] `backlog.md` の完了項目を削除（該当なし・N/A）
