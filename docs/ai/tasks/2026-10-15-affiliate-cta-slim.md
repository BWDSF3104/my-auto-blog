# アフィリエイトCTAカードのスリム化 + テキストリンクの統一（案B）

**Status**: 完了
**Date**: 2026-10-15
**Backlog**: P2 #3

## 背景

CTA box（`_build_main_cta_section`、インラインスタイルの琥珀グラデ box「🔥 …の今すぐチェックできるおすすめアイテム / Amazonで確認する →」）と検索リンクの markdown リスト（`📦/🛍️「Amazonで「kw」を探す」`）が同一キーワードを重複表示し、末尾セクションが重かった。ユーザーが案B（CTA box 廃止 + 検索リンクを `.product-card` 行に統一）を選択。

## 変更内容

- `scripts/article/affiliate.py`:
  - `_build_main_cta_section`（CTA box）を削除
  - `_build_affiliate_links_html` → `_build_search_link_rows` に改名・書き換え: キーワードごとに 1 行の `.product-card` 行を生成（`.pc-name` に「🔥 「kw」」（1行目の主キーワードのみ 🔥）、`.pc-category` に「Amazon / 楽天市場で検索」、`.pc-links` に `.pc-btn` Amazon/楽天 ボタン）。UTM 追跡パラメータは維持
  - `_build_rakuten_cards_section`: `.product-cards` ラッパーを除去し、生カード HTML を返却するよう変更
  - `inject_affiliate_links`: 楽天商品カード + 検索リンク行を単一の `.product-cards` ラッパーに統合
- `scripts/tests/test_generate_article.py`: `TestInjectAffiliateLinks` クラス 6 テスト追加（CTA 文言削除・行統一・🔥 主キーワードのみ・UTM 維持・単一ラッパー統合・tags フォールバック）
- CSS 追加ゼロ: 既存 `.product-card`/`.pc-btn` を再利用。`global.css` の `:has()` CSS（旧記事の markdown リスト用）は約40本の旧記事のスタイル維持のため継続維持
- 既存記事は旧フォーマット（CTA box + markdown リスト）のまま。新記事のみ新フォーマット適用

## Verification

- `pytest scripts/tests/ -q`: 404 passed in 7.00s（既存 398 + 新 6）
- `npm run build`: 145 page(s) built in 2.94s（テスト記事削除後の再ビルド）
- 視覚検証: `_rakuten_search` をモックしたテスト記事を生成し、ローカル HTTP サーバー（port 8123）で `.product-cards` セクションをライト/ダーク両モードでスクリーンショット。ユーザーのモバイルで確認済み（2026-10-15、レイアウト OK）
- テスト記事・スクリーンショットは `kilo-safe-remove.cmd` で削除済み

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除（開始時未登録のため該当なし）
- [x] `plans/` の該当ファイル（該当なし）
- [x] `known-issues/` の該当ファイル（該当なし）
- [x] `backlog.md` の完了項目 P2 #3 を削除
