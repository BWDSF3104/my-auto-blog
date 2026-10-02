# Reddit 代替ソースの追加

**Status:** 調査中 - 中断
**Priority:** P0
**Date:** 2026-10-01

## Objective

Reddit API がブロックされているため、代替のトレンドデータソースを追加してトレンドデータの多様性を確保する。

## Investigation Results

### 現在のデータ収集状況 (2026-10-01_202015.json)

- 総トピック数: 14件
- 動作中のソース: e621, GitHub のみ
- 停止中のソース: Reddit, HackerNews, RSS, Bluesky
- カテゴリ別: kemono 7件, pokemon 7件, tech 0件

### Reddit ブロッキングの詳細

- `www.reddit.com/r/{sub}/hot.json` → HTTP 403
- `old.reddit.com/r/{sub}/hot.json` → HTTP 404
- User-Agent ヘッダの変更では回避不可
- 影響カテゴリ: kemono (r/kemono, r/furry, r/furry_irl), pokemon (r/pokemon), tech (r/localllama, r/MachineLearning)

### 代替ソースの候補

1. **HackerNews RSS**: 既に Firebase API で実装済みだが現在は動作停止中。RSS フィード (`https://hnrss.org/frontpage`) に切り替え可能
2. **TechCrunch RSS**: `https://techcrunch.com/feed/` - tech カテゴリに適合
3. **Lobsters RSS**: `https://lobste.rs/rss` - tech カテゴリに適合
4. **kemono/pokemon RSS**: 専用 RSS フィードの探索が必要

### 計画

1. `fetch_topics.py` に新しい RSS フィードを追加
2. HackerNews Firebase API が停止している場合、RSS にフォールバック
3. kemono/pokemon カテゴリの代替ソースを探索

## Next Action

代替 RSS フィードの可用性を確認し、`fetch_topics.py` に追加する

## Verification

なし (調査段階)
