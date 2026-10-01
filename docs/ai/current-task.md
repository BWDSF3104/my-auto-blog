# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

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

進行中

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
