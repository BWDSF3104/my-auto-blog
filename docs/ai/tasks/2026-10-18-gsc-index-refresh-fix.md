# GSC index.update の refresh 呼び出し修正（TypeError: 'Session' object is not callable）

**Status**: 完了（TypeError 修正 + RefreshError の真因（コード起因）特定・修正 ともに検証済み。`gsc-verify.yml` CI 再検証 green: run 39102042828）
**Date**: 2026-10-18
**Next Action**: なし（完了）。

## 意図 / 背景

- CI run 39090062867（SITE_ORIGIN 修正後の再実行）で初めて GSC ステップが実際に実行され、`TypeError: 'Session' object is not callable` で失敗（非致命・`continue-on-error`）。新規記事 URL の `index.update` 要求が Google に届いていない（SEO: インデックス登録遅延）。
- 詳細・根拠は `docs/ai/known-issues/KI-20261018-02-gsc-index-session-not-callable.md`。ユーザー承認のもと本タスクで修正実施。
- 目的: GSC インデックス登録要求が正に Google へ届くよう `scripts/gsc_index.py` を修正し、外部 API を `unittest.mock` でモックした単体テストを追加（AGENTS.md: 実 API 呼び出し禁止）。
- TypeError 修正後に新たな blocker `RefreshError: No access token in response` が表面化。当初は GCP 側認証情報起因と推定して KI-20261018-03 に記録したが、2026-10-18 の調査で **真因はやはりコード側**（非標準 scope + 非存在エンドポイント）と判明し、同一タスクで修正した。

## 調査結果 / 変更内容

### 第1ラウンド: TypeError 修正（commit b8ea37f）

- 根本原因: `gsc_index.py:70` が `creds.refresh(requests.Session())` を呼ぶ。google-auth の `Credentials.refresh(request)` は `request` を **callable**（`google.auth.transport.requests.Request()` 等）として `response = request(url=..., ...)` を呼ぶが、`requests.Session` のインスタンスは非 callable なので TypeError。CI では新規 credentials のため `creds.token` は常に None でこの refresh 分岐は必ず通る。
- **採用方針（known-issue の選択肢 2: 慣用的な `AuthorizedSession`）**: `google.auth.transport.requests.AuthorizedSession` を使い、`session.post(API_URL, json=body, timeout=30)` で要求する。理由: (1) トークンの自動リフレッシュを google-auth に委ね、手動 `creds.refresh(...)` と手動 Authorization ヘッダーという「root cause のパターン」そのものを除去できる。(2) google-auth 公式が `requests` 向けに推奨するパターン。(3) `request_indexing` が簡潔になる（`json=body` で requests が Content-Type を自動設定するため手動ヘッダー不要）。
- 変更点: `gsc_index.py` を上記方針で書き換え（`request_indexing` 引数を `access_token: str` → `session: AuthorizedSession` に変更、`main` が `session = AuthorizedSession(creds)` を作成）。未使用だった `import requests` と `from google.auth import credentials` を削除。
- テスト: `scripts/tests/test_gsc_index.py` を新規作成。`get_latest_urls` / `load_credentials` / `request_indexing` / `main` を `unittest.mock` でカバレッジ（Google API 実呼出しなし）。

### 第2ラウンド: RefreshError の真因特定・修正（「認証情報問題」はコードのバグだった）

- 症状: TypeError 解消後（commit b8ea37f 以降）、JWT grant で `RefreshError: ('No access token in response.', ...)`。CI run 39094334108（`gsc-verify.yml`）とローカルで再現。当初は GCP 側起因（キーローテーション後の古い key / SA 削除 / secret 破損 / スコープ不足）と推定し KI-20261018-03 に記録。
- **調査（ローカル probe、`docs/ai/tmp/sa_scope_matrix.py` / `gsc_endpoint_probe.py` / `gsc_inspect_full.py`）**:
  - scope マトリクス: `searchconsole` scope（旧コードが使用）で refresh **失敗**。`webmasters` / `webmasters.readonly` / `cloud-platform` / `userinfo.email` は OK。
  - GSC API の公式 scope は `webmasters`（read/write）と `webmasters.readonly` のみ（公式 docs `how-tos/authorizing`・全公式クライアントライブラリで確認）。**`searchconsole` は文書化されていない scope** で、Google トークンエンドポイントが JWT grant を拒否 → "No access token in response"。
  - エンドポイント probe: `urlInspection/index.update` → **404（エンドポイントが存在しない）**。`urlInspection/index:inspect` → **200 + 実データ**（`verdict: NEUTRAL`、`coverageState: "URL is unknown to Google"`）。`sites.list` も 404（リソース名自体が存在しない）。
  - `index:inspect` の 200 が、SA が GSC property `https://bwdsf3104.github.io/my-auto-blog/`（URL-prefix property）へのアクセス権を**すでに持っている**ことを証明 → **GCP 側での権限付与・property user 追加は不要**。
  - GSC API v1 の `urlInspection.index` リソースは `inspect` の 1 メソッドのみ。「Request indexing」は GSC UI 限定で公開 API に存在しない（Indexing API は invite-only・JobPosting/BroadcastEvent 限定）。
- **修正（`scripts/gsc_index.py`）**:
  - scope: `https://www.googleapis.com/auth/searchconsole` → `https://www.googleapis.com/auth/webmasters`（API が公式に受け付ける scope。実 API 200 で確認済み。最小権限の代替として `webmasters.readonly` も検証済み OK）。
  - `API_URL`: `.../urlInspection/index.update` → `.../urlInspection/index:inspect`。
  - body: `{"inspectionUrl": url, "property": {"siteUrl": SITE_URL}}`（不正・ネスト構造）→ `{"inspectionUrl": url, "siteUrl": SITE_URL}`（正のトップレベル構造）。
  - docstring を更新。関数名 `request_indexing` は最小 diff のため維持。
  - **意味変更**: 本来の「インデックス登録要求」（write）は公開 API に存在せず、`index:inspect`（read）で **Google による URL の再チェックを促す**のが最も近い代替。
- テスト: `scripts/tests/test_gsc_index.py` を更新（`test_loads_with_searchconsole_scope` → `test_loads_with_webmasters_scope`、`test_posts_index_update_payload` → `test_posts_inspect_payload`、アサーションを新 scope / 新 body に変更）。
- `.github/workflows/gsc-verify.yml`: step 1（隔離診断）を `webmasters` scope + `index:inspect` 呼び出し（non-200 で `sys.exit(1)`）に変更、ヘッダコメントを更新。

## Verification

- `python -m pytest scripts/tests/ -q` → **423 passed in 7.46s**（2026-10-18、第2ラウンド修正後に再実行）。
- テスト `scripts/tests/test_gsc_index.py`（10件・全 PASS）: `get_latest_urls`（ファイル不在/strip・空行除去）・`load_credentials`（env 不在で RuntimeError / webmasters scope）・`request_indexing`（200→True / payload・timeout 検証 / 404→False）・`main`（URL なしで skip / 全成功で exit なし / 部分失敗で exit 1）。Google API は全件 `unittest.mock`（実呼出しなし）。
- **実 API probe（ローカル、キー: `C:\Users\fujim\Downloads\cloud-vision-api-test-157707-7e1cc85f95cb.json`）**:
  - `sa_scope_matrix_result.txt`: `REFRESH[searchconsole] FAILED` / `REFRESH[webmasters]: OK` / `REFRESH[webmasters.readonly]: OK` / `REFRESH[cloud-platform]: OK` / `REFRESH[userinfo.email]: OK`。
  - `gsc_endpoint_probe_result.txt`: `[index.update] HTTP 404` / `[index:inspect] HTTP 200`（`resource_id` = URL-prefix property 確認）/ `[sites.list] HTTP 404`。
  - `gsc_inspect_full_result.txt`: 200 完全レスポンス（`verdict: NEUTRAL` / `coverageState: "URL is unknown to Google"`）→ property アクセス正常。
- **CI 検証（TypeError 解消）**: run 39092902792（`deploy.yml`、commit `b8ea37f`）: 「Request GSC indexing」ステップで `TypeError: 'Session' object is not callable` が **解消**。コードは正しくトークン取得段階まで到達（run 全体は success だが、本ステップは `continue-on-error: true` により成功に偽装されるため conclusion だけで判断しない）。
- **CI 再検証（第2ラウンド修正）**: `gsc-verify.yml`（`workflow_dispatch`）run **39102042828** → **green（33s）**:
  - step 1（隔離診断）: `REFRESH OK`（`webmasters` scope、token len 1024）+ `index:inspect: 200`（`verdict: PASS`）。
  - step 2（実 `gsc_index.py`）: `🔍 GSC インデックス要求: 2件` → 成功（`data/new_urls/2026-10-18.txt` の 2 URL を `index:inspect` で処理）。
  - 旧コード（`searchconsole` scope + `index.update`）の RefreshError / 404 は解消。end-to-end 検証完了。

## Follow-up / Blocker（RefreshError blocker はクローズ）

- ~~`GSC_SA_JSON` のサービスアカウントがトークン取得（JWT grant）側で失敗している~~ → **クローズ**: 原因は旧コードが使用した `searchconsole` scope が GSC API に受け入れられないこと（**コードのバグ**）。SA キーは有効であり、`webmasters` scope + `index:inspect` で実 API 200 を確認済み（上記参照）。**GCP 側での操作は不要**。
- `docs/ai/known-issues/KI-20261018-03-gsc-sa-refresh-error.md` を「解決済み（コード起因）」に修正済み。CI 再検証 green（run 39102042828）確認後、`known-issues/archive/` へ移動済み。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除（header のみで削除すべき行が存在しなかった）
- [x] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（KI-20261018-03、`gsc-verify.yml` green 後）
- [x] `backlog.md` の完了項目を削除（GSC 関連項目が存在しなかったため N/A）
