# RSS Feeds for Pokemon Category

**Date**: 2026-10-02

**Decision**: Add 4 RSS feeds (PokéCommunity Art Studio, PokeBeach News, PokemonBlog, PocketMonsters) for the pokemon category.

**Reason**: Reddit API is blocked, so RSS feeds provide a stable alternative for pokemon-related content. RSS feeds are publicly accessible and don't require authentication.

**Rejected Alternatives**:
- 公式 Pokémon API: トレンドデータではなくゲームデータのみを提供
- Twitter/X API: 有料プランが必要

**Impact**:
- `fetch_topics.py`: `RSS_FEEDS` に 4 フィード追加、`collect_rss_feeds()` でカテゴリごとにフィルタリング
