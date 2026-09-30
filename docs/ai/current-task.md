# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

AI Memory Bank 運用方針改訂

## Priority

P1

## Status

完了

## Objective

`AGENTS.md` と `docs/ai/` の運用方針を改訂し、長時間タスク実行時のコンテキスト復帰・状態管理・コミット整合性を強化する。

## Requirements

- `current-task.md` 追加
- Memory Bank更新タイミングを commit 前に変更
- 「1コミット=1ファイル」ルール撤廃
- `Long-running Agent Tasks` と `Recovery After Interruption` セクション追加
- `plans.md` の Active/Completed 分離
- `backlog.md` の優先度を P0/P1/P2 に変更
- `known-issues.md` に `Next action` フィールド追加
- `decisions.md` に `Rejected Alternatives` フィールド追加

## Modified Files

- `AGENTS.md`
- `docs/ai/plans.md`
- `docs/ai/backlog.md`
- `docs/ai/known-issues.md`
- `docs/ai/decisions.md`
- `docs/ai/current-task.md` (新規)

## Completed

- [x] `docs/ai/current-task.md` 新規作成
- [x] `AGENTS.md`: Memory Bankタイミング変更、1-fileルール撤廃、Long-running Agent Tasks + Recovery セクション追加
- [x] `plans.md`: Active Plans / Completed Plans を1級見出しで分離
- [x] `backlog.md`: 優先度を P0/P1/P2 に変更
- [x] `known-issues.md`: 各項目に `Next action` フィールド追加
- [x] `decisions.md`: 全28項目に `Rejected Alternatives` フィールド追加

## Pending

(なし)

## Verification

Build: 不要（ドキュメントのみ）
Test: 不要

## Next Action

git commit & push

## Notes

(なし)
