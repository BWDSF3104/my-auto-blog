# ログ・出力先の一覧（全件明記・記録）

**Status**: 完了
**Date**: 2026-10-22
**Next Action**: docs/ai/log-locations.md を作成し、全ログ出力先とクリーンアップ方針を記載する

## 意図 / 背景

ログ出力先（ファイルログ・コンソール・CI・検証・サイト表示）が散在し、一元的な参考ドキュメントが存在しない。全件を調査し、`docs/ai/` 下の新規参考ドキュメント（候補: `docs/ai/log-locations.md`）に明記する。

## 調査結果 / 変更内容

### 選定した記録場所: `docs/ai/log-locations.md`（新規）

- 理由:
  - ログ出力先はパイプライン進化で変わる「可変な知識」で、`docs/ai/`（AI Memory Bank）が所定の置き場
  - 既存トップレベル参照ドキュメント（`api-rate-limits.md`、`image-analysis.md`、`architecture.md`）と同様に kebab-case の独立ファイル
  - `architecture.md` の「Data Flow」とは別テーマ（データ流 vs ログ出力先）で、独立ファイルで焦点を絞る
- 補足: `architecture.md` の Data Flow セクションから `docs/ai/log-locations.md` へ横リンク追加予定

### 特定したログ・出力先（全件）

**A. タイムスタンプ型ファイルログ（1デプロイ/1ファイル、30日期間クリーンアップ対象: `_cleanup_old_logs` / `LOG_CLEANUP_DIRS` / `LOG_CLEANUP_DAYS=30`、JST）**
1. `data/drafts/{ts}.json` — 2-pass ドラフトメタデータ。書き: `scripts/article/meta.py:_save_draft_metadata`
2. `data/trend_usage_logs/{ts}.json` — トレンド使用状況ログ。書き: `scripts/article/meta.py:_save_trend_usage_log`
3. `data/affiliate_logs/{ts}.json` — アフィリエイトリンク生成ログ。書き: `scripts/article/meta.py:_save_affiliate_link_log`
4. `data/prompt_logs/{ts}.txt` — 使用プロンプト。書き: `scripts/generate_article.py`（~L205）

**B. 数件保持型（期間クリーンアップ外）**
5. `data/topics/{ts}.json` + `data/topics/latest.json`(コピー) — トレンドデータ。書き: `scripts/fetch_topics.py:save_output`。クリーン: `fetch_topics.py:cleanup_old_topic_files(keep=10)`（最新10件保持）
6. `data/new_urls/{date}.txt` — GSC用新規記事URL（1行/URL、追記モード）。書き: `scripts/generate_article.py:_write_new_article_url`。読み: `scripts/gsc_index.py:get_latest_urls`。⚠️ クリーンアップなし（日付型ファイル、`_cleanup_old_logs` 対象外）

**C. 単一ファイル / 置換型**
7. `data/rakuten_cache.json` — 楽天API商品キャッシュ（30日TTL）。書き: `scripts/article/affiliate.py`
8. `data/slug-redirects.json` — スラッグリダイレクト。書き: `scripts/article/slug_links.py:_save_slug_redirects`
9. `data/character_features.json` — e621 キャラクター特徴集計。書き: `scripts/fetch_topics.py`
10. `data/genre_scores/cache.json` — Clef-flash 採点 SHA256 キャッシュ。書き: `scripts/genre_score.py`
11. `data/genre_scores/topics.json` — ジャンルフィットスコア結果。書き: `scripts/genre_score.py`
12. `data/equivalence_golden/` — 等価性検証の golden ファイル生成スクリプト（`build_golden.py`）。開発用

**D. コンソール / stdout ログ**
- Python: `print()` / `_safe_print()`（fetch_topics.py:593, cp932→UTF-8 フォールバック）
  - fetch_topics.py: ソース毎収集・WARN
  - generate_article.py: パイプライン進行（絵文字タグ付き）
  - gsc_index.py: URL 毎 `[OK]/[FAIL]` + 集計
  - genre_score.py: `[INFO]`/`[ERROR]` → stderr
- CI: GitHub Actions run logs（deploy.yml / gsc-verify.yml / zerogpu-quota-check.yml / genre-score.yml / deploy-only.yml）
- Dev: `astro dev logs`（dev server logs, `astro dev stop/status/logs`）
- npm: `npm-debug.log*` 等（`.gitignore` 対象）
- HF Space: `_check_space_logs.py` がログを取得

**E. 検証 / テストログ**
- `scripts/tests/equivalence_check.py` → 出力ディレクトリに `stdout.log`/`stderr.log`（L311-312）
- `docs/ai/verification/{task}/` — 検証実行ログ（`pytest_full.log`, `runs/*/stdout.log`, `stderr.log`）。`maintenance/archive_memory_bank.py` で直近2ラン保持
- `scripts/data/api_test_results/` — 実APIテスト結果（gitignore、`python scripts/tests/test_real_apis.py --save`）

**F. サイト表示「ログ」（生成情報セクション）**
- 記事本文 `<details class="gen-info">`「🤖 生成情報」。書き: `scripts/article/geninfo.py:_build_generation_info_section`。使用トレンド/キャラデータ/e621参照を公開表示

## Verification

- 対象: `docs/ai/`・`docs/ai/log-locations.md`（新規）・`docs/ai/architecture.md` ののみ変更
- 検証: AGENTS.md 例外（`docs/ai/`・`AGENTS.md`・`.kilo/` のみ変更）により pytest / build 不要
- 精度確認（grep・Read による全件照合）:
  - ファイルログ出力先（A: 4件、B: 2件、C: 6件、D: コンソール、E: 検証 3種、F: サイト表示）の生成元・関数・行番号をコードと照合
  - `data/` 実ディレクトリ（8サブディレクトリ + 単一ファイル3件 + equivalence_golden）と一致
  - `latest.json` はコピー（シンボリックリンクなし）を実ディレクトリ・コードで確認し、architecture.md 表記も修正
- `python maintenance/archive_memory_bank.py` dry-run → 0 action、`--apply` → 0 action（変更なし）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
