# 静的監査バグ修正

**Date**: 2026-09-30
**Status**: 解決済

ソースコードの静的解析で発見した Medium/Low バグを 5 件修正。テスト85件全件通過を確認。

- **M-1** `generate_article.py:L710` `_extract_article_body` regex: 閉じ `---` の後に改行がない場合にマッチしなかった。`re.DOTALL` のみ使用し、末尾の `\n` を `\n?` に変更。
- **M-2** `generate_article.py:L1410` `_validate_description` loop: 短い description 拡張時に同じ文を無限ループで繰り返した。`len(extended) + len(sentence) <= MAX_DESC_LEN` 条件を `next_ext` 事前チェックに置換。
- **L-1** `generate_article.py:L1370` `_extract_first_sentence_from_body`: `fm_end + 3` の offset 計算が frontmatter 形式に依存していた。`_extract_article_body()` を再利用するようにリファクタ。
- **L-2** `generate_article.py` `urllib.parse` の関数内インポート (4箇所): モジュールレベルのインポートに移動。
- **L-3** `generate_article.py:L407` `compose_image_prompt` の括弧正規表現: `re.search` で最初の括弧グループのみを取得していた。`re.findall` に変更して複数括弧グループに対応。`clean_situation` の除去も `re.sub` に変更。
