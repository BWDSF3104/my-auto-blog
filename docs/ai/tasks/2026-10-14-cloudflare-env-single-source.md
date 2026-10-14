# 2026-10-14: Cloudflare Pages 移行準備: ドメイン/base パスの env 単一ソース化

**Status**: 完了（2026-10-14）
**Next Action**: なし

## 概要

GitHub Pages のドメイン/base パスをハードコードから「env 変数（デフォルト=現在値）」へ単一ソース化し、CF Pages 移行時に値の差し替えだけで完結するようするリファクタ。挙動は不変（env 未設定なら従来出力とバイト単位同一）。

## 変更内容

- `astro.config.mjs`: `site: process.env.SITE_ORIGIN || 'https://BWDSF3104.github.io'` / `base: process.env.SITE_BASE_PATH || '/my-auto-blog'`
- `scripts/article/config.py`: `RAKUTEN_ORIGIN` / `RAKUTEN_REFERER` / `BASE_URL`（= `SITE_BASE_PATH`）を `os.environ.get(...) or <現在値>` で env 化（空文字列ガード）
- `.github/workflows/deploy.yml`: generate step に `RAKUTEN_ORIGIN`/`RAKUTEN_REFERER`/`SITE_BASE_PATH`（`vars.*`）、Build step に `SITE_ORIGIN`/`SITE_BASE_PATH`（`vars.*`）を `env:` 追加
- `.github/workflows/deploy-only.yml`: Build step に `SITE_ORIGIN`/`SITE_BASE_PATH`（`vars.*`）を `env:` 追加
- `src/layouts/Layout.astro`: **削除**（未使用。全ページが独自 `<html>`/`<head>` を持ち import 元 0 件、中身 Plausible スクリプトはデッドコード）
- `.env`: **secrets のみに維持**。公開変数 4 件は「コードのデフォルト値と同一」のため `.env` に置かず、コードデフォルト + GitHub Actions variables に依存（混在回避）
- `public/search-index.json`: 検証用 `npm run build`（= search-index 生成 + astro build）で 2026-10-13 記事の反映が追記された副産物

## URL 生成の派生経路（移行時に env 差し替えで自動追従）

- HTML リンク / canonical / `<link>`: astro `site`/`base` config（env 化済み）
- `rss.xml` / `sitemap.xml`: `context.site`（= `site` config）→ `new URL()` で host が小文字正規化され `https://bwdsf3104.github.io/my-auto-blog/` になる。line 17/16 の `new URL('https://BWDSF3104.github.io/my-auto-blog/')` は `context.site` が falsy 時の到達不能フォールバック（`site` は常時設定されるため未使用）
- 生成記事内の内部リンク・楽天カード: Python `BASE_URL` / `RAKUTEN_ORIGIN` / `RAKUTEN_REFERER`（env 化済み）

## 変更しない対象

- `src/pages/rss.xml.ts:17` / `sitemap.xml.ts:16`: 到達不能なフォールバック文言（`context.site` は常時設定される）
- `about.astro:46,61`: 説明文
- `docs/ai/manual-article-workflow.md:29,36`: 画像パスのドキュメント（CF Pages 移行時に文言更新）

## GitHub Actions variables（登録済み）

初回 `gh variable set` は fine-grained PAT の Variables 権限不足で `HTTP 403`。2026-10-14 に PAT へ Actions: Read and write variables 権限を付与し、`gh variable set` で 4 件登録済み（`gh variable list` で確認）。未登録でもコードデフォルト（空文字列→falsy→フォールバック）でフローは壊れない。

- `SITE_ORIGIN` = `https://BWDSF3104.github.io`
- `SITE_BASE_PATH` = `/my-auto-blog`
- `RAKUTEN_ORIGIN` = `https://bwdsf3104.github.io`
- `RAKUTEN_REFERER` = `https://bwdsf3104.github.io/my-auto-blog/`

## Verification

- `python -m pytest scripts/tests/ -v` → **391 passed** (8.00s)
- `npm run build` → **142 page(s) built** (10.02s)
- 出力 URL 不変確認: `dist/rss.xml`・`dist/sitemap.xml`・`dist/index.html` とも `https://bwdsf3104.github.io/my-auto-blog/`（base path `/my-auto-blog` 適用）。env 未設定時にデフォルトが効き、従来出力と同一

## 備考

- CF Pages 移行時: 上記 4 件を CF の値に差し替え（workflow の `env:` は `vars.*` 参照のまま）。`rss.xml.ts`/`sitemap.xml.ts` の到達不能フォールバック文言、`docs/ai/manual-article-workflow.md` の画像パス説明は移行時に更新
- Python 定数名 `BASE_URL` は改名しない（`from article.config import BASE_URL` / `patch("article.image.BASE_URL", ...)` 互換維持）
- `RAKUTEN_ORIGIN`/`RAKUTEN_REFERER` は `SITE_ORIGIN` から派生させない（楽天は登録 Origin 単位のため env 明示）
- 大小文字: astro 系=`https://BWDSF3104.github.io`（大文字）/ Rakuten 系=`https://bwdsf3104.github.io`（小文字）— 各々保持
