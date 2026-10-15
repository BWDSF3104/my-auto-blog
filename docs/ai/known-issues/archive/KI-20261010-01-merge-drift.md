# トレンドデータ `by_category` / `all` の merge 構造ドリフト

**Date**: 2026-10-10
**Status**: 解決（2026-10-15）

**症状**: `data/topics/latest.json` の `by_category.pokemon` に `all` に存在しない 7 件（e621 5 件 + GitHub 2 件、旧 e621 再収集で sources から脱落したトピック）が merge 継承で残存。

**原因**: `by_category` はカテゴリ単位で merge 継承、`all` / `sources` は source 単位の部分継承のため、両者の構造が乖離する（`fetch_topics.py:937-940` / retention 974-985）。

**影響**: 低。`generate_article.py:2313` のトレンド注入は `by_category` を読むが score しきい値でフィルタするため、実注入は想定されない。理論上、pokemon 記事に旧トピック注入の可能性。

**修正方針**: source 継承後に `by_category` を `all` から再構築する merge ロジックの再設計（単独で実施せず、関連変更とバッチ化が望ましい）。2026-10-10 に特定（`tasks/2026-10-10-trend-source-quality-fixes.md`）、backlog P3 #7 へ。

**更新 (2026-10-10)**: e621 固有の部分は解消済み — e621 をトレンド配管から分離（`NON_TREND_SOURCES` ガード + `data/topics/*.json` 12 ファイルの一次性除去、`tasks/2026-10-10-e621-trend-separation.md` 参照）により、e621 5 件は再混入しなくなった。一般構造ドリフト（他 source の残存可能性）は backlog P3 #7 で継続。

**更新 (2026-10-15, 解決)**: 2026-10-15 検証で GitHub 2 件（`ivi-vink/Akkamon` score=2 / `Ahmadsadin36/pokedex` score=0）が全 10 タイムスタンプファイル + `latest.json` に恒常再発を確認。`build_output()` の `by_category` カテゴリ単位独立継承を廃止し、source 継承後に `all` から毎回再構築する設計に変更（`decisions/2026-10-15-by-category-rebuild-from-all.md`）。既存 11 ファイルのドリフト 2 件を一括除去し、全ファイル `by_category` ⊆ `all` を確認。`tasks/2026-10-15-merge-drift-fix.md` 参照。
