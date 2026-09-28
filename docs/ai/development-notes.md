# Development Notes

## 2026-09-29

### Completed
- Score-based sorting implemented for all topic categories
- TTL validation added with 24-hour default
- Documentation structure created (docs/ai/)

### Observations
- Reddit API blocking is a critical gap in trend collection
- Bluesky API integration planned as future improvement
- e621 content filtering needed for non-kemono prompts

### Dependencies Installed
- Pillow, pillow-avif-plugin
- google-genai
- gradio-client
- feedparser, beautifulsoup4, python-dotenv, requests

## 改善案（優先度付き）

### A. トレンド収集層（fetch_topics.py）

| 優先度 | 改善項目 | 内容 | 工数 |
|--------|----------|------|------|
| **高** | NSFW フィルタ | e621 収集時に `rating:explicit` または既知の NSFW タグを含む投稿をフィルタ。または分離して `nsfw` カテゴリに分類 | 小 |
| **中** | Bluesky 収集関数追加 | `collect_bluesky()` を新規追加。Bluesky AT Protocol の `app.bsky.feed.getPopularPost` または `app.bsky.graph.getSuggestedFeeds` を利用。カテゴリは `tech` / `kemono` に分類 | 中 |
| **低** | 部分キャッシュ | 各ソースごとに部分キャッシュを保存。一部ソースが失敗しても前回のデータで補完 | 大 |

### B. 記事生成層（generate_article.py）

| 優先度 | 改善項目 | 内容 | 工数 |
|--------|----------|------|------|
| **高** | カテゴリ厳格化 | `kemono_story` 系プロンプトには e621 の Safe 系タグのみを注入。技術記事には tech カテゴリのみを注入 | 小 |
| **中** | トレンド参照の Frontmatter 記録 | 注入したトレンドのソース/URL を Frontmatter の `references: [...]` に記録。記事生成後に「どのトレンドが参考されたか」を追跡可能に | 小 |
| **中** | スコアしきい値 | 低スコアトピックを自動的に除外するオプションを追加 | 小 |

### C. Bluesky API 追加時の設計

```python
# fetch_topics.py に追加する関数のスケルトン

BLUESKY_FEEDS = [
    {"handle": "some-tech-feed.bsky.social", "category": "tech"},
    {"handle": "some-kemono-feed.bsky.social", "category": "kemono"},
]

def collect_bluesky(limit_per_feed: int = 5) -> list[dict]:
    """Bluesky AT Protocol で人気投稿を取得"""
    # app.bsky.feed.getPopularPost や app.bsky.feed.getAuthorFeed を利用
    # Bluesky は認証不要で公開 API を提供（rate limit あり）
    ...
```

Bluesky は AT Protocol (JSON-RPC over HTTPS) なので、既存の `fetch_json()` パターンで実装可能。認証トークンなしでも `getPopularPost` エンドポイントは利用可能。

### D. 推奨実装優先度（全体）

| 優先度 | 改善 | 工数 | ステータス |
|--------|------|------|------------|
| **完了** | スコア順ソート + TTL 検証 | 小 | ✅ 完了 |
| **高** | NSFW フィルタ | 小 | 未実装 |
| **高** | カテゴリ厳格化 | 小 | 未実装 |
| **中** | Bluesky 収集関数追加 | 中 | 未実装 |
| **中** | トレンド参照の Frontmatter 記録 | 小 | 未実装 |
| **中** | スコアしきい値 | 小 | 未実装 |
| **低** | 部分キャッシュ機構 | 大 | 未実装 |
| **低** | Reddit 公式 OAuth 対応 | 大 | 未実装 |
