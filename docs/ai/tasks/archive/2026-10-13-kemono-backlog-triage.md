# 2026-10-13: kemono バックログ4項目のトリアージ（キス追加・TFタグ修正・2項目のバックログ登録）

**Status**: 完了（2026-10-13）
**Next Action**: なし（既存記事の TF/TSF タグ遡及修正はユーザー判断待ち）

## 概要

ユーザー提示の4項目を2026-10-13に調査（調査結果は会話ログ参照）。ユーザーのトリアージ決定:

1. **e621 キャラクター名の「寄せる」指示**: 低優先度・様子見（直近の改修で改善の可能性）。→ backlog P3 登録
2. **ストーリー種族の絞り込み（Danbooru/e621 主要種族タグリスト化）**: 採用見送り・不採用見込みの低優先度。→ backlog P3 登録
3. **密着系シチュエーションへのキス追加**: 実施（現状記載を確認して追記。衝突時の誤ったキス等）
4. **最新記事の TF タグ欠落**: 「タグ設定入れ忘れ」と確認 → 修正実施

## 変更内容

- `scripts/prompts/kemono_story.txt`: 「緊張感ある密着」カテゴリに「衝突時の誤ったキス」を追加（16行）
- `scripts/article/config.py`: 新定数 `_KEMONO_TRANSFORM_TAGS`（none→[], tf→["TF"], tsf→["TSF"], tf+tsf→["TF","TSF"]）+ `__all__` 更新
- `scripts/article/image.py`: `_build_kemono_tags` に transform タグを組み込み（生成順 4. 変身タグ）
- `scripts/tests/test_generate_article.py`: TestBuildKemonoTags に transform テスト4件追加
- `docs/ai/backlog.md`: P3 #9（e621 キャラ名・様子見）/ P3 #10（種族絞り込み・採用見送り）登録
- `docs/ai/known-issues/KI-20261013-01-tf-tags-missing.md`: 作成（解決済）

## Verification

- `python -m pytest scripts/tests/ -q` → 391 passed（約7秒、新規 transform テスト4件含む）
- transform 関連単独: `pytest scripts/tests/test_generate_article.py -k "transform" -q` → 6 passed
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要

## 備考

- TF/TSF タグは `/` を含まないため `apply_frontmatter_fields` の `replace("/", "・")` は無影響
- 既存記事（10-08 以降、変身あり記事）のタグ遡及修正は未実施（ユーザー判断待ち）
