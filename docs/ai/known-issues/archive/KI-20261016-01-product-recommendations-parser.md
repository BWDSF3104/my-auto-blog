# product_recommendations パーサーが category/price_range・2項目目以降を落とす

**Date**: 2026-10-16
**状態**: 解決済み（2026-10-19）。commit `d1027b6` で修正し、全テスト（441 passed）で検証済み。

**症状**: frontmatter の `product_recommendations` にプロンプト指定形式（2-3商品、各 `name`/`category`/`price_range`）が出力されていても、商品カードは1枚目の name のみで生成される（category は既定値「商品」に、price_range は喪失）。

**原因**: `extract_product_recommendations`（`scripts/article/affiliate.py`）のブロック抽出正規表現 `r'^product_recommendations:\s*\n((?:\s*-\s+.*\n?)+)'` が `- ` 始まりの行のみ連続キャプチャするため、`category:` / `price_range:` の継続行でキャプチャが途切れ、2項目目以降もブロック外になる。

**影響**: 商品カードの品質低下（カテゴリ・価格帯の非表示）。楽天APIカスケードの Gemini 商品名抽出（`postprocess_content` の `gemini_product_names`）は name のみ使用する影響を受けない（ただし2項目目の商品名がカスケードから消える）。

**修正方針**: ブロック抽出を `product_recommendations:` の次ブロック開始（次の frontmatter キーまたは `---`）までキャプチャする形に修正し、`- name:` 起点の項目を `category:` / `price_range:` 継続行とペアでパースする。テスト追加（プロンプト指定形式の複数項目 round-trip）。

## 解決（2026-10-19）

- commit `d1027b6`（2026-10-19）: `extract_product_recommendations`（`scripts/article/affiliate.py:865` の `_product_rec_block_span`）にブロック範囲の span 取得を実装し、キー行〜次のトップレベルキー/`---` までキャプチャ。`- name:` 起点の項目を `category:` / `price_range:` 継続行とペアでパース。
- `postprocess_content`（商品名をマークアップへ復元する処理）も同一 span で削除し、フロントマターの整合性を確保。
- kemono_story プロンプトを「1つ以上」に変更し、複数項目の生成も確認。
- テスト追加: `scripts/tests/test_generate_article.py` の product_recommendations パーサー tests（18件、プロンプト指定形式の複数項目 round-trip を含む）+ 全スイート **441 passed**（2026-10-19 01:00 再検証）。

## 対応状況

- 2026-10-16: 発生確認。
- 2026-10-19: commit `d1027b6` で修正・テスト追加。全テスト通過で検証完了。`known-issues/archive/` へ移動しクローズ。
