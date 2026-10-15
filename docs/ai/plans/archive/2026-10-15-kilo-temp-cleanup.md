# Temp\kilo クリーンアップ + スクラッチ置き場を docs/ai/tmp/ へ転用

**Date**: 2026-10-15
**Status**: 進行中

`AGENTS.md` の scratch 指定を `C:\Users\fujim\AppData\Local\Temp\kilo\` から `docs/ai/tmp/`（gitignore 済み + `archive_memory_bank.py` でタスク開始時全削除の機構が既存）へ転用。ライブ参照 3 箇所（`AGENTS.md` / `docs/ai/manual-article-workflow.md` / `scripts/tests/equivalence_check.py`）を一括更新。%TEMP%\kilo の初回クリーンアップ（2,796 ファイル 105.7MB 削除候補・当日ファイル 5 件保持）はインベントリ確認 → ユーザー承認 → `Remove-Item` の個別フローで実施。新規スクリプトは作成しない（ユーザー指示）。
