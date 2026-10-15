# アフィリエイト末尾セクションの構造統一（案B: CTA box 廃止 + product-card 行統一）

**Date**: 2026-10-15

**Decision**: 記事末尾のアフィリエイトセクションを「楽天商品カード + キーワード検索リンク行」の `.product-card` 系 div を単一 `.product-cards` ラッパーに収める構造に統一した。インラインスタイルの CTA box（`_build_main_cta_section`）と検索リンクの markdown リスト（`_build_affiliate_links_html`）を廃止。

**Reason**: CTA box とテキストリンクで同一キーワードが重複表示され、末尾セクションが視覚的に重かった。既存の商品カード CSS（`.product-card`/`.pc-btn`）を再利用すれば新規 CSS 追加ゼロで統一できる。

**Rejected Alternatives**: 案A（CTA box の見た目をスリム化して残す）— 重複構造そのものが残る。案C（テキストリンク側を新しい `.search-link-row` class で個別スタイル化）— 新規 CSS が必要で見た目の差が生まれる。

**Impact**: 新記事のみ新フォーマット適用。既存記事（約40本）は旧フォーマット（CTA box + markdown リスト）のまま。`global.css` の `:has()` CSS（旧記事の markdown リストをカード表示する規則、commit `27cba6a`）は旧記事のスタイル維持のため継続維持。
