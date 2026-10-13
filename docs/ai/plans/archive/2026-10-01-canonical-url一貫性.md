# canonical URL一貫性

**Date**: 2026-10-01
**Status**: 完了

slug変更時の301リダイレクト実装。`data/slug-redirects.json` で旧→新slugマッピングを記録。`generate_article.py` にslug変更検出・自動記録ロジック追加。`[...slug].astro` の `getStaticPaths` にリダイレクトルートを追加してAstroレベルの301リダイレクトを実装。sitemap整合性確認済み。テスト119件全件通過、ビルド成功 (90ページ)

---
*以下は 2026-10-06 に plans.md からアーカイブ*
