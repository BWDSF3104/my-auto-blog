# Current Task Archive

Completed tasks moved from `current-task.md`. Kept active task + 1 recent completed in `current-task.md`.

---

## canonical URL一貫性 (完了)

slug変更時の301リダイレクト実装。`data/slug-redirects.json` で旧→新slugマッピングを記録。`[...slug].astro` の `getStaticPaths` にリダイレクトルートを追加。
pytest: 119 passed, npm run build: 90 pages
Commit: 1b8a6d4

## FAQPage schema + Speakable schema (完了)

記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成。記事冒頭段落をSpeakable JSON-LDとして出力。
pytest: 134 passed, npm run build: 90 pages

## 既存記事の見栄え改善（モバイル対応含む）(完了)

index.astro, tags/index.astro, tags/[tag].astro のインラインCSSをTailwindへ統一。共通 Header/Footer コンポーネント作成。ページネーション、タグ検索、ダークモード、404ページ、Aboutページ、読了時間表示を追加。
npm run build: 85 pages
Commit: dd356fe

## Google 検索エンジンへのサイトインデックス登録 (完了)

全ページに Google 所有権検証 meta タグ追加。JSON-LD 構造化データと sitemap の完全性を確保。
npm run build: 86 pages
Commit: 6fda78e

## CI ワークフローのキャッシュファイルパス修正と SEO 残タスク (完了)

`deploy.yml` の `git add data/latest_topics.json` を `git add data/topics/` へ更新。sitemap.xml に主要タグページ追加。
pytest: 96 passed, npm run build: 86 pages
Commit: 29e5120, a9f00e2

## 既存記事のdescription修正 (完了)

80文字未満のdescriptionを持つ4件の既存記事を独立スクリプトで120文字に拡張。
pytest: 96 passed, npm run build: 89 pages
Commit: 5f53c94

## 自動内部リンク機能の実装 (完了)

本文内で関連記事のタイトルが見つかった場合、自動的にアンカーテキストリンクを挿入。
pytest: 108 passed
Commit: 30bb1e7

## ページネーション修復と画像サイズ復元 (完了)

/page/2 以降のルーティングを復元し、記事一覧の画像サイズを元の 180×120px に戻す。
npm run build: 89 pages, pytest: 96 passed
Commit: b996bf2

## 記事生成を伴わないデプロイ用ワークフロー追加 (完了)

`deploy-only.yml` を追加して記事生成なしで Astro ビルド + デプロイのみを実行できるワークフローを提供。
Commit: c5d2636

## 記事一覧の画像サイズ修正（モバイル対応）(完了)

記事一覧の画像が横幅一杯に広がる問題を修正。Tailwind CSS がページに注入されない問題を調査・修正。
npm run build: 89 pages, pytest: 96 passed
Commit: 8c6b844, d52b445, 23fb19e

## LCP/CLSパフォーマンス最適化 (完了)

ヒーロー画像の preload, fetchpriority, aspect-ratio, preconnect を追加して Core Web Vitals を改善。
npm run build: 89 pages
Commit: c7d49c9

## ダークモード修正: トグルボタン動作復元と記事ページのダークモード適用 (完了)

`is:inline` 属性なしによりクライアントサイドスクリプトが動作しない問題を全ページで修正。記事ページに `dark:` クラスと `Header` コンポーネントを追加。
npm run build: 90 pages
Commit: d90ebe5

## 記事ページダークモードの文字色コントラスト改善 (完了)

`PostLayout.astro` の `<article>` に `dark:prose-invert` + 各要素の `dark:` 変種クラスを追加。
npm run build: 92 pages
Commit: 1f611e5

## ダークモードトグルボタン動作復元 (TypeScript型注釈削除) (完了)

`<script is:inline>` 内の TypeScript 型注釈 (`dark: boolean`) がブラウザで構文エラーを引き起こす問題を修正。
npm run build: 92 pages, pytest: 134 passed
Commit: 3232915

## ダークモードトグルボタン動作復元 (setDark関数の引数修正) (完了)

`setDark()` 関数内で未定義の変数 `dark` を参照していたバグを修正。
npm run build: 92 pages, pytest: 134 passed
Commit: 07e9804

## ダークモード初期化スクリプトの全ページ投入 (完了)

`ThemeInit.astro` 新規作成し、`PostLayout.astro` と各スタンドアロンページに `<ThemeInit />` を追加。`prefers-color-scheme` の自動検出と `localStorage` からのテーマ復元を全ページで有効化。
npm run build: 92 pages, pytest: 134 passed
Commit: 7d80e61
