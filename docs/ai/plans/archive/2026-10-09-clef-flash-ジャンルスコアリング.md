# Clef-flash ジャンルスコアリング（backlog #4）

**Date**: 2026-10-09
**Status**: 完了

Cloudflare Workers AI の判断特化モデル `@cf/cloudflare/clef-flash` で、文字列の複数ジャンル（sf/fantasy/cyberpunk/action、設定変更可能・最大64問）への関連度を 0-100 整数スコアで取得する。独立 CLI `scripts/genre_score.py`（env `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN`、5xx のみ限定的に再試行、4xx・無料枠超過は再試行せず、SHA256キャッシュ `data/genre_scores/cache.json`、`--no-cache` フラグ）+ 全モック単体テスト61件 + `workflow_dispatch` のみ `.github/workflows/genre-score.yml`。`generate_article.py` 組み込みはスコープ外。2段構成（LLM→Clef-flash）は backlog P3 #1 に追記。実 API スモーク: "攻殻機動隊" → sf:84, fantasy:3, cyberpunk:86, action:47（0.68s）。pytest 261通過。詳細: `docs/ai/tasks/2026-10-09-clef-flash-genre-score.md`
