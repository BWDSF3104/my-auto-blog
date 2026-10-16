# 2026-10-16: 記事内商品カードのスリム化（絵文字・カテゴリ行の削除 + padding 縮小）

**Status**: 完了
**Next Action**: なし（commit / push 済み）

## 概要

ユーザー要望: 記事内商品カード（frontmatter `product_recommendations` → `generate_product_cards` が生成する HTML）をスリム化する。具体的には:
1. 絵文字（📦 等、`.pc-icon` 要素）の削除
2. 「商品」カテゴリ行（`.pc-category` 要素）の削除
3. padding / gap の縮小

対象例: `2026-10-16-100918-auto-post.md` の「機動戦士ガンダム 閃光のハサウェイ」カード（`.pc-icon`📦 + 「商品」フォールバック行 + 価格なし）。

スコープ確定（ユーザーと認識合わせ済み、2026-10-16）:
- **対象**: 記事内カード（`generate_product_cards` 生成分）
- **変更しない**: 楽天APIカード（`.pc-img` 画像付き）、検索リンク行（`_build_search_link_rows`、`ENABLE_TAG_AFFILIATE` デフォルトOFF）、旧記事（再生成しない。静的HTMLは絵文字・カテゴリ行を残す）
- 案A/BのプレビューHTML（`docs/ai/tmp/card_preview_A.html` / `_B.html`）を作成しスクリーンショットを `I:\マイドライブ\kilo\` に配置。ユーザーは **案B（強め）** を選択。

## 変更内容

- `scripts/article/affiliate.py` `generate_product_cards`:
  - `cat_icons` 辞書・`icon` 変数・`category` 変数（不使用化）を削除
  - カード HTML テンプレートから `.pc-icon` 行と `.pc-category` 行を削除
  - docstring 更新
- `src/styles/global.css`:
  - 案B値の slim CSS を新設: `.product-card:not(:has(.pc-img)):not(:has(.pc-icon))`（padding 8px 10px / gap 8px、`.pc-btn` padding 4px 10px / font-size 0.75em）
  - プレビューのセレクタ（`:not(:has(.pc-img))` のみ）から `:not(:has(.pc-icon))` を追加: **旧記事のアイコンカードをスリム化対象から除外し、旧記事の外観を変更しない**（ユーザー確定スコープ「旧記事は変更しない」遵守）
  - `.pc-icon` / `.pc-category` の CSS ルールは維持（旧記事の静的HTMLが依存するため）

## 影響

- 新規記事: 商品カードが絵文字・カテゴリ行なしのコンパクト表示（高さが約 4px 縮小）
- 旧記事: 外観不変（静的HTMLに絵文字が残るが、スリムCSSは非該当）
- 検索リンク行（`ENABLE_TAG_AFFILIATE=1` 時）: スリムCSSが適用される（`.pc-icon` なしのため）
- 楽天APIカード: 不変（`:not(:has(.pc-img))` で除外）
- `extract_product_recommendations` の正規表現バグ（KI-20261016-01）は別タスクであり本タスクの対象外

## Verification

- `python -m pytest scripts/tests/ -v` → **407 passed**（7.63s）
- `npm run build` → **成功**（148 ページ）
- ビルド済み HTML 検証: `dist/posts/zankyou-no-duplica/index.html`
  - 旧カード（`.pc-icon`📦 + `.pc-category`「商品」）・楽天APIカード 3件（`.pc-img`）・検索リンク行 7件が不変で残存（旧記事スコープ遵守）
- ビルド済み CSS 検証: `dist/_astro/global.1wlmpSZV.css`（66,691 B）にスリムセレクタ 2箇所・`gap:8px;padding:8px 10px` 1箇所を確認
- 新フォーマット視覚検証: `generate_product_cards` 実関数で生成した新カードを dist コピーに差し替えてローカル配信し、Playwright で computed style を確認
  - card: `padding: 8px 10px` / `gap: 8px`、`.pc-icon` なし・`.pc-category` なし
  - button: `padding: 4px 10px` / `font-size: 12px`（0.75em）
  - スクリーンショット: `I:\マイドライブ\kilo\card_verify_new.png`
