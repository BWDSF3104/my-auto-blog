# `plans/` ディレクトリ廃止（タスクファイルへの統合）

**Date**: 2026-10-15

**Decision**: `docs/ai/plans/` を廃止する。新規タスクはタスク開始前（初回コード変更前）に `docs/ai/tasks/YYYY-MM-DD-short-name.md` を作成し、plan の役割（意図・背景・Backlog 参照）をタスクファイルに統合する。既存 `plans/`・`plans/archive/` のファイルは歴史記録として維持し、新規ファイルは作成しない。

**Reason**: `plans/` と `tasks/` は常に 1:1 で同名共存し、意図・背景の内容が重複していた。ステータス機構も不一致（plans=フォルダ判定・tasks=Status フィールド）で、作成タイミング「開始前 / 開始時」は実行上同一瞬間だった（2026-10-15-inspiration-source-links タスクで task 作成が完了時まで遅れた逸脱の構造的起因）。1 ファイル化により「着手時の簿記が一部のみ実行される」失敗モードが構造的に消滅する。

**Rejected Alternatives**:

- 案 B（両方維持し役割再定義: plan=意思決定、task=実行記録）: 「作業開始前の計画書」ケースは本プロジェクトでほぼ存在しない（ユーザー依頼起点の ad-hoc 作業が主体）ため、2 ファイル維持の根拠が薄い
- 案 C（task 主軸＋複数タスク計画のみ plans/ 残置）: plans/ を作る境界判断が新たな曖昧さ源となる

**Impact**: `memory-bank-guide.md`・`AGENTS.md`・`workflows.md`・`architecture.md` を改訂。`maintenance/archive_memory_bank.py` は `plans/` を参照しないため変更不要。既存 `plans/` ファイルは維持。
