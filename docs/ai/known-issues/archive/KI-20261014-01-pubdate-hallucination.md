# LLM が pubDate をハルシネーションし誤った日付が記事に書き込まれる

**Date**: 2026-10-14

**症状**: 自動生成記事の frontmatter `pubDate` が生成日時と不一致になる
（2026-10-14 実行分: `2026-03-30 21:15:00`、本来 `2026-10-14 10:46:53`）。
過去に 2 件同種事象あり（2026-09-27-110240: 12:45:00 誤生成、
2026-10-06-160117: 16:30:00 誤生成）。誤った日付は GitHub Pages へデプロイされる。

**原因**:
1. pass1 の LLM（gemini-3.8-flash）がプロンプトに埋め込まれた正しい
   `pub_date_str` を無視し、独自の（丸い時刻の）日付を生成する。
2. pass2（refine）プロンプトに正しい pubDate が含まれず、誤値を維持する。
3. スクリプト側に pubDate を生成時刻へ強制する後処理が存在しない
   （slug は `_apply_slug_field` で強制されるが、pubDate には相当処理なし。
   `validate_and_fix_frontmatter` は YAML 構文検証のみ）。

**影響**:
- 記事表示日付の誤り（読者・SEO に影響）。
- `generate-search-index.js` の pubDate ソート順がずれる。
- `meta.py` の「直近 N 件」選定に軽微な影響。

**修正方針（実施済み）**: スクリプトで pubDate 行を `pub_date_str` に正規表現置換して
上書きする（slug 同様の強制処理）＋ 既存誤記事の手修正（本日分のみ）。
詳細: `docs/ai/tasks/2026-10-14-pubdate-hallucination.md`

**解決（2026-10-14）**:
- `scripts/generate_article.py` の `finalize_and_save()`（5.6.1）で
  `_apply_pubdate_field` により pubDate を生成時刻に強制する後処理を実装。
- 本日分記事 `2026-10-14-104653-auto-post.md` を正しい日付へ手修正。
- `TestApplyPubdateField` 6 テスト新設。pytest 397 passed、`npm run build` 成功、
  検索インデックスの日付降順を確認済み。
- 過去記事 2 件（09-27 / 10-06）は未修正（ユーザー指示により本日分のみ実施）。
