# 2026-10-10: 記事末尾の「生成情報」セクション追加（トレンド情報＋キャラクターデータ）

## 概要

ユーザー要望: 記事の一番下（SNS共有の手前相当）に、記事生成に使った「トレンド情報」と「キャラクターデータ」を表示するセクションを追加。

設計決定（ユーザー承認済み 2026-10-10）:
- 表示項目: **トレンド情報＋キャラデータのみ**（AIモデル・art_style・seed・生成時間は不要）
- スタイル: `<details>` **折りたたみ・既定閉**（TOC に出ていない h2〜h4 を使わない）
- 生成方法: **Python スクリプト側がセクション HTML を生成し、本文末尾に追記**（ユーザー指示「生成情報の作成はPythonスクリプト側で行う」。frontmatter 拡張＋Layout 描画方式は不採用）
- 既存記事: **バックフィル不要**（新フィールドなし・セクションは本文に直接入るため既存記事は非表示）
- 配置: 本文末尾（関連記事の手前・SNS共有より上）。ユーザー指定「SNS共有の手前」は Layout 側配置だが、Python 側生成の指示により本文末尾に配置

## 実装

### `scripts/generate_article.py`
- `import html` 追加（モジュール冒頭）
- `_KEMONO_TRANSFORM_LABEL` 定数新設（:191 付近、`_KEMONO_TRANSFORM_TEXT` 直後）: `none`→「なし」/ `tf`→「TF（変身・変形）」/ `tsf`→「TSF（性転換フィクション）」/ `tf+tsf`→「TF・TSF」。既存の `transform_text` は「、」接頭のプロンプト結合文字列のため表示に不適で、生成情報用として分離
- `_append_trending_topics()`（:2244 付近）を 3→4 タプル化:
  - 戻り値 `tuple[str, list[str], list[str]]` → `tuple[str, list[str], list[str], list[str]]`
  - 第4要素 `trend_topic_titles`: 選択された各トレンドのクリーンタイトル `"{title}（{source}）"` 形式（source 空ならタイトルのみ）
  - 全4 return（file_not_found / json_parse_error / selected 0件 / 通常）を更新
- 新ヘルパー `_build_generation_info_section(trend_topic_titles, prompt_type, kemono_params, content)` 追加（`_append_trending_topics` 直後）:
  - `<details class="gen-info">` 折りたたみセクション HTML を組立（既定閉・h2〜h4 不使用のため TOC 非載入）
  - 「使用したトレンド情報」ブロック: `<ul>` でトレンドタイトル列挙（`html.escape` 済み）
  - 「キャラクターデータ」ブロック: `<dl>` で体型（`char_type`）/ 世界設定（`world_setting`）/ 変身（`_KEMONO_TRANSFORM_LABEL`）/ 関係性（`relationship_text`）/ 追加設定（`extra_key != "none"` のみ・`extra_tag`）+ frontmatter の `character_1` / `character_2`（`_extract_fm_field` で抽出）
  - 非ケモノ系: キャラ設定行なし（トレンド情報のみの場合あり）
  - 表示要素が一切ない場合は空文字列を返す（セクション非表示・既存記事影響なし）
- `generate_post()`:
  - 1.6 の `_append_trending_topics` 呼び出しを 4 タプル unpack に更新
  - 5.8 として「6. 保存」直前に追記処理: `gen_section = _build_generation_info_section(...)` → 空でなければ `content.rstrip() + "\n\n" + gen_section + "\n"`（FAQ / speakable / 内部リンク等の本文解析はすべてこの前に実行済みのため影響なし）

### `src/layouts/PostLayout.astro`
- `<style is:global>` に `.gen-info` 系 CSS 追加（`</style>` 直前）: ボックス（`--color-bg-alt` 背景・`--color-border` 枠・角丸）・summary（矢印 ▸ → 開閉回転アニメーション）・`gen-info-list` / `gen-info-dl`（dt 固定幅の縦積み行）。Astro は `is:global` スタイルをページ HTML にインライン出力
- 本文描画・TOC・JSON-LD・関連記事・SNS共有セクションは変更なし（セクションは本文 Markdown 内に直接入るため）

### `scripts/tests/test_generate_article.py`
- `_append_trending_topics` の 3 タプル unpack 5 箇所（:2550 / :2576 / :2608 / :2624 / :2640）を 4 タプルに更新（:2657 は unpack しないため不変）
- `test_genre_filter_applied` / `test_no_genre_scores_falls_back_to_random` に第4要素アサート追加（`"{title}（rss）"` 形式）
- 新テストクラス `TestBuildGenerationInfoSection`（6件）:
  - `test_kemono_full`: 全5設定行＋キャラ2件＋トレンド2件の表示
  - `test_transform_none_shows_nashi`: `transform_key=none` で「なし」表示
  - `test_extra_none_omitted`: `extra_key=none` で「追加設定」行非表示
  - `test_trend_only_non_kemono`: 非ケモノ系はトレンド情報のみのセクション
  - `test_empty_returns_empty_string`: 表示要素なしで空文字列（非表示）
  - `test_html_escaped`: タイトル・キャラ値の HTML エスケープ（`<script>` 注入対策）

### 不変（意図的）
- frontmatter スキーマ: 新フィールド追加なし（セクションは本文に直接入るため）
- 既存記事: バックフィル不要（セクションが存在しないため自動的に非表示）
- TOC JS（h2/h3/h4 抽出）: セクションに見出し要素がないため影響なし

## Verification

- `pytest scripts/tests/ -v` → **355 passed** (7.11s)（ベースライン 349 + 新規 6）
- `npm run build`（一時記事 `2026-10-10-180000-geninfo-tmp.md` 投入時）→ **137 page(s) built** (9.99s) 成功
  - 出力 HTML 検証（`dist/posts/geninfo-verification-tmp/index.html`）:
    - `<details class="gen-info">` が `<article>` 内・本文末尾に出力（`</article>` の直前、関連記事・サポートボックスより上）
    - `open` 属性なし＝既定閉
    - セクション内に h2/h3/h4 なし（TOC への載入なしを確認）
    - `.gen-info` CSS がページ HTML にインライン出力（旧記事ページにもグローバルとして出力・既存スタイル破損なし）
- 一時記事・一時スクリプト削除後の再 `npm run build` → **135 page(s) built** (2.80s) 成功（クリーン状態確認）
- 実データ生成（Gemini API 経由の E2E）は次回 deploy 時に確認

## Next Action

- 次回 deploy 実行で実際に生成された記事のセクション表示を確認
