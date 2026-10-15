# tmp/ クリーンの N 日保持

**Date**: 2026-10-15
**Backlog**: P3 #12（N 日保持部分。日付サブフォルダは対象外）

`tmp/` のバッチクリーンアップを「全削除」から「最更新 mtime が N 日（既定 7、`--tmp-retention-days` で変更）を超えるエントリを削除」に変更。ディレクトリは内部の最更新 mtime で判定（古い親ディレクトリに新ファイルが追加されても誤削除しない）。AGENTS.md と memory-bank-guide.md のルール文言を挙動に合わせて更新する。

関連タスクファイル: `tasks/2026-10-15-tmp-retention.md`
