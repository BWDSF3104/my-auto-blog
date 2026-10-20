# Gemini商品名・価格を出力から削除

**Status**: 完了
**Date**: 2026-10-20
**Next Action**: 完了（メモリバンク締結済み）

## 意図 / 背景

Gemini が生成する価格（frontmatter `product_recommendations` の `price_range`）は学習データ
由来で古情報・不正確。例: `src/content/posts/2026-10-19-100212-auto-post.md` の Gemini カード
「BEASTARS 1巻 / 500円台」が表示され、実際は楽天APIカードで全セット ¥14,817。
ユーザー要求: **Gemini に価格を出さない + スクリプト側も対応 + Gemini カードは名前のみ
（価格なし）で保持**（商品名は楽天APIカードのシードとして継続）。

## 調査結果 / 変更内容

### 現状のデータフロー（商品カードは現在 2 種）

1. **Gemini 商品カード（今回の対象: 価格表示だけ削除）**
   - `scripts/article/affiliate.py::process_product_cards()`（line 985）が frontmatter の
     `product_recommendations` をパースし、`generate_product_cards()`（line 936）で
     `name`＋`price_range` をカード化（画像なし・実アフィリエイトリンクなし・
     Amazon/楽天「検索」リンクのみ）。記事末尾に挿入
     （`generate_article.py` step 5.48 / line 389）。
   - **ユーザー確認: カードは残し、価格表示だけ削除。**
2. **楽天API 商品カード（現状どおり保持）**
   - `inject_affiliate_links()` → `_rakuten_api_keywords()`（line 508）が
     **Gemini 商品名をシードキーワード**として楽天APIカスケード検索し、
     `_generate_rakuten_card()`（line 327）で 実商品名・現在価格(`itemPrice`)・
     画像・実アフィリエイトリンク を生成。末尾アフィリエイトセクションに出す。

### 最終修正案

**1. プロンプト: Gemini の価格生成を止める**
各プロンプトの `product_recommendations` のサンプル frontmatter と指定ルールから
`price_range` を削除。Gemini は `name`・`category` のみ出力。
- `default.txt`: line 31, 55, 58, 75
- `ai_deep.txt`: line 37, 40, 52
- `kemono_story.txt`: line 87, 90, 109

**2. スクリプト側: 価格表示を削除し、カード（名前のみ）は保持**
| 対象 | 変更 |
|---|---|
| `affiliate.py::generate_product_cards()`（line 936） | 価格表示を削除: `price = prod.get("price_range", "")`、`price_html` 構築、テンプレート内の `{price_html}` を除去。カードは `name`＋検索リンク（Amazon/楽天）のみ。残り（カード構造・リンク・挿入）は維持 |
| `affiliate.py::extract_product_recommendations()`（line 892） | `price_range` パース（line 922-925）を削除。`name`・`category` は保持 |
| `affiliate.py::process_product_cards()`（line 985） | 変更なし（カード生成・ブロック削除・挿入は継続） |
| `generate_article.py` | 変更なし（import 維持、step 5.47 / 5.48 / 5.5 維持） |

**3. 表示されるもの（両方共存）**
1. Gemini カード: **名前のみ・価格なし**＋Amazon/楽天検索リンク — 記事末尾。
2. 楽天APIカード: 実商品名・**現在価格(¥)**・画像・実アフィリエイトリンク — アフィリエイトセクション。

**4. テスト**
- `test_generate_article.py`:
  - `_content`（line 1133）: 入力から price を除外し `price_range` 行を生成しない
    （新プロンプト出力と整合）。
  - `_assert_items`（line 1162）: `price_range` 断言を削除。
  - `test_card_count_and_price`（line 1309）: 件数・`pc-name` 断言を保持し、
    `pc-price` の非存在を断言へ。名称を `test_card_count_no_price` 等へ変更。
- `conftest.py`: `sample_product_recommendations`（line 114, 120）と
  `sample_product_cards_markdown`（line 228, 231）から `price_range` を削除。

### 備考・注意点
- `frontmatter.py::validate_and_fix_frontmatter`（line 305）が product_recommendations
  ブロック除去、修復 regex が `price_range`（line 321）も除去。重複しない。
- 楽天APIカードは Gemini 名をシードにしているため関連性は維持
  （実出力で「スターフォックス アサルト」「BEASTARS 1巻」から実商品取得済み）。
- 比較表 `AFF_PRODUCT`（`process_inline_products`）は別機構で対象外。
- 既出の古い記事の frontmatter には `price_range` が残るが、パーサーは無視
  （クラッシュなし）。再生成時にブロックは除去される。

## Verification（実装後）

- Python: 3.10（`C:\Users\fujim\AppData\Local\Programs\Python\Python310\python.exe`）
  （3.15 は使用しない / 3.15 の `python3` は `pillow_avif` 未インストールで非推奨）
- `python -m pytest scripts/tests/ -v`: **447 passed**（8.22s）
- `npm run build`: **154 page(s) built in 13.99s / Complete!**
- 変更確認:
  - 追加: 3つのテストメソッド（`test_missing_category`・`test_unquoted_values`・
    `test_card_count_no_price`）が直前のテストにネスト（余分インデント）化されていたため、
    pytest が収集しておらず dead code 化していたことを発見し、インデントを class レベルへ
    修正。修正後、3メソッドは収集・通過し、全件 **447 passed**（従来444 +3）
  - プロンプト 3 件に `price_range` 残存なし（grep 0 件）
  - `affiliate.py` の `generate_product_cards` に `price`/`price_html`/`{price_html}` 残存なし
  - テスト `test_card_count_no_price` が `pc-price` の非存在を断言し通過
  - 記事出力（既出 `2026-10-19-100212-auto-post.md` 等）の Gemini カードは
    実生成時のスナップショットであり、次回生成以降は価格なしとなる

## 完了時 Memory Bank 操作
- [x] `current-task.tsv` の参照行を削除（task_manager end で実施、ヘッダのみ）
- [x] 解決した `known-issues/` ファイルを archiveへ `mv` — 該当なし（本タスクは新規修正で issue なし）
- [x] `backlog.md` の完了項目を削除 — 該当なし（バックログ項目は作成していない）
