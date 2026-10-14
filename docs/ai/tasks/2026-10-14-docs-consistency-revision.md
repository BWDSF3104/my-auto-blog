# 2026-10-14: docs/ai 整合性整備（current-task 冒頭文言 + 言語統一 + 旧ファイル参照修正）

**Status**: 完了
**Next Action**: なし

## 概要

memory-bank 整備（`2026-10-14-memory-bank-guide-revision.md`）の延長で、`docs/ai/` のドキュメントに発見した整合性問題をまとめて修正する。3項目: ①`current-task.md` 冒頭の誤解を招く文言、②言語整合性（英語残留）、③旧ファイル名参照の実体なし化。

## 項目1: current-task.md 冒頭文言

### 問題点

- 5行目「完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される」→ タスクファイルが**完了後に**作成されると誤解させる（ルールは**開始時**作成）
- 3行目「参照を記録する」→ 「1タスク1行・詳細を書かない」制約が明示されていない（2026-10-14 の current-task 記載誤りの再発防止ポイント）

### 変更予定の前後

**変更前**
```markdown
# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。
```

**変更後（2026-10-14 適用済み）**
```markdown
# Current Task

Agentの現在進行中タスクの**参照**を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

**1タスク1行**（タスクファイルパス + ステータス + Next Action）のみ。
詳細（変更内容・検証結果等）はここに書かず、`docs/ai/tasks/` の個別タスクファイル（タスク開始時に作成）へ記録する。
```

## 項目2: 言語整合性

### 調査結果（2026-10-14）

| ファイル | 状態 | 対応 |
|---------|------|------|
| `memory-bank-guide.md`・`debugging.md`・`image-analysis.md`・`manual-article-workflow.md`・`workflow-test-procedure.md`・`image-prompt-*.md` | 日本語 ✅ | なし |
| `api-rate-limits.md`・`backlog.md` | 本文日本語、H1 タイトルのみ英語（軽微） | 任意で H1 日本語化 |
| `workflows.md` | 英語 H2 3件（`## Git Workflow` / `## Commit Checklist` / `## Deploy Verification`）+ 14-15行目の英語文2行 | 日本語化 |
| `architecture.md` | **全132行英語**（最大的不整合） | **見送り**（2026-10-14 ユーザー判断: 今回は実施しない。別タスクで実施する場合に参照） |
| `plans/`・`decisions/`・`known-issues/`・`tasks/` の既存英語エントリ | 英語 | AGENTS.md により**そのまま維持** |

## 項目3: 旧ファイル参照

### 構成移行の確認（2026-10-14 実施）

- 旧単一ファイル `plans.md` / `decisions.md` / `known-issues.md` は `docs/ai/` に**存在しない**（トップレベル 12 ファイル全て新形式）
- 移行先ディレクトリは実体あり: `plans/`（9 + archive）/ `decisions/`（9 + archive）/ `known-issues/`（2 + archive）/ `tasks/`（移行コミット `979d5e3`）
- `AGENTS.md`: 旧参照なし

### 現行ドキュメントの旧参照（修正対象）

| 場所 | 参照 | 正（実体確認済） | 備考 |
|------|------|------|------|
| `workflows.md:24` | `plans.md` の「完了した計画」 | `plans/` の該当ファイル `Status` = `完了` | **旧ルールの文言も**現在と不一致 |
| `workflows.md:25` | `known-issues.md` | `known-issues/` | |
| `workflows.md:26` | `known-issues.md` の Archive へ移動 | `known-issues/` の該当ファイル `Status` = `解決済` | **旧ルールの文言も**不一致（アーカイブは新規タスク開始時のみ・`mv` のみ） |
| `backlog.md:11` | `decisions.md`（Giscus 選定理由） | `decisions/2026-10-11-giscus-comments.md` | |
| `backlog.md:24` | `known-issues.md`（merge 構造ドリフト） | `known-issues/KI-20261010-01-merge-drift.md` | |

### 過去の記録（変更しない方針）

- **完了済みタスクファイル**（`tasks/2026-10-05`〜`2026-10-13` の 12 ファイル・約 19 参照: `plans.md`/`decisions.md`/`known-issues.md`）— 記録時点では正確な参照（当時旧形式が存在）。アーカイブ編集禁止原則・既存エントリ維持方針と整合のため変更しない
- **アーカイブファイル**（`plans/archive/`・`decisions/archive/`・`known-issues/archive/` の旧参照）— 歴史記録のため変更しない

## 変更内容

- `docs/ai/current-task.md:1-5`: 冒頭文言を適用済み（2026-10-14）—「**参照**」強調・「1タスク1行」制約と詳細の書込先（`tasks/` 個別ファイル・タスク開始時作成）を明示（項目1）
- `docs/ai/workflows.md:24-26`: 旧単一ファイル参照（`plans.md` / `known-issues.md`）+ 旧ルール文言を、現行ディレクトリ方式（`plans/`・`known-issues/` の該当ファイル `Status` 更新ルール）に書き換え（項目3）
- `docs/ai/backlog.md:11`: `decisions.md` → `decisions/2026-10-11-giscus-comments.md`（項目3）
- `docs/ai/backlog.md:24`: `known-issues.md` → `known-issues/KI-20261010-01-merge-drift.md`（項目3）
- 項目2（言語統一）: **見送り**（2026-10-14 ユーザー判断）

## 備考

- 適用後の検証は不要（docs/ai のみ変更 → pytest/build 不要）。参照破損確認は旧見出し名の grep で実施
- `plans/archive/` の過去記録にある旧英語セクション名は歴史記録のため変更しない
