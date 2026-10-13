# RSS description の取得・活用（backlog P2 #1, #5 統合）

**Date**: 2026-10-10

**Decision**: `fetch_rss()` に description 抽出（RSS2.0: content:encoded→description / Atom: content→summary、300文字切り詰め）。`score_topics()` で title+description[:200] スコアリング、`_append_trending_topics()` で description[:100] スニペット注入。GameSpot/IGN を HTML→RSS パースへ。`STORY_INSPIRATION_THEMES` NameError 修正。

**Reason**: kemono_story で e621 除外後の残り候補が title のみで score=0-1 になり物語テーマに反映されない問題。description 取得で下流全フロー（スコアリング→スニペット注入）を改善。GameSpot/IGN は実測で正規 RSS 2.0。
