# CI ワークフローのキャッシュファイルパス修正と SEO 残タスク

**Status:** 完了
**Date:** 2026-10-01
**Commit:** 29e5120, a9f00e2

## Objective

`deploy.yml` の `git add data/latest_topics.json` を `git add data/topics/` へ更新。sitemap.xml に主要タグページ追加。

## Verification

- pytest: 96 passed
- npm run build: 86 pages
