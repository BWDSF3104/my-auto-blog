# 画像プロンプトに場面ごとの表情/ポーズ指定を追加 (2026-10-09)

**状態: 実装完了・pytest＋実Gemini出力検証済み (2026-10-09)。** 生成画像の見た目（E2E）未検証。

## 背景

kemono_story の画像プロンプトは `[character_1, character_2] scene` 形式で、各キャラクターの表情データがなかった。生成画像の2匹は同じ表情・または場面に無関係な表情になりがちで、ストーリー再現度が低下していた。

## 要件（ユーザー）

- 2匹それぞれの表情を場面ごとに指定（各1-2タグ、Danbooru実在タグ）
- 2匹で表情が同じ場合は1回指定で可
- 表情はその場面の感情・緊張感・関係性に一致させる
- ポーズの追加も行う（2026-10-09 追加指示）
- 既存のプロンプト合成順序は維持（キャラ及びシチュエーションの再現度を最優先）
- `app.py`（HF Space）は変更しない

## 設計

### 括弧形式（3種）

| 形式 | 意味 |
|------|------|
| `[character_1: blushing, smile, character_2: frown, narrowed eyes] scene` | キャラ別表情/ポーズ（コロン区切り） |
| `[character_1, character_2, smile] scene` | 共有表情/ポーズ（コロンなし・末尾エントリ） |
| `[character_1, character_2] scene` | legacy（後方互換） |

- コロンモード: エントリは直前のキャラIDに属する（次のキャラIDまで）
- コロンなしモード: キャラ参照以外のカンマエントリは全キャラ共通タグ
- ポーズ: キャラ別ポーズ（standing, sitting 等）は括弧内、相互作用ポーズ（hugging, facing each other 等）はシーンキーワード

### 合成順序（変更なし）

`被写体数 → キャラ1外見 → キャラ1表情/ポーズ → キャラ2外見 → キャラ2表情/ポーズ → (共有) → シーン → artist → quality → style`
- 全キャラの表情が同一の場合 → キャラブロックの後に1回だけ出力（dedupe）

## 実装内容

### `scripts/prompts/kemono_story.txt`

- 【キャラクターの一貫性と画像プロンプトのルール】に2項目追加:
  - 「各キャラクターの場面ごとの表情」: Danbooru実在タグ（英語）、1人1-2個、場面の感情に一致、2匹で同じ場合は1回だけ。具体例2つ（異なる/同じ）
  - 「シーンキーワードは、ポーズ/アクション、相互作用、背景、構図、光、などの簡潔なタグで構成」: 背景は93行目（キャラ定義から背景を除外）と補完関係
- 例を4箇所更新（挿入形式・frontmatter例・章例3つ、異なる形式を混在させて両形式を学習させる）
- 冗長な表情具体例リストは削除（ユーザー修正）。22行目の「Danbooru互換タグ形式」ルール＋「実在タグ」要求＋具体例2つで十分と判断

### `scripts/generate_article.py`

- `_parse_image_prompt_targets(bracket_content, characters)` 新設: `(target_chars, per_char_tags, shared_tags)` を返す。コロン（全角/半角）・`、`/`&`区切り・legacy部分一致に対応
- `compose_image_prompt`:
  - 括弧解析を新ヘルパーへ置換
  - 1人分岐: 外見の直後に per-char / shared タグを付与
  - 2人以上分岐: 各キャラ外見の直後に per-char タグをインターリーブ、全同一時はdedupe、shared タグはキャラブロック後に付与

### テスト (`scripts/tests/test_generate_article.py`)

新規5件（`TestComposeImagePrompt`）:
- `test_compose_per_character_expressions`: インターリーブ順序
- `test_compose_single_character_expression`: 単独キャラ
- `test_compose_same_expression_dedup`: 同一表情は1回のみ
- `test_compose_shared_expression`: コロンなし共有形式
- `test_compose_legacy_format_without_expressions`: 旧形式後方互換

## Verification

- `pytest scripts/tests/` → **200 passed** (3.79s)（変更前: 195）
- `pytest scripts/tests/test_generate_article.py::TestComposeImagePrompt` → 9 passed
- 実Gemini API検証 (2026-10-09, ローカル): `generate_post` と同一のプロンプト構築（獣人/ハーフ + ファンタジーとSF + TSF + 相棒関係 + 2人）を再現しGeminiを1回呼び出し（gemini-3.6-flash、101.4s。3.8-flashは3回失敗してフォールバック）
  - 全6画像プロンプト（ヘッダー1 + 本文内5）が**個別指定形式（コロン）**で出力、100%遵守
  - `compose_image_prompt` のインターリーブ順序・既存順序維持・シーンとの表情一致を実出力で確認（例: desperate, straining + 崩落天井シーン）
  - ポーズも反映（mid-air, combat stance, head pat, standing side by side 等）
  - 軽微な逸脱: gentle smile（Danbooru単一タグでない自然言語句）1件。シーンキーワードに自然言語句2件（既存ルールの逸脱で本変更の範囲外）
  - 共有形式・legacy・dedupe パスは単体テストでカバー（実出力では未使用）
  - 出力保存: `C:\Users\fujim\AppData\Local\Temp\kilo\gemini_real_output.md`（ローカルのみ）

## 未検証

- E2E（GitHub Actions）: 生成画像の見た目（表情/ポーズが画像に反映されるか）
- Nova-Furry-XL が表情タグに反応するか（ベストプラクティス調査では期待できるが実測なし）
