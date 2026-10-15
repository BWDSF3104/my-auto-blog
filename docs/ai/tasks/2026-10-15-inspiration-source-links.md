# 生成情報セクションに「インスピレーション元」リンクを追加

**Status**: 完了
**Date**: 2026-10-15

## 背景

記事末尾「生成情報」セクションに、記事作成のインスピレーション元（トレンドデータ＋e621 投稿）への
外部リンクを追加し、版権・出典の開示を正確にする。URL は Gemini 出力に依存せず、
収集データ（`data/topics/latest.json` / `data/character_features.json`）から Python 側で構築する。

計画書: `plans/2026-10-15-inspiration-source-links.md`（完了後に `plans/archive/` へ移動済み）

## 調査結果 / 変更内容

- `scripts/article/trends.py`
  - `_build_selection_lists`: `trend_topic_links: list[dict]`（`{"title", "source", "url"}`）を組立するよう追加
  - `_append_trending_topics`: 第4戻り値をタイトル文字列リストから dict リスト（`trend_topic_links`）に変更、docstring 更新
- `scripts/article/geninfo.py`
  - `_gen_info_trend_block`: `list[dict]` 受けに変更。url あり項目は `<a class="gen-info-link" target="_blank" rel="noopener nofollow">タイトル（ソース）↗</a>` で描画、url なしは素のテキスト
  - `_gen_info_e621_block`: 各参考キャラに「元投稿: `https://e621.net/posts/{id}` ↗」リンク行を追加（`post.id` から組立）。「人気版権」→「人気版権（プロンプトに使用）」「人気artist」→「人気artist（プロンプトに使用）」へ再ラベル（`_merge_copyrights` による注入リストを明示するため）
  - `_build_generation_info_section`: 引数を `trend_topics: list[dict]` へ変更
- `scripts/generate_article.py`: `finalize_and_save` の引数を `trend_topic_links` へ変更し、呼び出し箇所を同期
- `src/layouts/PostLayout.astro`: `.gen-info-link` CSS 追加（通常は本文色＋点線下線、hover で `--color-link` 色）
- `scripts/tests/test_generate_article.py`: geninfo 系テストを dict 形式・新ラベル・元投稿リンクの assert に更新

実装判断: 参考キャラごとの「作品」行は各投稿自身の版権（正確）を表示し、集計ベースの結合版権は
「（プロンプトに使用）」ラベルで区別する。

## Verification

- `pytest scripts/tests/ -v` → 404 passed
- `npm run build` → 成功（147 ページ、search-index 56 posts。`public/search-index.json` は本ビルドで
  2026-10-15-102240 生成分が追記された正当な差分）
- サンプル描画（`docs/ai/tmp/render_geninfo_sample.py`、実データ＋実パイプライン関数使用）で
  生成情報セクションの HTML をレンダリングし、Playwright スクリーンショットを撮影
- 画像解析（Groq `analyze_image_with_groq`）で検証 4 項目すべて「正常」:
  1. 「使用したトレンド情報」3 項目がソース名付き外部リンク（↗）
  2. 参考キャラ 1/2 各ブロックに `元投稿: e621.net/posts/{id} ↗` リンク
  3. 新ラベル「人気版権（プロンプトに使用）」「人気artist（プロンプトに使用）」表示
  4. 文字化け・レイアウト崩れなし
- スクリーンショットはユーザーへモバイルアプリ送信済み（確認済み）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] `plans/` の該当ファイルを `plans/archive/` へ `mv`
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当なし）
- [ ] `backlog.md` の完了項目を削除（P5 #8「情報源の明示」はトレンド側を一部カバーしたが、
      ユーザーが本タスクとして明示的に依頼した項目ではないため残置）
