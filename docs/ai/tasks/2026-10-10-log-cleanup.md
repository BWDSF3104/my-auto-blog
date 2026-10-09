# ログ・メタファイルのクリーン処理（リネーム+期間削除）

- **Status**: 完了（2026-10-10、コミット `dc2181b`）
- **関連 Plan**: `plans.md` [2026-10-10]
- **関連 Backlog**: `backlog.md` P2 #1（完了済み・P2(完了)へ移動）

## 目的

デプロイごとに無制限に蓄積する監査ログ・メタファイルを整理し、リポジトリの肥大化を抑制する。さらにファイル名から「ログであること」が分かりにくい `affiliate_links` の命名を是正する。

## 調査結果（デプロイ毎の蓄積ファイル）

git 履歴・コード・実ディレクトリで特定。

| ディレクトリ | 1回あたり | クリーンアップ | 備考 |
|---|---|---|---|
| `data/drafts/{ts}.json` | 13〜28 KB | なし（無制限） | 2-passドラフトメタデータ `generate_article.py` `_save_draft_metadata` |
| `data/trend_usage/{ts}.json` | ~1.4 KB | なし（無制限） | トレンド使用ログ `_save_trend_usage_log` |
| `data/affiliate_links/{ts}.json` | 2〜3 KB | なし（無制限） | アフィリエイトリンク生成ログ `_save_affiliate_link_log`。**write-only（readbackなし）** |
| `data/prompt_logs/{ts}.txt` | 数 KB | なし（無制限） | 使用プロンプト。`generate_post()` 内で無条件書き込み。直近 CI 後に保存先変更のため当時空 |
| `data/topics/{ts}.json` | 97〜99 KB | **あり**（最新10件, `fetch_topics.py:892` 個数ベース） | 変更不要 |
| `data/rakuten_cache.json` | 置換 | あり（30日TTL） | 単一ファイル・有界 |
| `data/character_features.json` | 置換 | - | 単一ファイル・有界 |
| `data/genre_scores/cache.json` | 増加 | - | SHA256キャッシュ・単一ファイル |

## 決定事項（ユーザー回答 2026-10-09）

- `data/affiliate_links` → **`data/affiliate_logs`**（`prompt_logs` と同じ `_logs` 規則）
- `data/trend_usage` → **`data/trend_usage_logs`**（全ログディレクトリを `_logs` 規則で統一）
- 進め方: **今すぐ実装、ワークフローとの整合性にも留意**

## 実装内容

### T1. ディレクトリリネーム ✅

- [x] `git mv data/affiliate_links data/affiliate_logs` + `.gitkeep` 追加（従来なし）
- [x] `git mv data/trend_usage data/trend_usage_logs`（`.gitkeep` 既存）
- [x] 旧ディレクトリ消滅・新ディレクトリに全ファイル+`.gitkeep` 存在を検証

### T2. 機能コードの参照更新 ✅

- [x] `generate_article.py`: `TREND_USAGE_DIR = "data/trend_usage_logs"`
- [x] `generate_article.py`: `AFFILIATE_LINKS_DIR = "data/affiliate_logs"`
- [x] `.github/workflows/deploy.yml`: `git add data/trend_usage_logs/`（`affiliate_logs` は `git add -A` で捕捉のため変更不要）
- [x] 機能コード（py/yml）に旧ディレクトリ名参照が残らないことを grep 確認

### T3. 期間ベース削除関数 ✅

- [x] `generate_article.py` に `LOG_CLEANUP_DAYS = 30` / `LOG_CLEANUP_DIRS` / `_cleanup_old_logs(days)` 追加
  - ファイル名内のタイムスタンプ（`%Y-%m-%d-%H%M%S`）を基準に `days` 日前のファイルを削除
  - `.gitkeep` とタイムスタンプ形式に合わないファイルは削除対象外（安全側）
  - 対象ディレクトリ: `drafts/`・`trend_usage_logs/`・`affiliate_logs/`・`prompt_logs/`
  - 削除件数を返す。非致命（例外は warn 出力）
- [x] `generate_post()` 末尾（記事保存後）で `_cleanup_old_logs()` を呼出
- [x] CI 整合性: クリーンアップ削除は既存の commit 構造で捕捉される
  - `drafts/`・`trend_usage_logs/`・`prompt_logs/` → 明示 `git add` で第1コミット（`docs: ...`）
  - `affiliate_logs/` → `git add -A` で第2コミット（`chore: cleanup ...`）
  - `deploy.yml` 第2コミットメッセージを `chore: cleanup old log and topic files [skip ci]` に更新（実際の内容に合わせる）

### T4. 単体テスト（全モック・API 未消費）✅

- [x] `test_generate_article.py` に `TestCleanupOldLogs` 8件追加
  - 古いファイル削除+最新保持 / 全て最新で保持 / `.gitkeep` 非削除 / タイムスタンプ外ファイル非削除 / 不存在ディレクトリでエラーなし / 複数ディレクトリ / カスタム days しきい値 / リネーム後ディレクトリが対象に含まれること
- [x] 現在時刻相対のタイムスタンプ生成で日付依存を排除

### T5. 記録更新（コミット前）✅

- [x] `backlog.md` P2 #1 を完了扱いへ（P2(完了)セクション追加）
- [x] 本タスクファイル作成
- [x] `plans.md` へ追記
- [x] `current-task.md` へ追記

## Verification

- `pytest scripts/tests/ -v` → **305 passed** (3.81s)（新規 8 件含む、実 API 呼び出しゼロ）
- `python -m py_compile scripts/generate_article.py scripts/tests/test_generate_article.py` → OK
- `python -c "import yaml; yaml.safe_load(...)"` → `deploy.yml` + `deploy-only.yml` OK
- 機能コードに旧ディレクトリ名（`data/trend_usage\b` / `data/affiliate_links\b`）参照なし（grep 確認）
- コミット: `dc2181b`（2026-10-10、commit + push 実施。変更ファイルが deploy-only.yml の paths（`src/**` 等）に該当しないため自動デプロイはトリガーされず、deploy 確認不要）

## 制約・注意事項

- `data/topics/` は既存の個数ベースクリーンアップ（最新10件）を維持。本タスクでは変更しない
- 期間削除はファイル名タイムスタンプ基準（CI の checkout mtime に依存しない）
- `affiliate_logs` は write-only 監査ログだが、`fix_affiliate_links.py` による既存記事リンク修正の可能性を考慮し 30 日保持（短すぎない）
- Git commit・push は指示がない限り実行しない
