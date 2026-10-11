# 2026-10-11: 記事末尾の生成情報に e621 からの使用データを載せる

**Status**: 完了 (2026-10-11)

## 概要

ユーザー要望: 記事末尾の「生成情報」セクションに、記事生成時に実際に使用した e621 からのデータ（e621 キャラクター特徴）を表示する。

現状: `generate_article.py` の `_load_character_features()` が `data/character_features.json`（e621 集計）からランダムに 2 投稿選出しプロンプト指示文を生成するが、プロンプト文字列を返すだけで選出データ自体は破棄されるため、記事には使用した e621 参考データが表示されない。

方針:
- `_load_character_features()` を 2 関数に分割:
  - `_select_character_features(target_genres) -> dict | None`: 読込・2 投稿選出・人気版権/artist 抽出の「データ選出」のみ（構造化 dict を返す）
  - `_format_character_features_instruction(info) -> str`: 選出 dict からプロンプト指示文を組立
  - `_load_character_features()` は両者のラッパーとして残す（既存テスト互換）
- `generate_post()` で `_select_character_features()` を 1 回だけ呼び出し、選出 dict を (1) プロンプトの `character_features_instruction`、(2) 生成情報セクションの両方に渡す（プロンプトと表示が同じ選出データになる）
- `_build_generation_info_section()` に `e621_info: dict | None = None` パラメータ追加。「参考キャラクターデータ（e621）」ブロックを表示（参考キャラ1/2: 種族・色・身体的特徴・参照・作品、人気版権、人気artist、データ時点）
- 表示条件: **kemono_story 記事のみ**（e621 データは kemono_story プロンプトの `{character_features_instruction}` 経由でしか使われないため）。非ケモノ記事では「使用したデータ」ではないため非表示
- データ時点は ISO 文字列を `YYYY-MM-DD HH:MM UTC` に整形表示（tz なし・パース不能は生表示）
- CSS 追加不要（既存 `.gen-info-block` / `.gen-info-dl` を流用）
- 既存記事: 影響なし（バックフィル不要）

## 実装

### `scripts/generate_article.py`
- `_load_character_features()` を分割:
  - `_select_character_features(target_genres) -> dict | None` 新設: 従来 `_load_character_features()` の読込・選出・版権/artist 抽出ロジックをそのまま移設し、`{updated_at, total_posts, raw_posts, posts, copyrights, artists}` dict を返す。ファイル不在・読込失敗・投稿空は `None`（従来は空文字列）
  - `_format_character_features_instruction(info) -> str` 新設: 従来 `lines` 組立ロジックを移設（`info` から各フィールド参照）。`None` は空文字列。ログ出力は `raw_posts` 経由で従来形式維持
  - `_load_character_features(target_genres)` は `_format_character_features_instruction(_select_character_features(target_genres))` のラッパー（既存テスト `TestLoadCharacterFeaturesGenre` 互換）
- `generate_post()`:
  - 「2. テキスト記事の生成」で `e621_info = _select_character_features(target_genres=target_genres)` を 1 回呼び出し、`template.format(character_features_instruction=_format_character_features_instruction(e621_info), ...)` に使用
  - 5.8 の `_build_generation_info_section(trend_topic_titles, prompt_type, kemono_params, content, e621_info)` に選出 dict を渡す
- `_build_generation_info_section()`:
  - 第5引数 `e621_info: dict | None = None` 追加（省略時=従来挙動）
  - `show_e621 = bool(e621_info) and prompt_type == "kemono_story"` で表示判定。空判定に `not show_e621` を追加
  - 「キャラクターデータ」ブロック直後に「参考キャラクターデータ（e621）」ブロックを追加: 参考キャラ1/2（種族/色/身体的特徴/参照/作品を `<br>` 連結・空フィールドは `-`）+ 人気版権 + 人気artist + データ（`datetime.fromisoformat` で UTC 整形、tz なしは `%Y-%m-%d %H:%M`、パース不能は生値）。`html.escape` 適用

### `scripts/tests/test_generate_article.py`
- `TestBuildGenerationInfoSection` に `E621_INFO` fixture + 4 テスト追加:
  - `test_e621_block_rendered`: 全項目表示（2投稿目の空フィールド「-」表示・UTC 整形日付）
  - `test_e621_block_omitted_for_non_kemono`: `default` 型では e621 ブロック非表示
  - `test_e621_only_section_shown`: e621 のみでもセクション表示
  - `test_e621_escaped`: e621 フィールド値の HTML エスケープ
- `TestSelectCharacterFeatures` 新設（6件・全モック/ローカルファイルのみ）:
  - `test_missing_file_returns_none` / `test_empty_posts_returns_none`: None 返却
  - `test_returns_structured_dict`: dict 構造・版権補完・artist 順
  - `test_format_instruction_none` / `test_format_instruction_content`: 指示文組立
  - `test_load_character_features_wrapper_uses_selection`: ラッパーが選出と同一データを使用（シード固定で検証）

### 不変（意図的）
- `fetch_topics.py`: 不変（e621 集計経路は既に分離済み・`character_features.json` スキーマ変更なし）
- `PostLayout.astro`: 不変（既存 `.gen-info` 系 CSS を流用）
- プロンプトテンプレート: 不変（`{character_features_instruction}` の文言は同一）
- 既存記事: バックフィル不要

## Verification

- `pytest scripts/tests/` → **365 passed** (7.00s)（ベースライン 355 + 新規 10）
- `npm run build`（一時記事 `2026-10-11-120000-e621geninfo-tmp.md` 投入時）→ **140 page(s) built** (2.89s) 成功
  - 出力 HTML 検証（`dist/posts/e621geninfo-verification-tmp/index.html`）:
    - `<details class="gen-info">` が `</article>` 直前に出力（本文末尾配置）
    - `open` 属性なし＝既定閉
    - セクション内に h2/h3/h4 なし（TOC への載入なし）
    - 「参考キャラクターデータ（e621）」ブロックに参考キャラ2投稿・人気版権・人気artist・データ時点（`2026-10-11 01:46 UTC（25投稿を分析）`）が実データで表示
- 一時記事・一時スクリプト削除後の再 `npm run build` → **138 page(s) built** (2.88s) 成功（クリーン状態確認）
- 実データ生成（Gemini API 経由の E2E）は次回 deploy 時に確認

## Next Action

- なし（次回 deploy 実行で実際に生成された記事の e621 ブロック表示を確認）
