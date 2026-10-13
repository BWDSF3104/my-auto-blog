# 低スコアトピックの混入

**Date**: 2026-09-29
**Status**: 解決済

`generate_article.py` に `MIN_SCORE_THRESHOLD` 環境変数（デフォルト 0）を追加。しきい値未満の項目は注入時にスキップされる。
