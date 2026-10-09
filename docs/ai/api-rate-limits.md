# API Rate Limits

確認済みのレート制限情報（2026-10-02 実測）

| ソース | レート制限 | ヘッダー | 備考 |
|--------|-----------|---------|------|
| e621 | 2 req/s（IPベース、超過時503） | なし | 推奨 1 req/s 持続 |
| GitHub Search | 10 req/窓（未認証） | X-RateLimit-* | 認証で 30 req/分 |
| Reddit | 10 req/s | Retry-After | 現在 403 規制中 |
| Hacker News | なし | なし | Firebase 公開DB |
| RSS (Zenn/Qiita/PokéCommunity) | なし | なし | 公開フィード |
| Kemono API | 不明 | なし | express-rate-limit 依存あり |
| Bluesky | 不明 | なし | 公開検索APIは501 |
| HuggingFace ZeroGPU (blume/kemono-image-api) | 3.5 分/日（無料枠） | なし | `@spaces.GPU(duration=20)` はタイムアウト予約。実稼働時間分のみ消費（初回9秒、ウォーム2秒）。実質 1 日約 101 リクエスト。Space 停止時は起動に数分要する。残り確認: \`hf spaces zero-gpu quota\` |
| Pollinations.ai | なし | なし | API キー不要、クォータ無制限。Flux モデル使用 |
| 楽天市場API (IchibaItem/Search) | 1 req/s（application_id ごと、公式） | なし（429 body に待機秒数記載） | **公式確認済み (2026-10-09)**: 公式FAQ「各APIの利用制限を教えてください」= 1つの application_id につき**1秒に1回以下**。緩和申請不可（「APIリクエスト制限緩和について」）。制限超過が**一定期間継続**すると application_id 停止の可能性がある（瞬間超過では即停止しない）。429 `too_many_requests`（実測 body: "Rate limit is exceeded. Try again in 1 seconds."）。API仕様書注記: 「同一URLへの短期間の多数アクセス時は一定期間無応答になる場合あり」。旧ドキュメントの 1 日上限（個人型 500回 / Webアプリケーション型 10万回）は現行FAQでは明記されていない。実装: `_rakuten_search` で呼び出し間隔1.5秒＋429リトライ（2/4/6秒）＋30日キャッシュ |
