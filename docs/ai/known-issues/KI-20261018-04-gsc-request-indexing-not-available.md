# GSC「インデックス登録要求」(Request Indexing / write) が公開 API に存在しない

**Date**: 2026-10-18
**状態**: 既知の制約（API 非対応・設計上の限界）。コードで解決不可のため、意図と実装のズレを記録する。

## 背景 / 本来の意図

- `scripts/gsc_index.py`（`deploy.yml` step 1-D）の本来の意図は、新規記事 URL に対してネイティブな「インデックス登録要求」（GSC UI の "Request Indexing" ボタン相当の write 操作）を API 経由で自動化すること。
- 旧実装は `urlInspection/index.update` を呼んでいたが、**このエンドポイントは存在しない**（実 API probe で 404 確認）。

## 確認した事実（2026-10-18 調査）

- GSC API v1 の `urlInspection.index` リソースは **`inspect` の 1 メソッドのみ**。ネイティブな「Request Indexing」（write）は**公開 GSC API に存在しない**（GSC UI 限定）。
- Indexing API（Publish API）は invite-only・`JobPosting` / `BroadcastEvent` 限定で、**通常のブログ記事には非対応**。
- したがって、新規ブログ記事 URL へのネイティブな「インデックス登録要求」は API 経由で自動化できない。

## 現在の代替実装

- `urlInspection/index:inspect`（read）を呼び出し、Google による URL の**再チェック（再確認）を促す**。これが公開 API 上で最も近い代替。
- 関数名（`request_indexing` → `inspect_url_indexing`）・`deploy.yml` step 名・docstring を実態（inspect = 再チェック nudge）に合わせて修正済み（タスク: `docs/ai/tasks/2026-10-18-gsc-index-refresh-fix.md`）。
- 実際のインデックス登録は主に **sitemap** が担う（本ステップは補助的な再チェック nudge）。

## 影響 / 制約

- 新規記事 URL へのネイティブな「インデックス登録要求」は API 経由で自動化できない（API 制約・恒久）。
- 本ステップは「再チェックの nudge」であり、ネイティブ要求と同等の効果は保証されない。
- 優先記事でネイティブな要求が必要なら、**GSC UI の "Request Indexing" ボタンを手動で**使う（非自動化）。

## 対応状況

- 2026-10-18: タスク `docs/ai/tasks/2026-10-18-gsc-index-refresh-fix.md` で確認・命名/コメント修正を実施。本件は API 制約のため「未解決」のまま継続（既知の制約として記録）。
