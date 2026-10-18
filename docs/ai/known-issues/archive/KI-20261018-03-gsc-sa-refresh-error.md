# GSC index.update が `RefreshError: No access token in response` で失敗（SA トークン取得失敗）

**Date**: 2026-10-18
**状態**: 解決済み（2026-10-18）。**真因はコード起因**（非標準 scope + 非存在エンドポイント）で、当初推定した GCP 側認証情報問題ではなかった。GCP 側での操作は不要。

## 症状

`scripts/gsc_index.py`（CI「Request GSC indexing」ステップ）が、トークン取得の JWT grant で
`google.auth.exceptions.RefreshError: ('No access token in response.', ...)` を送出し exit 1。
トレースバックは `google/oauth2/_client.py:320 jwt_grant`（`response_data["access_token"]` の `KeyError`）→
`service_account.py:462 _perform_refresh_token` で発生。

## なぜ今回発現した（KI-20261018-02 との関係）

- 本件は当初「コード起因ではない（認証情報起因）」と推定されていた。KI-20261018-02 の `TypeError: 'Session' object is not callable`
  （`creds.refresh(requests.Session())`）が、コードがトークン取得段階に到達する **前** にクラッシュしていたため、
  本 RefreshError が隠されていた。
- 2026-10-18 のタスク（KI-20261018-02 修正・`AuthorizedSession` への書き換え）により TypeError が解消し、
  コードが正しく JWT grant を発行するようになった結果、**その先** にある本 RefreshError が初めて表面化した。
- 後の調査で、本件もコード起因であることが判明（下記「原因（確定）」。2026-10-18 追記）。

## 隔離検証で確認済みの事実（専用ワークフロー `gsc-verify.yml` / run 39094334108）

- SA JSON は構造的に妥当:
  - `type: service_account`
  - `client_email: gcs-indexer@cloud-vision-api-test-157707.iam.gserviceaccount.com`
  - `token_uri: https://oauth2.googleapis.com/token`（標準）
  - `private_key` 存在
- `service_account.Credentials.from_service_account_info(...)` は成功（JSON パース・バリデーション通過）。
- `creds.refresh(Request())` が `RefreshError: No access token in response` で失敗（再現確認）。
- 実 `scripts/gsc_index.py` も同一の RefreshError で失敗（コード経路の再現確認）。

## 原因（確定・2026-10-18 追記）

**コード起因**。旧 `scripts/gsc_index.py` が 3 点の誤りを含んでいた:

1. **非標準 scope**: `https://www.googleapis.com/auth/searchconsole` を使用。GSC API の公式 scope は
   `webmasters`（read/write）と `webmasters.readonly` のみ（公式 docs `how-tos/authorizing`・全公式クライアントライブラリで確認）。
   `searchconsole` は文書化されていない scope のため、Google トークンエンドポイントが JWT grant を拒否
   → `access_token` 不在 → `RefreshError: No access token in response`。
2. **非存在エンドポイント**: `urlInspection/index.update` は存在しない（実 API probe で **404** 確認）。
3. **不正 body**: `{"property": {"siteUrl": ...}}` のネスト構造（正はトップレベル `siteUrl`）。

当初の GCP 側推定（キーローテーション / SA 削除 / secret 破損 / スコープ不足）は誤り。
スコープ不足という項目だけが実態に近かったが、正しくは「コードが受け入れられない scope を要求していた」である。

### 調査で確認した事実（ローカル probe、`docs/ai/tmp/`）

- `sa_scope_matrix_result.txt`: `REFRESH[searchconsole] FAILED` / `REFRESH[webmasters]: OK` / `REFRESH[webmasters.readonly]: OK` / `REFRESH[cloud-platform]: OK` / `REFRESH[userinfo.email]: OK`。
- `gsc_endpoint_probe_result.txt`: `[index.update] HTTP 404` / `[index:inspect] HTTP 200`（`resource_id` = URL-prefix property 確認）/ `[sites.list] HTTP 404`。
- `gsc_inspect_full_result.txt`: 200 完全レスポンス（`verdict: NEUTRAL` / `coverageState: "URL is unknown to Google"`）→ **SA は GSC property へのアクセス権をすでに持っている**（GCP 側での権限付与・property user 追加は不要）。
- GSC API v1 の `urlInspection.index` リソースは `inspect` の 1 メソッドのみ。「Request indexing」は GSC UI 限定で公開 API に存在しない（Indexing API は invite-only・JobPosting/BroadcastEvent 限定）。

## 解決（2026-10-18）

`scripts/gsc_index.py` を修正（タスク: `docs/ai/tasks/2026-10-18-gsc-index-refresh-fix.md`）:

- scope: `searchconsole` → `https://www.googleapis.com/auth/webmasters`（実 API 200 確認済み）。
- `API_URL`: `urlInspection/index.update` → `urlInspection/index:inspect`。
- body: `{"inspectionUrl": url, "siteUrl": SITE_URL}`（正のトップレベル構造）。
- テスト更新: `scripts/tests/test_gsc_index.py`（10/10 passed・全スイート 423 passed）。
- `gsc-verify.yml` step 1 も `webmasters` + `index:inspect` に更新し CI で再検証中。
- **意味変更**: 本来の「インデックス登録要求」（write）は公開 API に存在せず、`index:inspect`（read）で Google による URL の再チェックを促すのが最も近い代替。

## 影響

- 未修正期間中: 新規記事 URL の `index.update` 要求が Google に届かない（SEO: 新記事のインデックス登録が遅延）。
- 修正後: `index:inspect` で URL の再チェックを Google に促す。
- パイプライン自体はブロックされない（`continue-on-error: true` の非致命ステップ）。**ブログ生成・デプロイは正常**。

## 対応状況

- 2026-10-18: コード修正（KI-20261018-02）が完了したことで本件が表面化。専用検証ワークフロー `gsc-verify.yml` を作成・実行。
- 2026-10-18: ローカル probe（scope マトリクス / エンドポイント probe / inspect 完全レスポンス）で真因がコード起因と確定。`gsc_index.py` / テスト / `gsc-verify.yml` を修正、pytest 423 passed。
- 2026-10-18: `gsc-verify.yml`（`workflow_dispatch`）CI 再検証 **green**（run 39102042828、33s）:
  - step 1: `REFRESH OK`（`webmasters` scope、token len 1024）+ `index:inspect: 200`（`verdict: PASS`）。
  - step 2: 実 `gsc_index.py` が 2 URL を処理し成功。
  - 本ファイルを `known-issues/archive/` へ移動しクローズ。
