# tmp/ クリーンの N 日保持方針

**Date**: 2026-10-15

**Decision**: バッチクリーンアップ（`maintenance/archive_memory_bank.py`）の `docs/ai/tmp/` 処理を「全削除」から「最更新 mtime が N 日（既定 7、`--tmp-retention-days` で変更可）を超えるエントリを削除」に変更。ディレクトリは内部を再帰走査した最更新 mtime で判定する。

**Reason**: スクラッチが複数日にまたがる運用（調査スクリプト、equivalence run）になり、タスク開始時の全削除で進行中作業が失われるため。mtime 基準の保持は運用コストゼロで直近のスクラッチを保つ。ディレクトリの親 mtime だけでは判定不能（サブディレクトリ内部にファイルを追加しても親ディレクトリの mtime は更新されない）ため再帰走査が必要。

**Rejected Alternatives**:

- タスク別日付サブフォルダ（backlog P3 #12）: ルール変更 + ユーザー側の運用変更を要する。mtime 保持で十分のため見送り（backlog に残置）
- トップレベルディレクトリ mtime のみの判定: 古い親ディレクトリに新ファイルが追加されている場合の誤削除リスク

**Impact**: `archive_memory_bank.py`（`TMP_RETENTION_DAYS=7` 定数 + `--tmp-retention-days` CLI オプション）、`maintenance/tests/test_archive_memory_bank.py`、AGENTS.md コマンド実行ルール、`memory-bank-guide.md`（ファイル一覧・バッチクリーンアップ表）、`backlog.md` P3 #12。
