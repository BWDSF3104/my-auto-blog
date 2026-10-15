# `by_category` を `all` から再構築する merge 設計

**Date**: 2026-10-15

**Decision**: `fetch_topics.py` の `build_output()` で `by_category` のカテゴリ単位独立継承を廃止し、source 継承と `NON_TREND_SOURCES` フィルタ後に `all`（canonical）から毎回再構築する。`prev` の `by_category` は一切読み込まない。

**Reason**: カテゴリ単位継承（旧 `:957-965`）と source 単位継承（`sources`/`all`）の粒度差により、`sources` から脱落した旧トピックが `by_category` に恒常残存する構造ドリフト（KI-20261010-01）が発生し続けていた（2026-10-15 検証: GitHub 2 件が全 10 ファイルに再発）。`by_category` は `all` のカテゴリ分割ビューであるべき派生値であり、独立継承させないことで両構造の乖離を構造的に不可能にする。

**Rejected Alternatives**:
- カテゴリ継承時に「前回リスト ∩ 現在の all」でフィルタする: 症状を緩和するのみで、`all` にあるトピックが `by_category` へ欠落する逆方向ドリフト（旧: 収集カテゴリは fresh のみで上書き）は残る
- 毎ランの事後検証スクリプト: 原因の除去ではなく検知のみ

**Impact**:
- `latest.json` のスキーマ不変（`by_category`/`all`/`sources`/`total` 同一）
- 未収集 source のトピック保持は `sources` 継承 → `all` 結合の経路で従来どおり機能（`trends.py` の per-source TTL / need_fetch ロジックとの互換はテストで確認）
- 意図的挙動変化: 収集カテゴリにも未収集 source の継承トピックが `by_category` に反映される（旧は fresh のみ）。`all` と一致するため整合的
- 2026-10-15 に既存 `data/topics/*.json`（11 ファイル）のドリフト 2 件を一括除去済み
