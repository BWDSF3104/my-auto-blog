# Pythonスクリプトの構造は「入口ファイル固定 + `scripts/article/` パッケージ + フェーズ分割移行」

**Date**: 2026-10-11

**Decision**: `generate_article.py`（3561行）を `scripts/article/` パッケージ（8 モジュール）へ責務分離し、入口+`generate_post()` パイプライン（8 ステージ関数）に縮約。`fetch_topics.py` は関数抽出のみ（入口不変）。8 フェーズで各フェーズ末に pytest 緑で進行。

**Reason**: `deploy.yml` がファイル名固定で起動するため入口は残置。テストが `patch("generate_article.X")` に強く結合するため関数移設と patch 経路更新を同一フェーズで実施。フェーズ分割で中間状態の回帰を最小単位で検出。
