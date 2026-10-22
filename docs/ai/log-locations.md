# ログ・出力先の一覧

ログの「出力先」を全件一处的に記録した参考ドキュメント。
パイプライン（CI）実行ごとに生成・蓄積されるログ、コンソール出力、CI run log、検証ログ、サイト表示「生成情報」を網羅する。
`docs/ai/architecture.md` の Data Flow とは別テーマ（データ流 vs ログ出力先）で、相互補完する。

> 更新タイミング: 新規ログ出力先を追加・削除・リネームした際に更新する（コード変更と同時）。

## 全体像（クイックリファレンス）

| # | 出力先 | 種別 | 保持方針 | 生成元 |
|---|--------|------|----------|--------|
| 1 | `data/drafts/{ts}.json` | ファイルログ | 30日（期間） | `meta.py` |
| 2 | `data/trend_usage_logs/{ts}.json` | ファイルログ | 30日（期間） | `meta.py` |
| 3 | `data/affiliate_logs/{ts}.json` | ファイルログ | 30日（期間） | `meta.py` |
| 4 | `data/prompt_logs/{ts}.txt` | ファイルログ | 30日（期間） | `generate_article.py` |
| 5 | `data/topics/{ts}.json` + `latest.json` | ファイル（データ） | 最新10件（個数） | `fetch_topics.py` |
| 6 | `data/new_urls/{date}.txt` | ファイル | 30日（期間） | `generate_article.py` |
| 7 | `data/rakuten_cache.json` | 単一ファイル | 置換（30日TTL） | `affiliate.py` |
| 8 | `data/slug-redirects.json` | 単一ファイル | 置換 | `slug_links.py` |
| 9 | `data/character_features.json` | 単一ファイル | 置換 | `fetch_topics.py` |
| 10 | `data/genre_scores/cache.json` | 単一ファイル | 置換（SHA256キャッシュ） | `genre_score.py` |
| 11 | `data/genre_scores/topics.json` | 単一ファイル | 置換 | `genre_score.py` |
| 12 | `scripts/tests/equivalence_golden/` | 開発用 | 手動 | `build_golden.py` |
| 13 | コンソール（stdout/stderr） | コンソール | CI run log に保存 | 全 Python スクリプト |
| 14 | GitHub Actions run logs | CI log | Actions 保存 | workflows/ |
| 15 | `scripts/tests/equivalence_check` 出力 | 検証ログ | 手動 | `equivalence_check.py` |
| 16 | `docs/ai/verification/{task}/` | 検証ログ | 直近2ラン | 検証実行 |
| 17 | `scripts/data/api_test_results/` | 検証ログ | 手動（gitignore） | `test_real_apis.py --save` |
| 18 | 記事本文 `<details class="gen-info">` | サイト表示 | 記事寿命 | `geninfo.py` |

---

## A. タイムスタンプ型ファイルログ（30日期間クリーンアップ対象）

パイプライン実行ごとに1ファイル生成される監査ログ。パイプラインから読み戻されないため、
`_cleanup_old_logs()`（30日超過で削除）の対象。

**共通仕組み**
- 定義: `scripts/article/config.py` (`TREND_USAGE_DIR`, `DRAFTS_DIR`, `AFFILIATE_LINKS_DIR`, `LOG_CLEANUP_DIRS`, `LOG_CLEANUP_DAYS=30`)
- 削除: `scripts/article/meta.py:_cleanup_old_logs()` ← `generate_article.py:479`（記事保存後の `generate_post()` 末尾）で呼出
- 基準: ファイル名内タイムスタンプ（`%Y-%m-%d-%H%M%S`）が JST で30日前より古いもの
- 安全側: `.gitkeep` とタイムスタンプ形式に合わないファイルは削除対象外
- 出力: 削除件数が0なら無出力、>0なら `[cleanup] 古いログファイル N 件を削除（30日前）`

### 1. `data/drafts/{ts}.json`
- **内容**: 2-pass 生成（下書き→精製）のメタデータ。Pass1/Pass2 のモデル・実行時間・文字数・行数・本文
- **書き**: `scripts/article/meta.py:_save_draft_metadata()`
- **出力**: `[draft_meta] 2-passメタデータを保存: {filepath}`
- **用途**: 生成品質の追跡・差分検証

### 2. `data/trend_usage_logs/{ts}.json`
- **内容**: トレンドデータの使用状況。候補プール統計、フィルタ結果（raw / after_score / after_rating）、選択トピックのメタデータ
- **書き**: `scripts/article/meta.py:_save_trend_usage_log()`
- **出力**: `[trend_log] 使用状況ログを保存: {filepath}`
- **用途**: 候補集計・フィルタ効率の確認

### 3. `data/affiliate_logs/{ts}.json`
- **内容**: アフィリエイト末尾セクションのキーワード・URL生成ログ。`timestamp`, `file_timestamp`, `prompt_type`, `article_title`, `keywords[]`（keyword, source, amazon_url, rakuten_url）
- **書き**: `scripts/article/meta.py:_save_affiliate_link_log()`
- **出力**: `[affiliate_log] リンク生成ログを保存: {filepath}`
- **用途**: アフィリエイトリンク生成の監査（write-only・読み戻しなしだが 30日保持）

### 4. `data/prompt_logs/{ts}.txt`
- **内容**: 生成に使用したプロンプト本文
- **書き**: `scripts/generate_article.py`（~L205-210、プロンプト保存処理）
- **出力**: `📝 プロンプト保存: {prompt_path}`
- **用途**: 生成再現・プロンプト追跡
- **CI**: `deploy.yml` で `git add data/prompt_logs/`（第1コミット）

---

## B. 数件保持型（期間クリーンアップ外）

### 5. `data/topics/{ts}.json` + `data/topics/latest.json`
- **内容**: 収集したトレンドデータ（`fetched_at`, `ttl_hours`, 各ソースの `topics`）。`latest.json` は最新ファイルの**コピー**（シンボリックリンクではない）
- **書き**: `scripts/fetch_topics.py:save_output()`（~L976-994）
- **クリーン**: `fetch_topics.py:cleanup_old_topic_files(keep=10)`（~L999-1011）— 最新10件保持、`latest.json` は除外
- **出力**: `[WARN] 古いファイルのクリーンアップに失敗しました: {e}`（失敗時のみ）、`[WARN] latest.json の更新に失敗しました: {e}`
- **CI**: `deploy.yml` で `git add data/topics/`（第1コミット）
- **備考**: e621 はトレンド出力から分離（`NON_TREND_SOURCES = {"e621"}`）

### 6. `data/new_urls/{date}.txt`
- **内容**: GSC 索引再チェック用。日付（`YYYY-MM-DD`）ごとに1ファイル、URL を1行ずつ**追記**（mode `a`）
- **書き**: `scripts/generate_article.py:_write_new_article_url()`（~L419-434）— `slug` 未検出ならスキップ
- **読み**: `scripts/gsc_index.py:get_latest_urls()`
- **クリーンアップ**: `generate_article.py:cleanup_old_new_urls()`（`finalize_and_save` 内で書き出し後に呼出）— 日付（`%Y-%m-%d`）を基準に JST で30日前を削除（`.gitkeep`・日付形式外は除外、`_cleanup_old_logs` と同方針）
- **出力**: `📮 GSC用URL出力: {url}`、`⚠️ slug未検出のためGSC用URL出力をスキップ`
- **CI**: `deploy.yml` で `git add data/new_urls/`

---

## C. 単一ファイル / 置換型（有界）

### 7. `data/rakuten_cache.json`
- 楽天API商品キャッシュ（30日TTL、`RAKUTEN_CACHE_TTL_DAYS=30`）
- 書き: `scripts/article/affiliate.py`（~L225-226）
- 置換: 毎回上書き

### 8. `data/slug-redirects.json`
- スラッグ衝突時のリダイレクト記録（`SLUG_REDIRECTS_FILE`）
- 書き: `scripts/article/slug_links.py:_save_slug_redirects()`

### 9. `data/character_features.json`
- e621 キャラクター特徴集計（種族・色・身体的特徴・キャラクター・版権・artist）
- 書き: `scripts/fetch_topics.py:_aggregate_and_save_character_features`（~L531-532）
- 出力: `[char-features] 特徴集計を保存しました (...)`
- 置換: 毎回上書き

### 10. `data/genre_scores/cache.json`
- Clef-flash 採点の SHA256 ベースキャッシュ
- 書き: `scripts/genre_score.py`（~L328-345）
- 置換: キャッシュ更新

### 11. `data/genre_scores/topics.json`
- ジャンルフィットスコア結果（`GENRE_SCORES_PATH`）
- 書き: `scripts/genre_score.py`
- 置換: 毎回上書き
- **CI**: `deploy.yml` で `git add data/genre_scores/`

### 12. `scripts/tests/equivalence_golden/`
- 等価性検証の golden ファイル生成スクリプト（`build_golden.py`）
- 開発用・手動管理
- 2026-10-22: テストフィクスチャのため `data/` 外へ移動（`scripts/tests/equivalence_check.py` の `GOLDEN` 参照、`build_golden.py` の `ROOT = parents[3]` を更新）

---

## D. コンソール / stdout ログ

Python スクリプトは `print()`（stdout）または `stderr` へ出力。CI では GitHub Actions run log として保存。

**Windows コンソール対策**
- `fetch_topics.py:_safe_print()`（~L593-598）: cp932→UTF-8 フォールバック（絵文字等非収録文字で UnicodeEncodeError 防止）
- `generate_article.py`: `sys.stdout.reconfigure(encoding="utf-8")`（win32 のみ、~L15-16）

**スクリプト別**
| スクリプト | 出力 | 備考 |
|------------|------|------|
| `fetch_topics.py` | 各ソース収集・WARN（`_safe_print`） | ソース毎 `[source] ...` |
| `generate_article.py` | パイプライン進行（絵文字タグ: `📝`/`👤`/`🎨`/`🔗`/`🏷️`/`📋`/`🎤`/`📮`/`🎉`/`🎲`） | 全 STEP 進行 |
| `gsc_index.py` | URL 毎 `[OK]`/`[FAIL]` + 集計 `📊 結果: {n}/{total} 成功` | 失敗で `sys.exit(1)` |
| `genre_score.py` | `[INFO]`/`[ERROR]` → `stderr` | 採点結果は stdout |
| `fix_descriptions.py` | `[FIX]`/`[WARN]`/`[ERROR]`/完了集計 | |
| `fix_affiliate_links.py` | 置換行・合計 | dry-run 対応 |
| `_check_space.py` / `_check_space_logs.py` / `_check_space_runtime.py` | HF Space の status / log / runtime | |
| `scripts/prompts/*` | なし（テンプレート） | |

**CI / Dev**
- GitHub Actions run logs: `deploy.yml`, `deploy-only.yml`, `gsc-verify.yml`, `zerogpu-quota-check.yml`, `genre-score.yml`（`.github/workflows/`）
- Dev server: `astro dev logs`（`astro dev stop/status/logs` で管理）
- npm: `npm-debug.log*`、`yarn-debug.log*`、`yarn-error.log*`、`pnpm-debug.log*`（`.gitignore` 対象）
- HF Space: `_check_space_logs.py` がログを取得

---

## E. 検証 / テストログ

### 15. `scripts/tests/equivalence_check.py` 出力
- 等価性検証で子プロセスの stdout/stderr をファイル化
- 出力: `{out}/stdout.log`, `{out}/stderr.log`（~L311-312）
- golden ファイル生成: `grab(...)` で `data/prompt_logs/{TS}.txt` 等をコピー

### 16. `docs/ai/verification/{task}/`
- 検証実行ログの置き場（例: `2026-10-12-refactor-equivalence/pytest_full.log`, `runs/{name}/stdout.log`, `stderr.log`）
- **保持**: `maintenance/archive_memory_bank.py` が直近2ランのみ保持（`--tmp-retention-days` は別）

### 17. `scripts/data/api_test_results/`
- 実APIテスト結果（`python scripts/tests/test_real_apis.py --save`）
- **`.gitignore` 対象**（コミットしない）
- 外部API（Gemini, HuggingFace, Kemono, e621 等）を実呼出する検証のみ使用

---

## F. サイト表示「ログ」（生成情報セクション）

### 18. 記事本文 `<details class="gen-info">`（「🤖 生成情報」）
- **場所**: 記事本文末尾の折りたたみ `<details>`（h2〜h4 不使用のため TOC に載らない）
- **書き**: `scripts/article/geninfo.py:_build_generation_info_section()`
- **表示内容**:
  - 使用したトレンド情報（タイトル＋ソース、URL取得時はリンク）
  - キャラクターデータ（体型 / 世界設定 / 変身 / 関係性 / 追加設定 / 視点 + キャラクター1/2）
  - 参考キャラクターデータ（e621）: 元投稿・人気版権・人気artist・データ時点（kemono_story のみ）
- **非表示条件**: 表示すべき内容が一切ない場合は空文字列返却（セクション非表示）
- **性質**: 公開表示（サイトユーザーにも見える）なため、個人情報・シークレットは含めないこと

---

## CI（deploy.yml）でのログの git 管理

第1コミット (`docs: auto-generated daily post with image and draft metadata [skip ci]`):
- `src/content/posts/`, `public/images/`
- `data/topics/`, `data/trend_usage_logs/`, `data/drafts/`
- `data/rakuten_cache.json`, `data/prompt_logs/`, `data/genre_scores/`, `data/new_urls/`

第2コミット (`chore: cleanup old log and topic files [skip ci]`):
- `git add -A` でクリーンアップによる削除・残りの変更を捕捉

> 注意: `data/new_urls/` は `_cleanup_old_logs`（`LOG_CLEANUP_DIRS`）の対象外だが、`finalize_and_save` 内の `cleanup_old_new_urls()`（30日・日付ベース）で削除されるため、削除は第2コミットの `git add -A` で捕捉される。

---

## 関連ドキュメント

- `docs/ai/architecture.md` — データフロー・コンポーネント（Data Flow）
- `docs/ai/tasks/2026-10-10-log-cleanup.md` — ログ・メタファイルのクリーン処理（リネーム+期間削除）の詳細
- `docs/ai/api-rate-limits.md` — 外部APIのレート制限
- `docs/ai/debugging.md` — デバッグ手順
- `.github/workflows/deploy.yml` — 生成・コミット・デプロイ・GSC 再チェック
