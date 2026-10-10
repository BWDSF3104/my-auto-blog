# 既知問題リスト

進行中の問題のみを記録。解決済は `known-issues-archive.md` に移動する。

---

## KI-20261010-01: トレンドデータ `by_category` / `all` の merge 構造ドリフト

**症状**: `data/topics/latest.json` の `by_category.pokemon` に `all` に存在しない 7 件（e621 5 件 + GitHub 2 件、旧 e621 再収集で sources から脱落したトピック）が merge 継承で残存。

**原因**: `by_category` はカテゴリ単位で merge 継承、`all` / `sources` は source 単位の部分継承のため、両者の構造が乖離する（`fetch_topics.py:937-940` / retention 974-985）。

**影響**: 低。`generate_article.py:2313` のトレンド注入は `by_category` を読むが score しきい値でフィルタするため、実注入は想定されない。理論上、pokemon 記事に旧トピック注入の可能性。

**修正方針**: source 継承後に `by_category` を `all` から再構築する merge ロジックの再設計（単独で実施せず、関連変更とバッチ化が望ましい）。2026-10-10 に特定（`tasks/2026-10-10-trend-source-quality-fixes.md`）、backlog P3 #7 へ。
