# GSC インデックス要求が `TypeError: 'Session' object is not callable` で失敗

**Date**: 2026-10-18

**症状**: CI の「Request GSC indexing」ステップ（`scripts/gsc_index.py`）が `TypeError: 'Session' object is not callable` で exit 1。トレースバックは `google/oauth2/service_account.py:462 _perform_refresh_token` → `google/oauth2/_client.py:198 _token_endpoint_request_no_throw` の `response = request(...)` で発生。

**原因**: `scripts/gsc_index.py:70` が `creds.refresh(requests.Session())` と呼び出している。google-auth の `Credentials.refresh(request)` は `request` を **callable**（`google.auth.transport.requests.Request()` など）として `response = request(url=..., ...)` を呼ぶが、`requests.Session` のインスタンスは非 callable なので TypeError になる。

**なぜ今まで発現しなかった**: 本ステップは `if: always()` + `continue-on-error: true` の非致命ステップであり、かつ GSC 機能（コミット `5d80f14`、2026-10-17）導入直後の初回 run（39084122543）は生成段階の NameError でクラッシュし本ステップは「本日URLファイルなし」で skip。URL ファイルが存在して本ステップが実際に実行されたのは run 39090062867（2026-10-18、SITE_ORIGIN 修正後の再実行）が初めてで、そこで発現した。CI 環境では新規 credentials なので `creds.token` は常に None であり、`refresh()` 分岐は必ず通る。

**影響**: 新規記事 URL の `index.update` API 要求が Google に届かない（SEO: 新記事のインデックス登録が遅延）。パイプライン自体はブロックされない（非致命）。`data/new_urls/{date}.txt` への URL 書き出しは正常。

**修正方針（いずれか）**:
1. 最小修正: `from google.auth.transport import requests as gauth_requests` として `creds.refresh(gauth_requests.Request())` に変更（`Request` は callable）。
2. より慣用的: `google.auth.transport.requests.AuthorizedSession(creds)` を作成し `session.post(API_URL, ...)` を使う（自動リフレッシュで手動 refresh 不要、`request_indexing` の手動 Authorization ヘッダーも不要になる）。

テストは AGENTS.md のルールに従い Google API を `unittest.mock` でモックして `gsc_index.py` をカバレッジに含める（実呼出し禁止）。

**対応状況**: 2026-10-18 のタスク（CI SITE_ORIGIN 修正・再実行）は本件が必須でないため修正せず記録のみ。
