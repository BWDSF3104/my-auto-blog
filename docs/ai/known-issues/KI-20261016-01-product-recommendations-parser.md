# product_recommendations パーサーが category/price_range・2項目目以降を落とす

**Date**: 2026-10-16

**症状**: frontmatter の `product_recommendations` にプロンプト指定形式（2-3商品、各 `name`/`category`/`price_range`）が出力されていても、商品カードは1枚目の name のみで生成される（category は既定値「商品」に、price_range は喪失）。

**原因**: `extract_product_recommendations`（`scripts/article/affiliate.py`）のブロック抽出正規表現 `r'^product_recommendations:\s*\n((?:\s*-\s+.*\n?)+)'` が `- ` 始まりの行のみ連続キャプチャするため、`category:` / `price_range:` の継続行でキャプチャが途切れ、2項目目以降もブロック外になる。

**影響**: 商品カードの品質低下（カテゴリ・価格帯の非表示）。楽天APIカスケードの Gemini 商品名抽出（`postprocess_content` の `gemini_product_names`）は name のみ使用する影響を受けない（ただし2項目目の商品名がカスケードから消える）。

**修正方針**: ブロック抽出を `product_recommendations:` の次ブロック開始（次の frontmatter キーまたは `---`）までキャプチャする形に修正し、`- name:` 起点の項目を `category:` / `price_range:` 継続行とペアでパースする。テスト追加（プロンプト指定形式の複数項目 round-trip）。
