# 既存記事のアフィリエイトリンク一括置換

**Date**: 2026-10-02
**Status**: 解決済

`scripts/fix_affiliate_links.py` で既存記事 15ファイル（48行）のアフィリエイトリンクを `[text](url)` から `<a href="url" target="_blank" rel="noopener noreferrer nofollow sponsored">text</a>` に一括置換。1ファイルで試験実行・差分確認後、全体適用。ビルド成功 (94ページ) を確認。
