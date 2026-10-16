# 2026-10-16: タグ由来検索リンクのトグル化（ENABLE_TAG_AFFILIATE、デフォルトOFF）

**Status**: 完了
**Next Action**: なし

## 概要

ユーザー要望: 記事タグ（frontmatter tags / kemono_params）から生成されるアフィリエイトの「Amazon / 楽天市場で検索」リンク（検索リンク行）をオン・オフ可能にし、デフォルトはオフとする。

背景:
- 記事末尾の「### 📚 テーマ関連のおすすめアイテム・書籍」セクションが常にONで、tags から派生した検索リンク行（例: 「ケモノ」「ケモノ BL」）が生成されていた。
- スコープ確定（ユーザーと認識合わせ済み）: **タグ由来の検索リンク行のみ**をトグル対象（案B1）。
  - 楽天API商品カード（画像・価格付きの実在商品）はそのまま維持。検索カスケード（`_rakuten_api_keywords`）も変更しない。
  - `process_inline_affiliates`（本文プレースホルダー）・`process_inline_products`（比較表）・`process_product_cards`（product_recommendations）はタグ由来でないため対象外。
- 既存のトグル前例 `ENABLE_CHAR_DEDUP`（2026-10-13）の同一パターンを踏襲する。

## 変更内容

- `scripts/article/config.py`:
  - 新定数 `ENABLE_TAG_AFFILIATE = os.environ.get("ENABLE_TAG_AFFILIATE", "0") == "1"`（デフォルトOFF、`ENABLE_TAG_AFFILIATE=1` でON）
  - `__all__` に追加
- `scripts/article/affiliate.py`:
  - `inject_affiliate_links`: トグルOFF時は `_build_search_link_rows` をスキップ（検索リンク行・リンクログエントリを空に）。楽天APIカード・開示文言は不変
  - トグルOFFかつ楽天APIカードも無い場合は末尾セクションが空になるため、セクション全体をスキップして content をそのまま返す（誤解を招く空見出しの回避）
- `scripts/tests/test_generate_article.py`:
  - `TestInjectAffiliateLinks._run`: `article.affiliate.ENABLE_TAG_AFFILIATE` を True にパッチ（既存テストはON時の挙動を検証）
  - `TestTagAffiliateToggle` 新增: OFF（既定）で検索リンク行とセクションがスキップ / OFF かつ楽天カードありでカードのみ残存 / ON で検索リンク行生成

## 影響

- デフォルト（OFF）: 新規生成記事に「Amazon / 楽天市場で検索」行が出ない。楽天API商品カードが無い記事は末尾セクション自体が無くなる。`data/affiliate_logs/` の検索リンクログも出ない
- `ENABLE_TAG_AFFILIATE=1` 時: 現行と同一
- 既存記事は不変（次回以降の生成のみ影響）
- `.env`・`deploy.yml` への変数は不要（既定OFFで動作）

## 副次所見（別タスク化）

- `extract_product_recommendations`（`affiliate.py`）の正規表現 `((?:\s*-\s+.*\n?)+)` が `category:` 等の継続行にマッチせず、2項目目以降・category・price_range を落としている（2026-10-16-100918 記事で 2商品→1商品・価格帯喪失を確認）。ユーザー指示により本タスク外 → `known-issues/KI-20261016-01-product-recommendations-parser.md` に記録。

## Verification

- `python -m pytest scripts/tests/ -v` → 407 passed（7.41秒、新規3テスト含む）
- `TestTagAffiliateToggle` + `TestInjectAffiliateLinks` 単独 → 9 passed（1.14秒）
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要

## 備考

- `.env` への `ENABLE_TAG_AFFILIATE` 追記は不要（既定OFFで動作）。有効化したい場合は `.env` に `ENABLE_TAG_AFFILIATE=1` を追加

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] `known-issues/KI-20261016-01-product-recommendations-parser.md` を新規作成（副次所見の別タスク化）
- [x] `decisions/` 不要（既存トグル前例 `ENABLE_CHAR_DEDUP` の同一パターン踏襲。タスクファイルで記録）
- [x] `backlog.md` 不要（KI エントリが未修正タスクの参照先）
- [x] `architecture.md` を更新（トグルの明記）
