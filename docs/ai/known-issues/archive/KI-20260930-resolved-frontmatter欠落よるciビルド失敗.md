# frontmatter欠落によるCIビルド失敗

**Date**: 2026-09-30
**Status**: 解決済

Gemini APIの出力に`---`がない場合、`generate_article.py`の`content.replace("---", ...)`が何もしないままmdファイルが保存され、frontmatterのない記事が生成される。`PostLayout.astro`の`.split()`と`rss.xml.ts`の`escapeXml`がundefinedでクラッシュ。

- `PostLayout.astro`: `.split()`のnullチェックと関連記事フィルタのnull除外を追加
- `rss.xml.ts`: `title`, `pubDate`, `description`のデフォルト値を追加
- `generate_article.py`: `---`が出力にない場合、デフォルトfrontmatterを付与するガードを追加
