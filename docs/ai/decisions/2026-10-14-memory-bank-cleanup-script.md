# Memory Bank バッチクリーンアップスクリプトの置き場・形式・判定基準

**Date**: 2026-10-14

**Decision**: バッチクリーンアップスクリプトは `maintenance/archive_memory_bank.py`（新規トップレベル `maintenance/` = 開発用ツール置き場）に Python（標準ライブラリのみ）で実装する。テストは `maintenance/tests/`。tasks/ のアーカイブ判定は **mtime（最終更新）から 14 日経過**（ファイル名の作成日方式は不採用）。verification/ の「直近 2 ラン」は **mtime 順**（同値は名順）。

**Reason**: `scripts/` は本番パイプラインの置き場であり（`fetch_topics.py` → `generate_article.py`、`npm run build` が `generate-search-index.js` を参照、`hf-space/` が HF Space デプロイ元）、非パイプラインのメンテナンストールを混入させるのは不適切（ユーザー判断）。`maintenance/` は「開発用ツール置き場」としてアーキテクチャ（`AGENTS.md` Project Structure・`architecture.md`）に明示できる。判定基準は「最後に触ってから古い」がアーカイブの意図に最も近く、mtime 方式の失敗モードは「アーカイブ遅延」のみの安全側（進行中ファイルは `current-task.tsv` 参照で別途保護）。

**Rejected Alternatives**:
- `scripts/archive_memory_bank.py`: 本番パイプライン置き場に非パイプラインツールを混入（ユーザー否決）。
- `scripts/maintenance/`: パイプライン領域内という問題が残る。
- `.kilo/scripts/`: Kilo 設定・削除検証スクリプト（`safe-*.ps1`）の置き場。Python + テストスイートは不適。

**Impact**:
- `AGENTS.md`: Project Structure に `maintenance/`（開発用ツール）を追加。Code Verification は `pytest scripts/tests/ -v` を標準とし、`maintenance/tests/` は `maintenance/` 変更時のみ実行（ユーザー判断: メンテナンストールは毎回テスト不要）
- `docs/ai/architecture.md`: Development Tools セクションを新規追加
- `README.md`: 構造ツリーに `maintenance/` を追加
- `docs/ai/memory-bank-guide.md`: バッチクリーンアップ表をスクリプト実行への参照に更新。tasks/ 基準を「ファイル名日付」から「mtime（最終更新）」へ更新
- `scripts/` のワンオフ 8 ファイル（`fix_*`・`_check_*` 等）の `maintenance/` へ移動は別タスクとして分離: `docs/ai/tasks/2026-10-14-move-oneoff-scripts.md`（pending）。`scripts/hf-space/` は HF Space ソース（本番コンポーネント）のため `scripts/` に留置
