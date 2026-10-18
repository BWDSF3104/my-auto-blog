# CI 自動生成の SITE_ORIGIN NameError 修正と再実行

**Status**: 完了
**Date**: 2026-10-18

## 意図 / 背景

2026-10-18 09:48 JST の scheduled run（databaseId 39084122543）が `NameError: name 'SITE_ORIGIN' is not defined`（`scripts/generate_article.py:427`）で失敗。原因調査 → 修正 → 再実行まで実施する。

## 調査結果 / 変更内容

### 原因
- コミット `5d80f14`（2026-10-17 22:39 JST、GSC インデックス登録機能）が `scripts/article/config.py:57` に `SITE_ORIGIN` を追加したが、`__all__`（327〜355行）への追加を漏れていた。
- `generate_article.py:27` は `from article.config import *` であり、star import は `__all__` に従うため `SITE_ORIGIN` がスコープに入らず、`_write_new_article_url()`（420-434行）が NameError を送出。
- 10/17 10:12 JST の run（38989891690）は `5d80f14` 前のコード実行で成功。本件は新コードを含む初の run で発現。
- テスト漏れ: `_write_new_article_url` / `SITE_ORIGIN` のテストが `scripts/tests` に存在しない（grep 0件）。

### 修正
- `scripts/article/config.py:337`: `__all__` に `"SITE_ORIGIN"` を追加（`"BASE_URL"` の隣）。1 行変更。
- コミット `264346b`、push 済み。

### 再実行
- 失敗 run（39084122543）の `gh run re-run` は修正前のコミット（`1b8b75f`）で再実行されるため、`gh workflow run deploy.yml` で修正済み main（`264346b`）上に新規 run を発火（run 39090062867、workflow_dispatch）。

### 副次発見（本タスク完了に必須でない）
- GSC インデックス登録ステップ（`continue-on-error: true`）が `TypeError: 'Session' object is not callable` で失敗（`scripts/gsc_index.py:70` の `creds.refresh(requests.Session())` が google-auth の要求する callable でない）。非致命だがインデックス登録要求は届いていない。`docs/ai/known-issues/KI-20261018-02-gsc-index-session-not-callable.md` に記録。

## Verification

| 項目 | コマンド / 手順 | 結果 |
|---|---|---|
| Python テスト | `pytest scripts/tests/ -v` | 413 passed（7.97s） |
| star import 確認 | `python docs/ai/tmp/check_star_import.py`（一時スクリプト） | `SITE_ORIGIN = https://BWDSF3104.github.io` を確認 |
| CI 再実行 | `gh workflow run deploy.yml` → run 39090062867（headSha `264346b`） | generate 成功（3m59s）、build-and-deploy 成功（25s） |
| 生成物 | `git ls-tree origin/main` | `src/content/posts/2026-10-18-112737-auto-post.md`、`data/new_urls/2026-10-18.txt`（`https://BWDSF3104.github.io/my-auto-blog/posts/koku-no-kage-to-hoshikuzu-no-chikai`）コミット確認 |
| GSC ステップ | run 39090062867 の generate ジョブ log | `TypeError: 'Session' object is not callable` で失敗（非致命・known-issue 記録済み） |

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
