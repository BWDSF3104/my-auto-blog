# e621 データのトレンド配管からの分離

**Date**: 2026-10-10

**Decision**: e621 を `latest.json` から完全排除（収集は継続・キャラクター特徴集計用）。`NON_TREND_SOURCES = {"e621"}` 新設、出力構築前に `sources`/`merged_by_category`/`all_topics_merged` をフィルタ。

**Reason**: e621 は「キャラクター特徴集計」専用でありニュース的トレンドではない。トレンドとして注入されると意味が不自然。merge 継承で残存し続ける構造的問題の温床も解消。
