# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task (完了)

canonical URL一貫性: slug変更時の301リダイレクト実装

## Priority (完了)

P1

## Status (完了)

完了

## Context

GitHub Pages静的サイトのためミドルウェア使用不可。Astroの`getStaticPaths` + `redirect` で静的301リダイレクトを実装。
旧slug→新slugのマッピングを `data/slug-redirects.json` に記録。
`generate_article.py` がslug変更を検出して自動記録。

## Progress

- [x] Memory Bank (plans.md) に計画記録
- [x] `data/slug-redirects.json` の初期構造作成
- [x] `generate_article.py` にslug変更検出ロジック追加
- [x] `[...slug].astro` にリダイレクトルートの `getStaticPaths` 追加
- [x] テスト追加 (pytest) - 11件追加、計119件全件通過
- [x] ビルド検証 (npm run build) - 90ページ成功
- [x] sitemap整合性確認 - 34記事のslugが正しく反映
- [x] backlog.md から完了項目を削除
- [x] plans.md の Completed Plans に記録
- [x] git commit & push (1b8a6d4)

## Verification

- pytest scripts/tests/ -v: 119 passed in 1.64s
- npm run build: 90 page(s) built, Complete!
- sitemap.xml: 34 post URLs 正しく生成
- Commit: 1b8a6d4

---

## Task (完了)

FAQPage schema + Speakable schema: JSON-LD構造化データの追加

## Priority (完了)

P2

## Status

完了

## Context

記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成。
記事冒頭段落をSpeakable JSON-LDとして出力。
`generate_article.py` に抽出関数を追加し、frontmatter に結果を記録。
`PostLayout.astro` で条件付きJSON-LD出力。

## Progress

- [x] plans.md に Active Plans として記録
- [x] 既存 JSON-LD 実装を調査（PostLayout.astro, generate_article.py）
- [x] FAQPage schema: `_extract_faq_pairs()` 関数を `generate_article.py` に追加（行単位パーサー）
- [x] Speakable schema: `_extract_speakable_text()` 関数を `generate_article.py` に追加
- [x] `generate_post()` パイプラインに組み込み（frontmatter に `faq`, `speakable` を記録）
- [x] `PostLayout.astro` に FAQPage + Speakable JSON-LD 出力追加
- [x] ユニットテスト追加 (15件)
- [x] pytest 全件通過確認 (134件)
- [x] npm run build 成功確認 (90ページ)
- [x] Memory Bank 更新 (plans.md completed, backlog.md 削除)
- [x] git commit & push

## Verification

- pytest scripts/tests/ -v: 134 passed in 1.64s
- npm run build: 90 page(s) built, Complete!

## Next Action

なし

## Task (完了済み)

既存記事を除く本プロジェクトのページの見栄えや機能を改善（モバイル対応含む）

## Priority (完了済み)

P1

## Status (完了済み)

完了

## Objective (完了済み)

index.astro, tags/index.astro, tags/[tag].astro のインラインCSSをTailwindクラスへ置換し、PostLayout.astro とスタイル体系を統一する。

## Steps (完了済み)

1. [x] Tailwind統一: index.astro
2. [x] Tailwind統一: tags/index.astro
3. [x] Tailwind統一: tags/[tag].astro
4. [x] 共通 Header.astro / Footer.astro コンポーネント作成
5. [x] 全ページで Header/Footer を使用
6. [x] ホームページにページネーション追加
7. [x] タグ一覧ページに検索フィルタ
8. [x] ダークモード対応
9. [x] 404エラーページ作成
10. [x] Aboutページ作成
11. [x] 読了時間表示

## Completed (完了済み)

Steps 1-11 全完了。ビルド成功確認 (85ページ)。

## Commit (完了済み)

dd356fe — feat: dark mode support, reading time display, 404 page, about page, shared components, pagination, tag search

---

## Task (完了)

Google 検索エンジンへのサイトインデックス登録を有効化するための SEO 改善

## Priority

P1

## Status

完了

## Objective

Google Search Console での所有権検証を全ページで有効にし、JSON-LD 構造化データと sitemap の完全性を確保する。

## Steps

1. [x] Layout.astro に Google 所有権検証 meta タグ追加
2. [x] index.astro に Google 所有権検証 meta タグ追加 (Layoutをバイパスするため)
3. [x] about.astro に Google 所有権検証 meta タグ追加
4. [x] 404.astro に Google 所有権検証 meta タグ追加
5. [x] tags/index.astro に Google 所有権検証 meta タグ追加
6. [x] tags/[tag].astro に Google 所有権検証 meta タグ追加
7. [x] page/[page].astro に Google 所有権検証 meta タグ追加
8. [x] PostLayout.astro の sitemap 出力確認
9. [x] index.astro に JSON-LD (BlogPosting) 構造化データ追加
10. [x] about.astro に JSON-LD (AboutPage) 構造化データ追加
11. [x] sitemap.xml.ts に静的ページ (/about/, /tags/) を追加
12. [ ] `npm run build` でビルド成功確認
13. [ ] git commit & push
14. [x] Bing Webmaster Tools 検証 (Google Search Console からインポートで完了)
15. [x] Google Search Console に sitemap 提出 (手動完了)

## Modified Files

- `src/layouts/Layout.astro` — Google 所有権検証 meta タグ追加
- `src/layouts/PostLayout.astro` — sitemap 出力確認 (変更なし)
- `src/pages/index.astro` — Google 所有権検証 meta タグ + JSON-LD 追加
- `src/pages/about.astro` — Google 所有権検証 meta タグ + JSON-LD 追加
- `src/pages/404.astro` — Google 所有権検証 meta タグ追加
- `src/pages/tags/index.astro` — Google 所有権検証 meta タグ追加
- `src/pages/tags/[tag].astro` — Google 所有権検証 meta タグ追加
- `src/pages/page/[page].astro` — Google 所有権検証 meta タグ追加
- `src/pages/sitemap.xml.ts` — 静的ページ追加

## Pending

- Steps 12-15: ビルド確認、コミット、Bing検証、sitemap提出

## Verification

`npm run build` — 86ページビルド成功 (2026-10-01 13:17)

## Commit

6fda78e — feat: add Google Search Console verification, JSON-LD structured data, sitemap completeness

---

## Task (完了)

CI ワークフローのキャッシュファイルパス修正と SEO 残タスク

## Priority

P1

## Status

完了

## Objective

`deploy.yml` の `data/latest_topics.json` 参照を `data/topics/` へ更新し、CI のコミットステップが正常に動作するよう修正する。その後 Bing 検証 ID の追加と sitemap 提出を完了させる。

## Steps

1. [x] `deploy.yml` の旧キャッシュパスを特定
2. [x] `deploy.yml` の `git add data/latest_topics.json` を `git add data/topics/` へ更新
3. [x] `pytest scripts/tests/ -v` でテスト確認
4. [x] `npm run build` でビルド確認
5. [x] git commit & push (29e5120)
6. [x] Bing Webmaster Tools 検証 (Google Search Console からインポートで完了)
7. [x] Google Search Console に sitemap 提出 (手動完了)

## Modified Files

- `.github/workflows/deploy.yml` — キャッシュファイルパス更新

## Pending

- Steps 2-7: ワークフロー修正、テスト/ビルド確認、コミット、Bing検証、sitemap提出

## Verification

`pytest scripts/tests/ -v` — 96/96 passed (1.52s)
`npm run build` — 86 pages built in 1.89s

## Steps

1. [x] `deploy.yml` の旧キャッシュパスを特定
2. [x] `deploy.yml` の `git add data/latest_topics.json` を `git add data/topics/` へ更新
3. [x] `pytest scripts/tests/ -v` でテスト確認
4. [x] `npm run build` でビルド確認
5. [x] git commit & push (29e5120)
6. [x] sitemap.xml.ts に主要タグページ（Kemono, Novel, Fantasy, LLM, AI, Python, TF, SF）を追加
7. [x] `npm run build` でビルド成功確認 (89ページ)
8. [x] git commit & push (a9f00e2)
7. [x] Bing Webmaster Tools 検証 (Google Search Console からインポートで完了)
8. [x] Google Search Console に sitemap 提出 (手動完了)

## Commit

29e5120 — fix: update CI workflow cache path from data/latest_topics.json to data/topics/
a9f00e2 — feat: add major tag pages to sitemap.xml

## Next Action

なし (SEO 改善タスク全完了)

---

## Task (完了)

既存記事のdescription修正（80文字未満を修正）

## Priority

P1

## Status

完了

## Objective

80文字未満のdescriptionを持つ既存記事を独立スクリプトで修正。

## Steps

1. [x] 全記事のdescription長さをスキャン（4件が80文字未満）
2. [x] `scripts/fix_descriptions.py` スクリプト作成
3. [x] スクリプト実行して4件のdescriptionを120文字に拡張
4. [x] 修正後の長さを再スキャンで確認（全件80文字以上）
5. [x] `pytest scripts/tests/ -v` でテスト確認 (96/96 passed)
6. [x] `npm run build` でビルド確認 (89ページ)
7. [x] ビルドHTMLのdescription metaタグを確認（全件120文字）
8. [x] Memory Bank更新とgit commit

## Modified Files

- `src/content/posts/2026-09-27-092931-auto-post.md` — description 77→120文字
- `src/content/posts/2026-09-29-053425-auto-post.md` — description 68→120文字
- `src/content/posts/2026-09-29-060942-auto-post.md` — description 76→120文字
- `src/content/posts/2026-09-29-211041-auto-post.md` — description 78→120文字
- `scripts/fix_descriptions.py` — 独立スクリプト（新規）
- `scripts/_scan_desc.py` — 長さスキャンヘルパー（新規）

## Verification

`pytest scripts/tests/ -v` — 96/96 passed (1.42s)
`npm run build` — 89 pages built in 1.87s
HTML description metaタグ: 修正4件とも120文字確認

## Commit

5f53c94 — feat: fix existing articles with descriptions shorter than 80 characters

## Commit

5f53c94 — feat: fix existing articles with descriptions shorter than 80 characters

## Next Action

なし

---

## Task (完了)

自動内部リンク機能の実装

## Priority

P1

## Status

完了

## Objective

本文内で関連記事のタイトルが見つかった場合、自動的にアンカーテキストリンクを挿入して内部リンク構造を強化する。

## Steps

1. [x] `_load_posts_for_links()` ヘルパー関数を追加（既存記事の title, slug, tags を読み込み）
2. [x] `_existing_link_spans()` ヘルパー関数を追加（既存のMarkdownリンク・画像内の文字範囲を検出）
3. [x] `inject_internal_links()` 主関数を追加（タイトルマッチ→リンク挿入、既存リンク・画像内を回避、max_links 制限）
4. [x] `generate_post()` パイプラインに組み込み（`inject_affiliate_links` の後、`validate_and_fix_frontmatter` の前）
5. [x] ユニットテスト12件追加（post読み込み、基本マッチ、no-match、既存リンク・画像スキップ、max_links、frontmatter保護、短タイトルフィルタ）
6. [x] `pytest scripts/tests/ -v` でテスト確認 (108/108 passed)
7. [x] `npm run build` でビルド確認

## Modified Files

- `scripts/generate_article.py` — 内部リンク関数3つ追加、パイプラインに組み込み
- `scripts/tests/test_generate_article.py` — ユニットテスト12件追加

## Verification

`pytest scripts/tests/ -v` — 108/108 passed
`npm run build` — 成功確認

## Commit

30bb1e7 — feat: auto internal linking - insert anchor text links to related articles in body content

---

## Task (現在進行中)

ページネーション修復と画像サイズ復元

## Priority

P1

## Status

完了

## Objective

/page/2 以降のルーティングを復元し、記事一覧の画像サイズを元の 180×120px（モバイル 100%×160px）に戻す。

## Steps

1. [x] `[page].astro` の glob パスを `../../content/posts/*.md` に修正
2. [x] `calcReadingTime` を `getStaticPaths` 内にインライン展開
3. [x] デバッグ用 console.log を削除
4. [x] 画像サイズを `w-full h-[160px] sm:w-[180px] sm:h-[120px]` に復元
5. [x] `npm run build` でビルド成功確認 (89ページ、/page/2,3,4 生成)
6. [x] `pytest scripts/tests/ -v` でテスト確認 (96/96 passed)
7. [x] git commit & push (b996bf2)

## Modified Files

- `src/pages/page/[page].astro` — globパス修正、calcReadingTimeインライン化、画像サイズ復元
- `src/pages/index.astro` — 画像サイズ復元

## Verification

`npm run build` — 89 pages built in 1.91s (/page/2, /page/3, /page/4 生成確認)
`pytest scripts/tests/ -v` — 96/96 passed (1.40s)

---

## Task (完了)

記事生成を伴わないデプロイ用ワークフロー追加

## Priority

P1

## Status

完了

## Objective

既存の `deploy.yml` を維持したまま、`deploy-only.yml` を追加して記事生成なしで Astro ビルド + デプロイのみを実行できるワークフローを提供する。

## Steps

1. [x] 既存 `deploy.yml` のトリガーに `scripts/`, `data/` への push を追加
2. [x] `deploy-only.yml` 新規作成 (`src/`, `public/` などの push + 手動起動)
3. [x] `[skip ci]` 付きコミットは deploy-only でスキップされるよう `if` 条件設定
4. [x] git commit & push (c5d2636)

## Modified Files

- `.github/workflows/deploy.yml` — push トリガーに `scripts/**`, `data/**` を追加
- `.github/workflows/deploy-only.yml` — 新規作成

## Commit

c5d2636 — feat: add deploy-only workflow for build+deploy without article generation

---

## Task (完了)

記事一覧の画像サイズ修正（モバイル対応）

## Priority

P1

## Status

完了

## Objective

記事一覧の画像が横幅一杯に広がり、スマートフォン表示で画面からはみ出る問題を修正。

## Steps

1. [x] `index.astro` の画像に `max-w-[240px]` を追加（モバイルで幅を制限）
2. [x] `page/[page].astro` にも同様の修正を適用
3. [x] `npm run build` でビルド成功確認（89ページ）
4. [x] git commit & push (8c6b844)
5. [x] Tailwind CSS がページに注入されない問題を調査
6. [x] `global.css` import を Layout をバイパスする全ページに追加
7. [x] Playwright で画像の計算スタイルを確認（デスクトップ 180×120px、モバイル 240×160px）
8. [x] `npm run build` でビルド成功確認（89ページ）
9. [x] `pytest scripts/tests/ -v` でテスト確認 (96/96 passed)
10. [x] git commit & push (d52b445)

## Modified Files

- `src/pages/index.astro` — 画像に `max-w-[240px]` + `sm:max-w-none` を追加、`global.css` import 追加
- `src/pages/page/[page].astro` — 同上
- `src/pages/about.astro` — `global.css` import 追加
- `src/pages/404.astro` — `global.css` import 追加
- `src/pages/tags/index.astro` — `global.css` import 追加
- `src/pages/tags/[tag].astro` — `global.css` import 追加

## Verification

`npm run build` — 89 pages built in 2.15s
`pytest scripts/tests/ -v` — 96/96 passed (1.66s)
Playwright: デスクトップ画像 180×120px、モバイル画像 240×160px 確認

## Commit

8c6b844 — fix: constrain article list image width on mobile with max-w-240px
d52b445 — fix: add global.css import to pages bypassing Layout for Tailwind CSS
23fb19e — chore: add deploy workflow rule and screenshot directory to AGENTS.md

---

## Task (完了)

LCP/CLSパフォーマンス最適化

## Priority

P1

## Status

完了

## Objective

記事ページのヒーロー画像（LCP要素）の読み込み高速化と、画像読み込み時のレイアウトシフト（CLS）を解消する。

## Steps

1. [x] `<link rel="preload">` をヒーロー画像に追加（head 内）
2. [x] `fetchpriority="high"` をヒーロー画像の `<img>` に追加
3. [x] `width="896" height="512"` をヒーロー画像に追加
4. [x] `decoding="async"` をヒーロー画像・関連記事画像に追加
5. [x] `<link rel="preconnect">` を cdn.buymeacoffee.com に追加
6. [x] CSS `aspect-ratio: 896/512` を `.post-image` に追加
7. [x] CSS `aspect-ratio: 16/9` を `article img` に追加
8. [x] `astro.config.mjs` に `image.domains` を追加
9. [x] `npm run build` でビルド成功確認 (89ページ)
10. [x] 出力HTMLの属性確認（preload, fetchpriority, aspect-ratio, preconnect）
11. [x] git commit & push

## Modified Files

- `src/layouts/PostLayout.astro` — preload, fetchpriority, width/height, decoding, preconnect, aspect-ratio 追加
- `astro.config.mjs` — image.domains 追加

## Verification

`npm run build` — 89 pages built in 2.13s
出力HTML: preload, fetchpriority, preconnect, aspect-ratio 全属性確認済み

## Commit

c7d49c9 — feat: LCP/CLS performance optimization - preload hero image, fetchpriority, aspect-ratio, preconnect

## Next Action

なし

---

## Task (完了)

ダークモード修正: トグルボタン動作復元と記事ページのダークモード適用

## Priority

P1

## Status

完了

## Objective

`is:inline` 属性なしによりクライアントサイドスクリプトが動作しない問題を全ページで修正。記事ページ (`PostLayout.astro`) に欠落していた `dark:` クラスと `Header` コンポーネントを追加。

## Steps

1. [x] `Header.astro` の `<script>` に `is:inline` を追加
2. [x] `PostLayout.astro` に `Header` コンポーネントをインポート
3. [x] `PostLayout.astro` の `<body>`/`<main>` を `<div>` でラップ
4. [x] `PostLayout.astro` の `<script>` に `is:inline` を追加
5. [x] `PostLayout.astro` に `dark:` 変種クラスを追加（パンくず、ヘッダー、タグ、TOC、関連記事、アフィリエイトフォールバック、サポートボックス）
6. [x] `PostLayout.astro` にダークモードCSSを追加（`.post-image`, `article img`, `.toc-link`）
7. [x] `tags/index.astro` の `<script>` に `is:inline` を追加
8. [x] `npm run build` でビルド成功確認 (90ページ)
9. [x] Memory Bank 更新
10. [x] git commit & push

## Modified Files

- `src/components/Header.astro` — `<script is:inline>` 追加
- `src/layouts/PostLayout.astro` — `Header` インポート、`dark:` クラス、`is:inline`、ダークモードCSS
- `src/pages/tags/index.astro` — `<script is:inline>` 追加

## Verification

`npm run build` — 90 pages built, Complete!

## Commit

d90ebe5 — fix: dark mode toggle and post page dark mode styling

## Next Action

なし

---

## Task (完了)

記事ページダークモードの文字色コントラスト改善

## Priority

P1

## Status

完了

## Objective

ダークモード時の記事ページで `prose` クラスのデフォルト色が暗く、本文の文字が見づらかった問題を修正。

## Steps

1. [x] `PostLayout.astro` の `<article>` に `dark:prose-invert` + 各要素の `dark:` 変種クラスを追加
2. [x] `npm run build` でビルド成功確認 (92ページ)

## Modified Files

- `src/layouts/PostLayout.astro` — `dark:prose-invert` と各要素のダークモードカラーを追加

## Verification

`npm run build` — 92 pages built in 2.37s, Complete!

## Commit

1f611e5 — fix: improve dark mode text contrast on post pages with prose-invert

## Next Action

なし

---

## Task (完了)

ダークモードトグルボタン動作復元

## Priority

P1

## Status

完了

## Objective

`<script is:inline>` 内の TypeScript 型注釈 (`dark: boolean`) がブラウザで構文エラーを引き起こし、ダークモードトグルボタンが動作しない問題を修正。

## Steps

1. [x] `Header.astro` の `setDark(dark: boolean)` を `setDark(isDark)` に変更
2. [x] `npm run build` でビルド成功確認 (92ページ)
3. [x] `pytest scripts/tests/ -v` でテスト確認 (134/134 passed)
4. [x] git commit & push (3232915)

## Modified Files

- `src/components/Header.astro` — TypeScript型注釈を純粋なJavaScriptに変換

## Verification

`npm run build` — 92 pages built in 2.19s, Complete!
`pytest scripts/tests/ -v` — 134/134 passed (1.85s)

## Commit

3232915 — fix: dark mode toggle - remove TypeScript type annotation from is:inline script

## Next Action

なし

---

## Task (完了)

ダークモードトグルボタン動作復元 (setDark関数の引数修正)

## Priority

P1

## Status

完了

## Objective

`setDark()` 関数内で未定義の変数 `dark` を参照していたバグを修正し、トグルボタンが正常に動作するよう復元する。

## Steps

1. [x] `Header.astro` の `setDark()` 関数内で `dark` → `isDark` に修正
2. [x] `npm run build` でビルド成功確認 (92ページ)
3. [x] `pytest scripts/tests/ -v` でテスト確認 (134/134 passed)
4. [x] 出力HTMLのインラインスクリプトを確認
5. [x] git commit & push

## Modified Files

- `src/components/Header.astro` — `setDark()` 関数内の `dark` を `isDark` に修正

## Verification

`npm run build` — 92 pages built, Complete!
`pytest scripts/tests/ -v` — 134/134 passed (1.75s)

## Commit

07e9804 — fix: dark mode toggle - fix setDark function to use isDark parameter instead of undefined dark variable

## Next Action

なし

---

## Task (調査中 - 中断)

Reddit 代替ソースの追加 (P0)

## Priority

P0

## Status

調査中 - 中断

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

なし (調査段階)

---

## Task (完了)

ダークモード初期化スクリプトの全ページ投入

## Priority

P1

## Status

完了

## Objective

`PostLayout.astro` と各スタンドアロンページが独自の `<html>`/`<head>` を定義しているため、`Layout.astro` の初期化スクリプトが読み込まれず、`prefers-color-scheme` の自動検出と `localStorage` からのテーマ復元が効かない問題を修正。

## Steps

1. [x] `ThemeInit.astro` 新規作成（`localStorage` + `prefers-color-scheme` の初期化スクリプト）
2. [x] `PostLayout.astro` に `<ThemeInit />` を `<head>` 内に追加
3. [x] `index.astro` に追加
4. [x] `page/[page].astro` に追加
5. [x] `tags/index.astro` に追加
6. [x] `tags/[tag].astro` に追加
7. [x] `about.astro` に追加
8. [x] `404.astro` に追加
9. [x] `npm run build` でビルド成功確認 (92ページ)
10. [x] 出力HTMLに初期化スクリプトが含まれることを確認

## Modified Files

- `src/components/ThemeInit.astro` — 新規作成
- `src/layouts/PostLayout.astro` — `ThemeInit` インポート + `<head>` 内に追加
- `src/pages/index.astro` — 同上
- `src/pages/page/[page].astro` — 同上
- `src/pages/tags/index.astro` — 同上
- `src/pages/tags/[tag].astro` — 同上
- `src/pages/about.astro` — 同上
- `src/pages/404.astro` — 同上

## Verification

`npm run build` — 92 pages built in 2.14s, Complete!
出力HTML: `localStorage.getItem('theme')` が全ページに確認済み

## Next Action

なし
