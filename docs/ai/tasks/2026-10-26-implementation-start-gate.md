# 実装開始ゲート ルール追加（AGENTS.md）

**Status**: 完了
**Date**: 2026-10-26
**Next Action**: AGENTS.md へ「実装開始ゲート」セクション追加 / 決定的判断記録 / 完了処理・commit

## 意図 / 背景

ユーザー指示: 「実装開始の明示的な指示を受けるまで決して実装・ファイル変更はしないルール（タスクファイルなどの記録除外、設計〜実装を一任した場合除外）を AGENTS.md に追加する」。設計先行フロー（`decisions/` への事前記録、commit/push の事前承認前提）は事実上は存在したが、agent が設計合意前に単独で実装へ進むリスクを排除する明示的なルールが欠けていた。

## 調査結果 / 変更内容

- 現状ルール確認（AGENTS.md / memory-bank-guide.md / .kilo/command/*）: 「実装着手のタイミング」を規定するゲートは欠けており、新規セクションが必要と判断
- 位置: トップレベル `## 実装開始ゲート`（`## 言語` の後）。代替案 `## ワークフロー` 内は可視性が低いため非推奨
- 文言: 4 項目（禁止 / 記録除外の一覧 / 一任例外 / 明示的開始指示の定義）
- 変更ファイル: `AGENTS.md`、`docs/ai/decisions/2026-10-26-implementation-start-gate.md`、`docs/ai/tasks/2026-10-26-implementation-start-gate.md`、`current-task.tsv`（旧タスク `2026-10-24-task-create-single-path` は Status 進行中 → 保留）
- 旧タスクの残作業（禁止条項の 3 ファイル追加）は保留として残した（後で再開可）

## Verification

- 2026-10-26 commit 前: `git diff AGENTS.md` で「実装開始ゲート」セクションのみが追加されることを確認
- docs/ai/ と AGENTS.md のみ変更 → pytest / build 不要（AGENTS.md の例外項目）
- commit 前 `git pull`: fast-forward 成功・衝突なし（リモート 4 コミットは data/・public/images/・src/content/posts のみで、変更パスと重複なし）
- 2 コミット: chore（旧タスク記録）+ feat（本ルール追加）
- 残置未コミット変更: `maintenance/restart-vscode.bat`、`maintenance/vscode_graceful_restart.py`、`public/search-index.json`（前回セッションの遺残で、本タスク範囲外）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
