# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

## Backlog P0 実装計画 (2026-10-02)

9件を4つのバッチにグループ化。依存関係と影響範囲で分割。

| バッチ | 項目 | 推定工数 | 依存 |
|--------|------|----------|------|
| B1 | Back to Top, Skip Navigation | 低 | なし |
| B2 | コピーボタン, Lazy Loading | 低 | なし |
| B3 | Tag Colors, OG Tags | 中 | B1/B2と独立 |
| B4 | Social Sharing, Footer SNS, Breadcrumb Schema | 中 | B3のOG最適化と関連 |

### B1: アクセシビリティ・ナビゲーション

**1. Back to Top ボタン**: 固定位置 (bottom-right) の FAB。スクロール位置が 300px を超えた時点でフェードイン。`PostLayout.astro` のみに追加。

**2. Skip Navigation Link**: ページ最上部に `visibility: hidden` のスキップリンク。フォーカス時に可視化。`<main>` に `id="main-content"` を設定。`PostLayout.astro` と `index.astro` に追加。`global.css` に `.skip-link` スタイル。

### B2: 機能改善

**3. コードブロックのコピーボタン**: 各 `<pre>` 右上にコピーボタン。クリップボードAPIでコピー。成功時に「Copied!」を2秒表示。`PostLayout.astro` に追加。

**4. Lazy Loading for Images**: 本文内の画像に明示的な `loading="lazy"` を追加。アイキャッチは `fetchpriority="high"` のまま維持（LCP候補）。

### B3: デザイン・SEO

**5. Tag Colors**: タグ名から一貫した色を生成。8-12色のパレットを定義。ハッシュ関数でタグ名→色マッピング。`PostLayout.astro`, `index.astro`, `tags/index.astro` で共通化。

**6. OG Tags の最適化**: `og:locale` に `ja_JP` を追加。`og:image:type`, `og:image:width`, `og:image:height` を追加。`article:modified_time` を追加（frontmatter に更新日がある場合）。

### B4: 共有・SNS

**7. Social Sharing Buttons**: 記事ページ下部に共有ボタン。Twitter (X), Hatena Bookmark, LINE, Pocket。SVGアイコンをインライン埋め込み。

**8. Footer の SNS リンク**: Footer に Twitter (X), GitHub, RSS のアイコンリンクを追加。既存のテキストリンクは維持。

**9. Breadcrumb Schema**: トップページとタグページに BreadcrumbList JSON-LD を追加。記事ページは既に完全。

---

# Completed Plans

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。

- [2026-10-02] Reddit 代替ソースの追加: e621、Kemono API、RSS フィードを代替ソースとして追加。kemono/pokemon カテゴリのトピック収集を安定化。テスト134件全件通過
- [2026-10-02] 既存記事のアフィリエイトリンク一括置換: `scripts/fix_affiliate_links.py` で 15ファイル（48行）を `[text](url)` から `<a>` タグに置換。1ファイル試験→全体適用→ビルド成功 (94ページ)
- [2026-10-01] canonical URL一貫性: slug変更時の301リダイレクト実装。`data/slug-redirects.json` で旧→新slugマッピングを記録。`generate_article.py` にslug変更検出・自動記録ロジック追加。`[...slug].astro` の `getStaticPaths` にリダイレクトルートを追加してAstroレベルの301リダイレクトを実装。sitemap整合性確認済み。テスト119件全件通過、ビルド成功 (90ページ)
- [2026-10-01] FAQPage schema + Speakable schema: 記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成（行単位ステートマシンパーサー）。記事冒頭段落をSpeakable JSON-LDとして出力。`generate_article.py` に `_extract_faq_pairs()` と `_extract_speakable_text()` を追加し、frontmatter にJSON文字列で記録。`PostLayout.astro` で条件付きJSON-LD出力。テスト134件全件通過、ビルド成功 (90ページ)
- [2026-10-01] 記事ページダークモードの文字色コントラスト改善: `PostLayout.astro` の `<article>` に `dark:prose-invert` + 各要素の `dark:` 変種クラスを追加して本文の文字色を改善。ビルド成功 (92ページ)
