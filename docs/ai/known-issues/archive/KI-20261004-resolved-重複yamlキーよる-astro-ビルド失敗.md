# 重複YAMLキーによる Astro ビルド失敗

**Date**: 2026-10-04
**Status**: 解決済

AI がプロンプト指示の `character_1`/`character_2` を無視し、キャラクタータイプ名（例: `少年:`）を YAML キーとして出力。2人以上のキャラクターでキーが重複し、Astro/Vite が `duplicated mapping key` エラーでビルド中断。

- `scripts/generate_article.py` に `_fix_duplicate_yaml_keys()` と `_is_character_like_key()` を実装
- `validate_and_fix_frontmatter()` 内で `safe_load` 前に重複チェックを无条件実行
- 破損記事 `2026-10-04-112752-auto-post.md` を手動修正（`少年:` → `character_1:`/`character_2:`）
- テスト110件全通、ビルド成功、デプロイ完了を確認
