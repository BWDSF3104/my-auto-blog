# 2026-10-16: 【直近の執筆作品】セクションを ENABLE_CHAR_DEDUP でゲート

**Status**: 完了（2026-10-16）
**Next Action**: なし

## 概要

ユーザー要望: 【直近の執筆作品（テーマ・展開被り防止）】セクション（物語系 kemono_story/novel/story に常時注入されるタイトルリスト）のプロンプト追加を、**既存の `ENABLE_CHAR_DEDUP` トグルで併せてゲート**する。新規トグルは作成しない（ユーザー指示）。

背景:
- 現状、物語系ではこのセクションが常時ONで、全生成プロンプトに直近5タイトルが注入されていた（`data/prompt_logs/2026-10-16-100918.txt:68-74` で確認）。
- キャラ・被り防止（`ENABLE_CHAR_DEDUP`、デフォルトOFF）は2026-10-13 にトグル化済み。今回の変更は同じトグルでタイトルリストも抑制する。

## 変更内容（予定）

- `scripts/generate_article.py`:
  - `build_ng_instruction`: 物語系ブランチの【直近の執筆作品】セクションを `ENABLE_CHAR_DEDUP` でゲート。OFF時は物語系で ng_instruction は空（非物語系の【重要：重複の禁止】は不変・常時ON）
  - `generate_post`: トグルOFF時の物語系は `get_recent_titles_by_type()` のファイルI/O自体をスキップ（メタ抽出スキップと同様の先行パターン）
- `scripts/article/config.py`:
  - `ENABLE_CHAR_DEDUP` のコメントを更新（ゲート対象セクションが2つになることを明記）
- `scripts/tests/test_generate_article.py`:
  - `TestBuildNgInstruction`: OFF時は【直近の執筆作品】も除外されることをアサート（現行 line 2206 のアサート反転）、ON時は両セクション出現をアサート

## 影響

- デフォルト（OFF）: 物語系プロンプトからタイトルリストが消える。ng_instruction はトレンドトピック（`_append_trending_topics`）のみになる可能性あり
- `ENABLE_CHAR_DEDUP=1` 時: 従来どおり両セクション注入
- 非物語系（default 等）: 【重要：重複の禁止】は常時ONのまま（スコープ外）

## Verification

- `python -m pytest scripts/tests/ -v` → 404 passed（8.15秒）
- `TestBuildNgInstruction` 5 件すべて通過（改名: `test_disabled_excludes_recent_and_char_sections` / `test_enabled_includes_recent_and_char_sections`）
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] `decisions/` 不要（既存トグル `ENABLE_CHAR_DEDUP` のスコープ拡張のみ。2026-10-13 前例と同様にタスクファイルで記録）
- [x] `backlog.md` 不要（#15 world_setting 除外とは別項目・保留のまま）
