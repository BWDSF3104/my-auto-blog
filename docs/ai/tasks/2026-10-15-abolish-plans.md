# `plans/` ディレクトリ廃止（タスクファイルへの統合）

**Status**: 完了
**Date**: 2026-10-15
**Backlog**: —（該当なし）

## 意図・背景

`plans/` と `tasks/` の使い分けが曖昧だった（1:1 同名共存、意図・背景の内容重複、フォルダ判定と Status フィールドの 2 系統ステータス機構、作成タイミング「開始前 / 開始時」の実質同一）。ユーザー確認のもと案 A を採用: `plans/` を廃止し、旧 plan の作成タイミング（タスク開始前・初回コード変更前）にタスクファイルを作成する運用に変更。plan の役割（意図・背景・Backlog 参照）をタスクファイルへ統合する。

## 変更内容

- `memory-bank-guide.md`: ファイル一覧の `plans/` 行を削除（運用ルールに廃止注記を残さない）・`tasks/*.md` の作成タイミングを「タスク開始前」へ変更＋テンプレートに `**Backlog**` フィールド追加・テンプレート・命名規則・アーカイブルール・folder=status・長時間タスク手順から plans 削除
- `AGENTS.md`: 「AI Memory Bank」に「タスク開始時（初回コード変更前）2 ステップゲート」追加
- `workflows.md`: Commit Checklist の plans/ mv 項目を「タスクファイル Status 更新＋tsv 行削除」に置換
- `architecture.md`: Memory Bank 構成記述から plans 削除
- `decisions/2026-10-15-abolish-plans-directory.md`: 新規作成

既存 `plans/`・`plans/archive/` のファイルは歴史記録として維持（新規作成なし・編集なし）。

## Verification

- `grep plans/`（docs/ai・AGENTS.md・.kilo・maintenance）: 現行規則ファイル（memory-bank-guide.md / AGENTS.md / workflows.md / architecture.md）は 0 件。残りヒットは全て歴史記録（`decisions/2026-10-14-folder-status-archiving.md`、`tasks/2026-10-0*`〜`2026-10-15` の完了タスク）と本変更の決定記録（`decisions/2026-10-15-abolish-plans-directory.md`）のみ ✅
- `docs/ai/`・`AGENTS.md` のみの変更のため pytest / build 不要（AGENTS.md コード検証の例外）✅
- 所要: 約 45 分（2026-10-15 08:22→09:10 UTC）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
