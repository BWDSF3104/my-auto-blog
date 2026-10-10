# 2026-10-10: 世界設定の2段階拡大（12種・アンカワーク基準）

**Status**: 完了（コミット未実施）
**Next Action**: なし

## 背景

`2026-10-10-genre-expansion.md`（7種・未コミット）の続き。ユーザー指摘:
1. 「現代（現代人獣社会）」と「歴史（時代・史前）」は追加決定
2. ケモノ作品と親和性の高い舞台をもう少し検討したい（例: ポケモンの不思議のダンジョン的世界）
3. スペースオペラも追加（Star Fox）
4. 「ニッチ」は追加しない理由としては弱い。ただし細分化しすぎるのも不好
5. ファンタジー・異世界方面のジャンルが少ない印象

## 判別基準（変更）

世界設定の追加基準を「ニッチかどうか」から以下の2条件に切り替え:
1. ケモノに独立した世界を定義する**アンカワーク**が存在する
2. プロンプトが**明確に異なる物語**を生む

## 変更内容

### 世界設定（7→12種、重み合計100）

| key | 重み | 追加種別 | アンカワーク / 根拠 | GENRE_MAP |
|---|---|---|---|---|
| fantasy | 21 | 既存（30→21） | — | [fantasy] |
| isekai | 10 | **新設** | 異世界転生・異世界冒険（ファンタジー族の読者目線ラベル、ユーザー指摘「異世界方面が薄い」への対応） | [fantasy, action] |
| modern | 10 | **新設**（追加決定） | Zootopia 系・現代人獣社会（furry 界で最も一般的な舞台） | [slice_of_life, action, mystery] |
| slice_of_life | 10 | 既存（22→10） | — | [slice_of_life] |
| sf | 8 | 既存（15→8） | — | [sf] |
| space_opera | 7 | **新設**（追加決定） | Star Fox（宇宙冒険・艦長物語） | [sf, action] |
| adventure | 7 | 既存（8→7） | — | [action, fantasy] |
| cyberpunk | 7 | 既存（12→7） | — | [cyberpunk] |
| dungeon_crawl | 6 | **新設** | ポケモンの不思議のダンジョン（モンスター主役＋ダンジョン攻略） | [fantasy, action] |
| mystery | 5 | 既存（据え置き） | Kemono Jihen | [mystery] |
| historical | 5 | **新設**（追加決定） | 史前獣人・戦国獣人 | [historical]（新 genre） |
| fantasy+sf | 4 | 既存（8→4） | — | [fantasy, sf] |

ファンタジー族（fantasy + isekai + dungeon_crawl + fantasy+sf）= 41/100 に拡大。

### スコアリング genre（6→7種）

- `historical` を新設（専用 instruction: 過去設定・時代劇・史前要素）
- 他新 world setting は既存 genre の複合マッピングで対応（再スコアリングコスト増なし）

### 見送り（「ニッチ」ではなく独立世界定義不足のため）

- メカ: Star Fox のメカ要素は space_opera に吸収。独立したケモノメカのアンカワークなし
- ポストアポカリプス: sf + action のバリアントで表現可能
- スポーツ: slice_of_life + action のバリアントで表現可能
- いずれも需要が観測されたら後日追加（新 genre 不要のはず）

### 一次性コスト

- 直前の 7種変更（未コミット・未デプロイ）と**同バッチ**のため、次回 `deploy.yml` の `score_topics()` で 7-genre 版の全件再スコアリングが**1回のみ**発生（6-genre 版の再スコアリングは支払われない）

## 変更ファイル

- `scripts/genre_score.py`: `GENRE_INSTRUCTIONS` +historical、`DEFAULT_GENRES` 7種化
- `scripts/generate_article.py`: `WORLD_SETTING_WEIGHTS` / `WORLD_SETTING_GENRE_MAP` / `_KEMONO_WORLD_TAGS`
- `.github/workflows/genre-score.yml`: genres デフォルト入力 7種化
- `scripts/tests/`: `TestWorldSettingGenreMap` +5、`test_world_setting_in_options` +5文字列、`test_default_genres` 7種化

## Verification

- `pytest scripts/tests/` → **315 passed** (4.08s)（GENRE_MAP テスト6件 + 重み合計100テスト + 全設定カバレッジテスト追加、`test_world_setting_in_options` を12文字列へ）
- 実 API スモーク（clef-flash、`--no-cache`、7genre）:
  - "戦国武将" → historical:80, action:45（新 genre `historical` の instruction が意図通り動作）
  - "スターフォックス" → action:69, sf:40, cyberpunk:32（`space_opera` → `[sf, action]` マッピングの妥当性確認）
- 直前の 6-genre 変更（`2026-10-10-genre-expansion.md`）と**同バッチ**（未コミットのまま）のため、次回 `deploy.yml` の `score_topics()` で 7-genre 版の全件再スコアリングが **1回のみ**発生

## コミット

未実施（ユーザー指示待ち）
