# Description 検証のバグ

**Date**: 2026-09-30
**Status**: 解決済

- 無意味なパディング: 本文から最初の文を抽出する `_extract_first_sentence_from_body()` に置換
- 正規表現の脆弱性: `re.sub` 呼び出し前に `safe_corrected = corrected.replace("\\", "\\\\")` を追加
- 既存記事の修正: 独立スクリプトに保留
- LLM リトライ: スコープ外
