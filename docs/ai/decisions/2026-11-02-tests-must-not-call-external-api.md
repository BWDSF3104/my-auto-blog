# my-auto-blog のテストは外部 API を呼ばない（禁止継続）

**Date**: 2026-11-02

## Decision

テストスクリプトでの外部 API 呼出しは**禁止を継続**。API キー・クォータ・レート制限を要するサービス（Gemini / HuggingFace / e621 / 楽天 / Cloudflare Workers AI 等）は `unittest.mock` でモックする。

例外: 公開エンドポイントで認証・クォータ不要な RSS フィードは実呼出しを許可。

## 対象外

`scripts/tests/test_real_apis.py` は `__test__ = False` により pytest 集外であり、本決定の禁止対象ではない。独立実測スクリプトとして、`docs/ai/api-rate-limits.md` のレート制限を守って実行する（`--save` で `scripts/data/api_test_results/` に保存）。

## 背景

正典 `AGENTS.md` の外部 API 禁止条が 2026-11-02 に削除され、可否がプロジェクト依存となった（決定: `S:\Documents\Kilo_Commons\Common_Operations\docs\ai\decisions\2026-11-02-test-external-api-policy-per-project.md`）。本プロジェクトは禁止を継続する側として AGENTS.md に明記。

## Impact

- `AGENTS.md`（コード検証条）に禁止継続・RSS 例外・`test_real_apis.py` の位置づけを追記
- 既存テスト（`scripts/tests/`）は全 mock のまま → コード変更なし
- `README.md` の記述はプロジェクト方針として自立（変更なし）
