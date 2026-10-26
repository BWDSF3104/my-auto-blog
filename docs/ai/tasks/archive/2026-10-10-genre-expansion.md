# 2026-10-10: ストーリー系ジャンル拡大（世界設定7種・スコアリングgenre6種へ一括変更）

**Status**: 完了
**Next Action**: なし

## 背景

ストーリー系（kemono_story）の世界設定は fantasy/sf/slice_of_life/fantasy+sf の4種のみで、事前スコアリングの `cyberpunk` が未使用のままコストだけを消費していた。また `slice_of_life` が `[action]` にマッピングされ、日常世界にアクション高スコアのトレンドが優先される意味逆転バグが存在した。

ユーザー指示: Phase 1（cyberpunk + adventure 追加）と Phase 2（mystery + slice_of_life 修正）を実施。ジャンル追加はキャッシュキー（SHA256(text|genres)）変更で全エントリ失効→次回 deploy で全件再スコアリング（138 calls, ≈31s, 無料枠内）になるため、**一次性コストを1回にまとめる**方針。

## 変更内容

### スコアリング genre（`genre_score.py`、6種へ一括）

| genre | 状態 |
|---|---|
| sf / fantasy / cyberpunk / action | 既存（不変） |
| slice_of_life | **新設**（専用 instruction） |
| mystery | **新設**（専用 instruction、SFW: サスペンス・心理的緊張） |

- comedy/romance 等の未使用 genre は追加しない（cyberpunk と同じ「スコアリング済但未使用」の無駄を再現しない）

### 世界設定（`generate_article.py`、7種・重み合計100）

| key | 重み（旧→新） | WORLD_SETTING_GENRE_MAP | タグ |
|---|---|---|---|
| fantasy | 35→30 | [fantasy] | ファンタジー |
| slice_of_life | 25→22 | [action] → **[slice_of_life]**（意味逆転修正） | 日常 |
| sf | 20→15 | [sf] | SF |
| cyberpunk | —→12 | [cyberpunk]（新設・未使用genreを有効化） | サイバーパンク |
| adventure | —→8 | [action, fantasy]（新設・既存genreでカバー） | 冒険 |
| fantasy+sf | 20→8 | [fantasy, sf] | ファンタジーとSF |
| mystery | —→5 | [mystery]（新設） | ミステリー |

### 一次性コスト

- `DEFAULT_GENRES` 変更で `data/genre_scores/cache.json` の全エントリ失効
- 次回 `deploy.yml` の `score_topics()` で全件再スコアリング（119 topics + 19 copyrights = 138 API calls、≈31s、1call≈数 neurons → 無料枠 10,000 neurons/日の範囲内）

## 変更ファイル

- `scripts/genre_score.py`: `GENRE_INSTRUCTIONS` +2、`DEFAULT_GENRES` 6種化
- `scripts/generate_article.py`: `WORLD_SETTING_WEIGHTS` / `WORLD_SETTING_GENRE_MAP` / `_KEMONO_WORLD_TAGS`
- `scripts/tests/test_genre_score.py`: `test_default_genres` のセット断言更新
- `scripts/tests/test_generate_article.py`: `test_world_setting_in_options`（新3文字列）、`TestWorldSettingGenreMap`（slice_of_life 修正断言 + cyberpunk/adventure/mystery 3件追加）

## Verification

- `pytest scripts/tests/` → **308 passed** (3.81s)（GENRE_MAP 新テスト3件追加、TestScoreTopics のモックpayloadを `DEFAULT_GENRES` 派生へ更新4件）
- 実 API スモーク（clef-flash、`--no-cache`）:
  - "攻殻機動隊" → sf:81, cyberpunk:81, mystery:34, action:44, slice_of_life:16, fantasy:3（1021 input tokens ≈ 8 neurons）
  - "日常 四葉の妹" → slice_of_life:85, fantasy:28（新genreのinstructionが意図通り動作）
- 次回 `deploy.yml` 実行時に全件再スコアリングが発生（キャッシュキー変更による一次性コスト、138 calls ≈ 31s、無料枠内）

## コミット

`dde9c5b`（2026-10-10、`2026-10-10-world-setting-expansion.md` の12種拡大と同一コミットに集約）
