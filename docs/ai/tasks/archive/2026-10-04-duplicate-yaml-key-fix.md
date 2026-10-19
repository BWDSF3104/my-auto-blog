# 重複YAMLキーによるビルド失敗の修正 (2026-10-04)

**Status**: 完了

**Summary**:
- AI がプロンプト指示の `character_1`/`character_2` を無視し、キャラクタータイプ名（例: `少年:`）を YAML キーとして出力
- 2人以上のキャラクターでキーが重複し、Astro/Vite が `duplicated mapping key` エラーでビルド中断
- `generate_article.py` に自動修復ロジックを実装し、破損記事を手動修正
- Git リベース時の PowerShell エディタフリーズを回避するため、`git merge` に切り替え
- リモートリポジトリにも同様の破損ファイルが存在していたため、手動での個別修正が必要

**Files Changed**:
- `scripts/generate_article.py`: `_fix_duplicate_yaml_keys()` と `_is_character_like_key()` を追加、`validate_and_fix_frontmatter()` に重複チェックを組み込み
- `src/content/posts/2026-10-04-112752-auto-post.md`: 重複キーを手動修正（`少年:` → `character_1:`/`character_2:`）
- `scripts/tests/test_generate_article.py`: 重複キー修復のテストケースを追加

**Verification**:
- `pytest scripts/tests/ -v`: 110件全パス
- `npm run build`: 成功
- `git push`: 成功、GitHub Actions deploy-only.yml 再トリガー
