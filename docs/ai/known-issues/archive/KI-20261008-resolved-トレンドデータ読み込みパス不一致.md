# トレンドデータ読み込みパス不一致

**Date**: 2026-10-08
**Status**: 解決済

`generate_article.py` の `PROJECT_DIR` が `scripts/` 自身を指していたため、`TOPICS_DIR = scripts/data/topics/`（存在しない）となり、`fetch_topics.py` の出力先 `data/topics/`（リポジトリ直下）と不一致。2026-10-02 のコミット `2b4a815`（静的解析修正「相対パスを絶対パス化」）で退行。以降の全記事生成でトレンド注入がサイレント無効化（`data/trend_usage/` ログに `skipped: "file_not_found"`）されていた。楽天API商品リンク連携の調査中に発見し、別タスクとして修正（`docs/ai/tasks/2026-10-08-topics-path-bug.md`）。`PROJECT_DIR` をリポジトリ直下に変更し、`fetch_topics.py` 起動パスを `scripts/` 補正。回帰テスト3件追加、pytest 164通過。
