# fetch_topics.py の CRITICAL バグ

**Date**: 2026-09-30
**Status**: 解決済

静的監査で発見した 5 件の CRITICAL バグを修正。テスト85件全件通過、ビルド成功を確認。

- **C-1** `fetch_topics.py:L276`: `isinstance(post.get("score"), int)` → `(int, float)` に変更。e621 API が float スコアを返す場合、int チェックのみではスコアが `None` にフォールバックし、高スコア投稿が失われていた。
- **C-2** `fetch_topics.py:L499-503`: TTL merge ロジックが逆。収集したソースに `now.isoformat()` を割り当て、未収集ソースが前の `fetched_at` を継承するよう修正。前実装は収集したソースのタイムスタンプを消去し、未収集ソースに `now()` を設定していた（TTLが常にリセットされるバグ）。
- **C1** `generate_article.py:L915`: カテゴリ不一致のソースを `expired[src_name] = False`（有効）としてマーク。`True`（期限切れ）に修正。カテゴリ不足のソースが再取得されなかった。
- **C2** `generate_article.py:L862-863`: `except Exception: break` の bare except が API 一時障害時にループを早期終了。`APIError` ハンドラーと同じリトライロジックに置換。
- **C3** `generate_article.py:L1015`: `_check_topics_ttl()` の戻り値（期限切れ辞書）を破棄。変数にキャプチャしてログ出力に接続。
