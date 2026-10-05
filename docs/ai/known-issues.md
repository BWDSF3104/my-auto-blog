# 既知問題リスト

進行中の問題のみを記録。解決済は `known-issues-archive.md` に移動する。

---

### KI-001: ハンバーガーメニューの記事一覧リンクが反応しない

- 発見日: 2026-10-05
- 症状: モバイルハンバーガーメニュー内の「記事一覧」リンクを押してもページ遷移・スクロールが発生しない
- 影響範囲: `Header.astro` のモバイルメニュー
- 状態: 調査完了
- 原因: `href="#main-content"` はページ内の `id="main-content"` 要素へのアンカーリンク。`index.astro` と `PostLayout.astro` には `<main id="main-content">` があるが、`page/[page].astro` には `id` 属性がないため、ページネーションページでリンクが機能しない
- 修正案: `href="#main-content"` → `href={baseUrl}` に変更（トップページの記事一覧へ遷移）
- 修正完了: 2026-10-05, `Header.astro:112` を修正

### KI-002: ヒーローセクションの最新記事ボタンが記事一覧以外では動作しない

- 発見日: 2026-10-05
- 症状: ヒーローセクションの「最新記事を読む」ボタンがトップページ以外で期待通りに動作しない
- 影響範囲: `Header.astro` のヒーローセクション
- 状態: 調査完了
- 原因: `href="#main-content"` のアンカーリンク。KI-001と同様、`page/[page].astro` に `#main-content` が存在しない。さらに、ヒーローセクションは `Header.astro` 内にハードコードされており、全ページで表示される。記事ページで「最新記事を読む」ボタンが表示される意味が薄い
- 修正案A: `href="#main-content"` → `href={baseUrl}` に変更（最小修正）
- 修正案B: ヒーローセクションを `Header.astro` から分離し、トップページ専用に移動（設計変更）
- 推奨: 修正案A（最小修正）。skip-link も `#main-content` を参照しているので、`page/[page].astro` に `id="main-content"` を追加する
- 修正完了: 2026-10-05, `Header.astro:167` + `page/[page].astro:126` を修正

### KI-003: 記事内画像が劇中シーンと関連していない

- 発見日: 2026-10-05
- 症状: 記事内に生成される挿絵画像が、周囲の本文のシーンと関連性が低い
- 影響範囲: 物語系記事（kemono_story）
- 状態: 調査完了
- プロンプト生成のフロー:
  1. Gemini が記事生成時に `<!-- IMAGE_PROMPT: "[character_1] シーンの英語説明" -->` を本文に挿入
  2. `extract_image_prompt()` で frontmatter の `image_prompt` を抽出（アイキャッチ用）
  3. `process_inline_images()` で本文内の `IMAGE_PROMPT` タグを検出
  4. `compose_image_prompt()` で `BASE_QUALITY_PROMPT + art_style + character_N の外見定義 + シチュエーション` を合成
  5. 合成したプロンプトを HF Space (blume/kemono-image-api) に送信
- 問題点:
  - Gemini が生成する IMAGE_PROMPT の説明が簡略的または一般的なシーンになりがち
  - プロンプトテンプレート (`kemono_story.txt:38-47`) では「印象的なシーン」「異なる瞬間」という指示はあるが、AI が本文の文脈を正確に反映したプロンプトを生成しない
  - 1-pass 生成のため、記事生成時に画像プロンプトの品質を最適化できない
- 修正案A: プロンプトテンプレートを強化し、IMAGE_PROMPT に具体的なシーンの指示を追加
- 修正案B: 2-pass 生成を画像プロンプトにも適用（記事生成後、本文の文脈からプロンプトを精製）
- 推奨: 修正案A（最小修正）。テンプレートの指示を強化
