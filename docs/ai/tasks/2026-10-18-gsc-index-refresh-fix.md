# GSC index.update の refresh 呼び出し修正（TypeError: 'Session' object is not callable）

**Status**: 完了
**Date**: 2026-10-18
**Next Action**: gsc_index.py:70 を callable な transport.Request に修正し、mock ベース単体テストを追加

## 意図 / 背景

- CI run 39090062867（SITE_ORIGIN 修正後の再実行）で初めて GSC ステップが実際に実行され、`TypeError: 'Session' object is not callable` で失敗（非致命・`continue-on-error`）。新規記事 URL の `index.update` 要求が Google に届いていない（SEO: インデックス登録遅延）。
- 詳細・根拠は `docs/ai/known-issues/KI-20261018-02-gsc-index-session-not-callable.md`。ユーザー承認のもと本タスクで修正実施。
- 目的: GSC インデックス登録要求が正に Google へ届くよう `scripts/gsc_index.py` を修正し、外部 API を `unittest.mock` でモックした単体テストを追加（AGENTS.md: 実 API 呼び出し禁止）。

## 調査結果 / 変更内容

- 根本原因: `gsc_index.py:70` が `creds.refresh(requests.Session())` を呼ぶ。google-auth の `Credentials.refresh(request)` は `request` を **callable**（`google.auth.transport.requests.Request()` 等）として `response = request(url=..., ...)` を呼ぶが、`requests.Session` のインスタンスは非 callable なので TypeError。CI では新規 credentials のため `creds.token` は常に None でこの refresh 分岐は必ず通る。
- **採用方針（known-issue の選択肢 2: 慣用的な `AuthorizedSession`）**: `google.auth.transport.requests.AuthorizedSession` を使い、`session.post(API_URL, json=body, timeout=30)` で要求する。理由: (1) トークンの自動リフレッシュを google-auth に委ね、手動 `creds.refresh(...)` と手動 Authorization ヘッダーという「root cause のパターン」そのものを除去できる。(2) google-auth 公式が `requests` 向けに推奨するパターン。(3) `request_indexing` が簡潔になる（`json=body` で requests が Content-Type を自動設定するため手動ヘッダー不要）。
- 変更点: `gsc_index.py` を上記方針で書き換え（`request_indexing` 引数を `access_token: str` → `session: AuthorizedSession` に変更、`main` が `session = AuthorizedSession(creds)` を作成）。未使用だった `import requests` と `from google.auth import credentials` を削除。
- テスト: `scripts/tests/test_gsc_index.py` を新規作成。`get_latest_urls` / `load_credentials` / `request_indexing` / `main` を `unittest.mock` でカバレッジ（Google API 実呼出しなし）。

## Verification

- `python -m pytest scripts/tests/ -v` → **423 passed in 7.92s**（2026-10-18、修正前 413 → +10 新テスト）。
- 新テスト `scripts/tests/test_gsc_index.py`（10件・全 PASS）: `get_latest_urls`（ファイル不在/strip・空行除去）・`load_credentials`（env 不在で RuntimeError / searchconsole scope）・`request_indexing`（200→True / payload・timeout 検証 / 404→False）・`main`（URL なしで skip / 全成功で exit なし / 部分失敗で exit 1）。Google API は全件 `unittest.mock`（実呼出しなし）。
- CI 検証: push 後 `gh workflow run deploy.yml` で発火し「Request GSC indexing」ステップの成功を確認（run 結果は後記追記）。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
