# 既知問題リスト

進行中の問題のみを記録。解決済は `known-issues-archive.md` に移動する。

## ソースコード監査で発見された潜在的なバグ (静的解析 2026-09-30)

**ステータス**: 一部解決済み (5/9 修正完了)

**発見方法**: テスト実行によるものではなく、ソースコードの静的解析（手動監査）で発見。テストスクリプト（85/85全件通過）は正常に動作している。

**残候補リスト**:
- **[Low]** `_auto_fetch_topics` の相対パス: `scripts/fetch_topics.py` が CWD 変更時に失敗する可能性
- **[Low]** `collect_bluesky` の URI 解析: 特定のコロン区切り形式を前提
- **[Low]** `_is_nsfw_post`: `non_consecutive` メタタグを誤って NSFW として扱う可能性

**Next action**: 残りの Low 項目は実装影響が小さいため保留。

## Reddit API ブロッキング (2026-09-29)

**ステータス**: 進行中

**問題**: Reddit が `.json` エンドポイントを HTTP 403 でブロック。`old.reddit.com` へのフォールバックも 404 を返す。

**影響**: Reddit からの投稿収集が 0件。トレンドデータから kemono/tech 系の Reddit コンテンツが欠落。

**回避策**: 現在なし。Reddit OAuth 導入または代替データソースの検討が必要。

**Next action**: backlog P0 の「Reddit 代替ソースの追加」を実施し、HackerNews RSS または TechCrunch RSS を追加する。

**関連**: Bluesky API を代替トレンドソースとして検討中。

## 既存記事のアフィリエイトリンクがmarkdown形式 (2026-09-30)

**ステータス**: 保留

**問題**: `inject_affiliate_links()` の修正により新規記事はHTML `<a>` タグを生成するが、既存の記事ファイル（`src/content/posts/` 内のmdファイル）は依然として `[text](long_url)` のmarkdownリンク形式。長いURLが丸出し。

**影響**: 既存記事のフッターで長いアフィリエイトURLが可読状態。

**Next action**: 必要に応じて一括置換スクリプトを実装する。
