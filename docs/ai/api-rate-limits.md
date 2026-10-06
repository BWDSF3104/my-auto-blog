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
| HuggingFace ZeroGPU (blume/kemono-image-api) | 3.5 分/日（無料枠） | なし | `@spaces.GPU(duration=20)` で 1 リクエスト 20 秒予約。実質 1 日約 10 リクエスト。Space 停止時は起動に数分要する。残り確認: \`hf spaces zero-gpu quota\` |
| Pollinations.ai | なし | なし | API キー不要、クォータ無制限。Flux モデル使用 |
