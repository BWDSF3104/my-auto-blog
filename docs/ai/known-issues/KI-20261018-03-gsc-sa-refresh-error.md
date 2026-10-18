# GSC index.update が `RefreshError: No access token in response` で失敗（SA トークン取得失敗）

**Date**: 2026-10-18
**状態**: 未解決（GCP / GitHub secret 側の確認が必要・コード起因ではない）

## 症状

`scripts/gsc_index.py`（CI「Request GSC indexing」ステップ）が、トークン取得の JWT grant で
`google.auth.exceptions.RefreshError: ('No access token in response.', ...)` を送出し exit 1。
トレースバックは `google/oauth2/_client.py:320 jwt_grant`（`response_data["access_token"]` の `KeyError`）→
`service_account.py:462 _perform_refresh_token` で発生。

## なぜ今回発現した（KI-20261018-02 との関係）

- 本件は **コード起因ではなく認証情報起因**。KI-20261018-02 の `TypeError: 'Session' object is not callable`
  （`creds.refresh(requests.Session())`）が、コードがトークン取得段階に到達する **前** にクラッシュしていたため、
  本 RefreshError が隠されていた。
- 2026-10-18 のタスク（KI-20261018-02 修正・`AuthorizedSession` への書き換え）により TypeError が解消し、
  コードが正しく JWT grant を発行するようになった結果、**その先** にある本 RefreshError が初めて表面化した。

## 隔離検証で確認済みの事実（専用ワークフロー `gsc-verify.yml` / run 39094334108）

- SA JSON は構造的に妥当:
  - `type: service_account`
  - `client_email: gcs-indexer@cloud-vision-api-test-157707.iam.gserviceaccount.com`
  - `token_uri: https://oauth2.googleapis.com/token`（標準）
  - `private_key` 存在
- `service_account.Credentials.from_service_account_info(...)` は成功（JSON パース・バリデーション通過）。
- `creds.refresh(Request())` が `RefreshError: No access token in response` で失敗（再現確認）。
- 実 `scripts/gsc_index.py` も同一の RefreshError で失敗（コード経路の再現確認）。

## 原因（推定・要確認）

JWT grant が `access_token` を返さない = Google トークンエンドポイントが認可を拒否/異常応答している。
構造的に妥当な SA JSON なのに失敗するため、以下いずれかが考えられる（**GCP 側での確認が必要**）:

1. **キーローテーション後の古い key**: `GSC_SA_JSON` secret が旧 private key を保持し、GCP 側の現行 key と不一致 → JWT 署名が不正。
2. **SA の削除**: `gcs-indexer@cloud-vision-api-test-157707` が GCP プロジェクト `cloud-vision-api-test-157707` から削除済み。
3. **secret の欠損/破損**: `GSC_SA_JSON` が切り詰め・改行混入等で破損（`from_service_account_info` を通るが key が不正）。
4. **スコープ/権限不足**: SA に `searchconsole` スコープや GSC プロパティのアクセス権がない。

## 影響

新規記事 URL の `index.update` 要求が Google に届かない（SEO: 新記事のインデックス登録が遅延）。
パイプライン自体はブロックされない（`continue-on-error: true` の非致命ステップ）。
**ブログ生成・デプロイは正常**。

## 修正方針（ユーザー側の GCP / secret 操作が必要）

1. GCP コンソールでプロジェクト `cloud-vision-api-test-157707` の SA `gcs-indexer` が存在するか確認。
2. 存在する場合、SA の **新しい key（JSON）を再生成** し、GitHub secret `GSC_SA_JSON` を更新。
3. SA が GSC プロパティ（`https://bwdsf3104.github.io/my-auto-blog/`）にアクセスできる権限（Search Console API スコープ）を持つか確認。
4. `GSC_SA_JSON` secret が完全（切り詰めなし）か確認。
5. 修正後、専用ワークフロー `gsc-verify.yml`（`workflow_dispatch`）を再実行し、`REFRESH OK` + `sites.get 200` を確認。

## 対応状況

- 2026-10-18: コード修正（KI-20261018-02）が完了したことで本件が表面化。専用検証ワークフロー `gsc-verify.yml` を作成・実行し、
  認証情報起因であることを確認。GCP 側の対応待ち。
