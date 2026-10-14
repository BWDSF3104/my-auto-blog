# 記事 pubDate の日付誤り調査（2026-10-14 実行分）

**Status**: 修正完了（原因特定済み・pubDate 強制後処理を実装・本日分手修正・検証済み）
**Date**: 2026-10-14

## 背景

2026-10-14 実行分の Auto Generate Content and Deploy で生成された
`src/content/posts/2026-10-14-104653-auto-post.md` の frontmatter
`pubDate: "2026-03-30 21:15:00"` が生成日時（2026-10-14 10:46:53 JST）と
一致しておらず、GitHub Pages に誤った日付で配信された。

## 調査結果

### 事実関係（証拠）

| 項目 | 値 | 出所 |
|------|-----|------|
| スクリプト計算値 | `2026-10-14 10:46:53` | `scripts/generate_article.py:437` |
| プロンプトへの埋め込み | `pubDate: "2026-10-14 10:46:53"`（正しく埋め込まれている） | `data/prompt_logs/2026-10-14-104653.txt:84` |
| pass1 出力（下書き） | `pubDate: "2026-03-30 21:15:00"`（**ここで誤生成**） | `data/drafts/2026-10-14-104653.json` pass1, model=gemini-3.8-flash |
| pass2 出力（精製） | 同上（誤った値をそのまま維持） | 同上 pass2 |
| 最終記事 | `pubDate: "2026-03-30 21:15:00"` | `src/content/posts/2026-10-14-104653-auto-post.md:8` |
| デプロイ | 誤った日付のままコミット・配信済み | commit `55d0fd5`（2026-10-14 01:50 UTC） |

### 原因（連鎖）

1. `generate_post()` が正しく `pub_date_str`（JST 現在時刻）を計算し、
   プロンプトテンプレート（`scripts/prompts/kemono_story.txt:74` の
   `pubDate: "{pub_date_str}"`）に埋め込んでいる。
2. **pass1 の LLM（gemini-3.8-flash）が指示された日付を無視し、
   独自の日付 `2026-03-30 21:15:00` をハルシネーションした。**
   （「21:15:00」のような丸い時刻は LLM 生成の典型パターン）
3. **pass2（refine）のプロンプト（`scripts/prompts/refine_story.txt`）には
   正しい pubDate が含まれず、「Frontmatter を維持せよ」という指示のみで、
   誤った値をただ受け継いだ。**
4. **スクリプト側に pubDate を生成時刻へ強制する後処理が存在しない。**
   `validate_and_fix_frontmatter`（`scripts/article/frontmatter.py`）は
   YAML の構文検証のみで、値の正確性は検査しない。
   slug（`_apply_slug_field`）はスクリプト側で検証・上書きされるが、
   pubDate に相当する処理はない。

### 過去にも同種事象を確認（全記事スキャンの結果）

| ファイル | 実際の pubDate | 本来の日時（ファイル名） |
|----------|---------------|------------------------|
| `2026-09-27-110240-auto-post.md` | 2026-09-27 **12:45:00** | 11:02:40 |
| `2026-10-06-160117-auto-post.md` | 2026-10-06 **16:30:00** | 16:01:17 |
| `2026-10-14-104653-auto-post.md` | **2026-03-30** 21:15:00 | 2026-10-14 10:46:53 |

（2026-10-14 以外の記事はすべて pubDate とファイル名が一致。）

### 影響

- 記事が誤った日付（3 月）で表示される。
- `scripts/generate-search-index.js:49` が pubDate で降順ソートするため、
  検索インデックス上で 3 月分の記事として扱われる。
- `scripts/article/meta.py:68`（`get_existing_posts`）も pubDate 文字列で
  ソートするため、重複防止の「直近 N 件」の選定に軽微な影響がある。

## 修正方針（実施済み）

1. **（実施）スクリプトで pubDate を強制**: `finalize_and_save()`（保存直前の
   最終検証ステップ）内で、`pubDate` 行を `pub_date_str` に正規表現置換して
   上書きする後処理 `_apply_pubdate_field(content, pub_date_str)` を新設
   （slug 同様の仕組み）。`pubDate` 行が欠落した場合は title 行の直後
   （title もない場合は frontmatter 開始直後）に挿入する。
   LLM の出力に依存しない根本対策。
   - `scripts/generate_article.py`: `_apply_pubdate_field` 新設＋`finalize_and_save`
     に `pub_date_str` を引数追加し 5.6.1 で強制（呼び出し側 `generate_post` も更新）。
   - `scripts/tests/test_generate_article.py`: `TestApplyPubdateField` 6 テスト新設。
2. **（実施・本日分のみ）** 本日分記事 `2026-10-14-104653-auto-post.md` の
   pubDate を `2026-03-30 21:15:00` → `2026-10-14 10:46:53` へ手修正。
   過去記事 2 件（09-27 / 10-06）はユーザー指示により修正対象外。
3. （未実施・任意）refine プロンプトに正しい pubDate を含め、pass2 側でも
   是正できる構成にする。

## Verification

### 調査フェーズ
- 調査のみ（ファイル変更・コード変更なし）のため pytest / build 不要。
- 証拠確認: prompt_log / draft JSON / 記事本体 / 全記事スキャン / git log。

### 修正フェーズ（2026-10-14）
- `python -m py_compile scripts/generate_article.py` → OK
- `python -m pytest scripts/tests/ -q` → **397 passed**（7.63s、新設 `TestApplyPubdateField` 6 件を含む）
- `python -m pytest scripts/tests/test_generate_article.py::TestApplyPubdateField -v` → **6 passed**（0.93s）
- `npm run build` → **145 page(s) built in 3.39s / Complete!**
- 効果確認: `dist/search-index.json` で本日分記事が `2026-10-14 10:46:53` で
  最新として先頭に表示され、日付降順が正しい（10-14 → 10-13 → 10-12 → …）。
