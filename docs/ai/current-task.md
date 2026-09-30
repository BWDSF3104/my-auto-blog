# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

静的監査バグの修正（Medium/Low 項目 5件）

## Priority

P1

## Status

完了

## Objective

ソースコードの静的解析で発見した Medium/Low バグを修正:
1. `_extract_article_body` regex: 閉じ `---` の後に改行がない場合にマッチしない問題を修正
2. `_validate_description` loop: 短い description 拡張時に同じ文を繰り返す問題を修正
3. `_extract_first_sentence_from_body`: offset 計算を `_extract_article_body` にリファクタ
4. `urllib.parse` の関数内インポートをモジュールレベルに移動
5. `compose_image_prompt` の括弧正規表現を複数グループ対応に修正

## Requirements

- 既存のテスト85件を全件通過させる
- 動作変更はバグ修正のみに限定

## Modified Files

- `scripts/generate_article.py` - 上記5件のバグ修正
- `docs/ai/current-task.md`
- `docs/ai/known-issues.md`

## Completed

- [x] 現状調査：generate_article.py のバグ箇所を grep/読取で特定
- [x] 実装1: `_extract_article_body` regex の末尾 `\n` を `\n?` に変更
- [x] 実装2: `_validate_description` loop の条件を `next_ext` 事前チェックに置換
- [x] 実装3: `_extract_first_sentence_from_body` を `_extract_article_body` 再利用にリファクタ
- [x] 実装4: `urllib.parse` の関数内インポート (4箇所) をモジュールレベルに移動
- [x] 実装5: `compose_image_prompt` の `re.search` を `re.findall` に変更、`clean_situation` を `re.sub` に変更
- [x] テスト検証: 85 tests passed
- [x] docs/ai/ 更新

## Pending

(なし)

## Verification

Test: 85 tests passed in 1.22s

## Next Action

(なし)

## Commit

e2f4219

## Notes

- `_extract_article_body` の regex は `re.MULTILINE` を削除し `re.DOTALL` のみに変更（`^` は文字列先頭のみで十分）
- `_extract_first_sentence_from_body` は frontmatter 除去ロジックを `_extract_article_body` に一元化
- `compose_image_prompt` は `re.findall` で複数括弧グループに対応、`clean_situation` も `re.sub` で全括弧を除去
