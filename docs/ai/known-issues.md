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
- **根本原因 (2026-10-05 調査で判明)**:
  - `compose_image_prompt()` が合成するプロンプトが SDXL の CLIP エンコーダー 77 トークン上限を常に超過（実測 78-155 トークン）
  - 77 トークン以降は切り捨てられるため、末尾の「シチュエーション（シーン説明）」が完全に破棄される
  - 固定コンポーネントのみで 88-96 トークン（BASE_QUALITY_PROMPT 25 + art_style 11-14 + character_1 24-29 + character_2 23-30）
  - 77 トークン上限はモデルアーキテクチャ（SDXL CLIP ViT-L/14）の制約であり、HF Space の設定では変更不可
- HF ZeroGPU クォータ制約:
  - Space `blume/kemono-image-api` は ZeroGPU A10G で稼働、無料枠 3.5 分/日
  - `@spaces.GPU(duration=90)` で 1 リクエストあたり 90 秒予約 → 1 日約 2 リクエストのみ可能
  - 1 記事 = 1 ヘッダー + 2 インライン = 3 画像 = 270 秒予約 → 無料枠の 1 記事生成ですら超過
- 修正案A: `compose_image_prompt()` の BASE_QUALITY_PROMPT とキャラ定義を短縮して 77 トークン内に収める（シーン説明を優先）
- 修正案C: `MAX_INLINE_IMAGES=1` に制限して HF クォータ内の利用に収める
- **修正案D: SDXL長プロンプトchunking実装 (2026-10-05 成功)**:
  - HF Space `app.py` に `get_long_prompt_embeddings_sdxl` 関数を追加
  - 75トークン単位でチャンク分割 → 各チャンクをtext encoderに通す → embeddingを連結
  - 关键点: `hidden_states[-2]` (penultimate layer)、`text_encoder_2`のpooled出力、positive/negativeチャンク数一致
  - 短プロンプト（~15トークン）テスト: 平均輝度69、成功
  - 長プロンプト（~65トークン）テスト: 平均輝度110、成功
  - 100+トークンテスト: 平均輝度119、成功
  - Compel 2.3.1は依存関係競合（huggingface-hubバージョン）で断念
  - 詳細: `docs/ai/tasks/2026-10-05-long-prompt-v2.md`
- 推奨: 修正案D（長プロンプトchunking）
