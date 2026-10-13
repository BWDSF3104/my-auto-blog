# トレンドソース品質（ANN whitelist + Crunchyroll一時無効化 + TTL誤検知修正）

**Date**: 2026-10-10

**Decision**: ANN に URL whitelist（記事パス5種+日付形式）を導入しナビゴミを排除。Crunchyroll を一時無効化（静的 HTML に記事0件）。`_check_per_source_ttl()` で他カテゴリ専属 source を `expired=False`（自動 fetch 不トリガー）。

**Reason**: ANN のナビ・フッター URL は開放集合で blocklist では追えないが記事パスは閉集合。Crunchyroll は JS 描画で静的 HTML に記事なし。TTL は source 横断共有のため他カテゴリ専属が毎回トリガーしていた。
