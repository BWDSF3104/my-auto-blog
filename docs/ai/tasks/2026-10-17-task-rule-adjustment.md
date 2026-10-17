# ルール調整（非必須問題は記録して継続 / タスク開始タイミング / dry-run 不要化）

**Status**: 完了
**Date**: 2026-10-17
**Next Action**: 3 ルールを AGENTS.md / memory-bank-guide.md / task_manager.py / コマンド / テストへ反映

## 意図 / 背景

ユーザー指示の 3 ルールを精査して反映する。

1. 非必須問題の記録と継続: タスク実行中にタスク完了に必須でない問題を見つけたら `known-issues/` に記録してタスクを先に進める（枝打ちで修復しない）。
2. タスク開始タイミング: 初回コード変更前ではなく**調査開始段階**で `/task-add` を実行する。
3. dry-run 不要化: タスク開始/終了（`task_manager.py` add/end）の dry-run 確認→`--apply` の 2 手順を廃止し、**既定で反映**（`--dry-run` でプレビューのみ）。

対象: `AGENTS.md` / `docs/ai/memory-bank-guide.md` / `maintenance/task_manager.py` / `maintenance/tests/test_task_manager.py` / `.kilo/command/task-add.md` / `task-end.md`。`archive_memory_bank.py`（破壊的バッチ）は対象外で dry-run 既定のまま。

## 調査結果 / 変更内容

### 精査ポイント

- ルール2（調査開始段階でのタスク開始）: 従来文言「初回コード変更の前」は実装直前までタスクファイルが存在しないため、調査結果の記録・中断復帰が弱い。調査開始段階への前倒しで両者を改善する。文言のみの変更で実装影響なし。
- ルール1（非必須問題の記録と継続）: 既存の「重要な未解決の問題は known-issues/ に記録」を補完する。branch 打ち防止（scope creep 抑制）と blocker の除外条件を明記して誤用を防ぐ。
- ルール3（dry-run 不要化）: 対象は `task_manager.py` の add/end のみ。`archive_memory_bank.py`（tmp/verification 削除等の破壊的バッチ）は指示範囲外のため dry-run 既定を維持。CLI は `--apply`（opt-in）から `--dry-run`（opt-out）へ反転し、apply 既定にする。`--no-git-add`・staging・レポート機構は不変。

### 変更ファイル

| ファイル | 変更 |
|---------|------|
| `AGENTS.md` | 「タスク開始時（調査開始段階）」へ見出し・文言変更 / 「タスク実行中に発見した非必須問題」セクション新設 / ワークフロー箇条書きを「既定で反映・`--dry-run`」へ更新 |
| `docs/ai/memory-bank-guide.md` | `tasks/*.md` 行の開始タイミングを「調査開始段階」へ / 長時間タスク箇条書きに非必須問題ルールの bullet を追加 |
| `maintenance/task_manager.py` | `--apply` → `--dry-run`（apply 既定）。docstring・help 文言・出力メッセージ（`planned (dry-run: no changes written)` / `would stage N path(s) (dry-run)`）を更新 |
| `maintenance/tests/test_task_manager.py` | `apply=` kwarg → `dry_run=`（既定 False = apply）。22 件すべてパス |
| `.kilo/command/task-add.md` / `task-end.md` | 手順 2〜3 の「dry-run → --apply」2 段階を単一実行（既定反映）へ集約し再番号付け |

## Verification

- 2026-10-17: `pytest maintenance/tests/ -v` → 45 passed in 1.07s（archive_memory_bank 23 + task_manager 22）。`--dry-run` 反転後も全テストパス
- 2026-10-17: `python maintenance/task_manager.py add --slug smoke-dry-run --title "スモーク" --dry-run` → `planned (dry-run: no changes written)` / `would stage 2 path(s) (dry-run)`。ファイル未作成を確認（書き込みなし）
- 2026-10-17: `python maintenance/task_manager.py end --task task-rule-adjustment --dry-run` → dry-run レポート正常（Status 変更プレビュー・未チェック項目列挙・git 差分レポート）。書き込みなし
- 2026-10-17: `grep --apply`（*.md）→ 残存はすべて `archive_memory_bank.py`（対象外・dry-run 維持）または過去タスクファイルの記録のみ。`task_manager.py` 参照の `--apply` 残留なし

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
