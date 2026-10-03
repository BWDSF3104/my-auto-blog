# Rate Limit Research (2026-10-02)

**Status**: 完了

**Summary**:
- 各データソースのレート制限を調査・実測
- `AGENTS.md` の Test Script Rules に確認済みレート制限テーブルを追加
- `scripts/tests/test_real_apis.py` を作成（独立スクリプト、pytest 収集除外）
- 実測結果: e621 (2 req/s), GitHub Search (10 req/窓), Reddit (403規制中), Hacker News (なし), RSS (なし), Kemono API (不明), Bluesky (501)

**Files Changed**:
- `AGENTS.md`: Test Script Rules にレート制限テーブル追加
- `scripts/tests/test_real_apis.py`: 新規作成（独立テストスクリプト）

**Verification**:
- `pytest scripts/tests/ -v`: 134件全パス、警告0
- `python scripts/tests/test_real_apis.py`: 7/9通過 (Reddit 403, Bluesky 501 はAPI側規制)
