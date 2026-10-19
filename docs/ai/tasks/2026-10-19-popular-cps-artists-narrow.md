# 人気作品・artistのプロンプト注入件数を絞り（作品1-2件・artist1件、スコア優先）

**Status**: 完了
**Date**: 2026-10-19

## 意図 / 背景
kemono_story プロンプトに注込む人気作品（e621）と人気artist の件数制限を絞る。
現状は作品最大8件・artist 最大8件がカンマ区切りで注注入され、Gemini が有効に利用されない。
方針：人気作品は1-2件、人気artist は1件。
人気作品は**参考投稿の作品**が主で、参考投稿が作品を持たない時のみ**集計ベース（事前スコアリングで高スコア優先）**にフォールバックする。
人気キャラクターは本次の対象外（変更しない）。

## 現状（修正前）
- 参考投稿抽選（`_select_two_posts`, characters.py:71-90）: 1投稿乱数 → 2投稿乱数、**作品（コピーライト）重複時は最大10回再抽選**、失敗時は先頭2投稿を返す。投稿自体の重複は作品再抽選の副作用で間接防止。
- 人気作品（`_merge_copyrights` + `_filter_valid_copyrights`）: 参考投稿の版権（先頭）＋集計ベースの版権（後、投稿数降順→スコア順）をマージし**最大8件**注入。スコア優先は補完部分のみ。
- 人気artist（`_extract_top_artists`）: 投稿数上位**8件**注入（スコアリングなし）。

## 変更内容（確定済み仕様）
### 3.1 参考投稿抽選
- 変更: 2投稿の**異なる投稿**を乱数抽選。`random.sample(posts, 2)` で投稿自体の重複は構造的に防止。
- 作品（コピーライト）重複時の再抽選・失敗時フォールバックは**廃止**（作品重複を許容）。

### 3.2 人気作品
- 主: 参考投稿2件の作品を重複除去し**上位1-2件**（`POPULAR_CPS_LIMIT`=2）。集計ベースは使用しない。
- フォールバック: 参考投稿ともに作品がない場合のみ、集計ベースの**上位1-2件**（事前スコアで高スコア優先）。
- `_merge_copyrights` を廃止し、分岐を `_select_character_features` 内へ直接。

### 3.5 人気artist
- 投稿数上位**1件**（`POPULAR_ARTIST_LIMIT`=1）。同数時は件数降順→名前順。

### 変更対象ファイル
- `config.py`: 定数 `POPULAR_CPS_LIMIT`（既定2）、`POPULAR_ARTIST_LIMIT`（既定1）を追加（env で上書き可能）。
- `characters.py`:
  - `_select_two_posts`: `random.sample(posts, 2)` 化、再抽選・失敗時フォールバック削除（`len(posts) < 2` のみで全件返す安全策維持）。
  - `_merge_copyrights` 廃止、`_select_character_features` に「参考投稿作品非空ならその1-2件、なければ集計上位1-2件（スコア順）」の分岐を直接埋める。
  - `_extract_top_artists`: 上位8→上位1、同数時は件数降順→名前順。
- テスト `scripts/tests/test_generate_article.py`:
  - `test_returns_structured_dict`: 人気作品1-2件・artist1件の期待値更新。抽選は `random.seed` で固定し再検証。
  - `test_format_instruction_content`: 期待値更新（作品1-2件・artist1件）。
  - `E621_INFO` フィクスチャ: `artists` を `"artist_a, artist_b"`→`"artist_a"`、関連 assert（3414/3415/3445/3446）更新。
  - **新規テスト**: 参考投稿に作品なし時のフォールバック（集計上位1-2件・スコア順）の検証。

## 前提・関連
- 事前スコアリング: 収集済みコピーライト 23件すべてが `data/genre_scores/topics.json`（copyrights 23件）にカバー（23/23、2026-10-19 01:02 UTC 取得）。
- `generate_article.py` の import リスト（line 117-122: `_extract_top_artists` / `_filter_valid_copyrights` / `_merge_copyrights`）は re-export のみで直接不使用 → 廃止しても影響なし（実装時に再確認）。
- 生成情報表示（geninfo.py）とプロンプトテンプレは変更なし。

## Verification
- 検証日: 2026-10-19
- **pytest**: `pytest scripts/tests/ -q` → **447 passed** (8.11s)（Python 変更 → 全テスト通過）
- 対象テスト:
  - `TestSelectCharacterFeatures`（9件）: 変更した選択ロジック（人気作品1-2件・artist1件）+ 新規フォールバックテスト3件（参考投稿に作品なし→集計スコア順上位2件 / 未スコア→投稿数順上位2件 / 1投稿のみ作品→1件）
- **実データ検証**（`docs/ai/tmp/verify_popular_cps.py`）:
  - `target_genres=None` → 人気作品 `sega, sonic_the_hedgehog_(series)`（選出投稿の作品上位2）、artist `badwing`（上位1）
  - `target_genres=['fantasy']` → 人気作品 `"five_nights_at_freddy's, scottgames"`（選出投稿の作品上位2）
  - 実データは全24投稿のうち15件が作品あり → 参考投稿の作品が主となるケース確認
- 変更ファイル: `scripts/article/config.py` / `scripts/article/characters.py` / `scripts/generate_article.py` / `scripts/tests/test_generate_article.py`
- 未対応: git commit（ユーザー承認待ち）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
