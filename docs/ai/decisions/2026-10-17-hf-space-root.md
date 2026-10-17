# HF Space デプロイ元ソースをトップレベル (hf-space/) へ移動

**Date**: 2026-10-17

**Decision**: `scripts/hf-space/` をトップレベルの `hf-space/` へ移動する。`scripts/` は本番パイプライン（CI 実行対象）のスクリプト置き場として純粋化し、HF Space ソースは独立したデプロイ先（`blume/kemono-image-api`）を持つトップレベルコンポーネントとして扱う。

**Reason**: ユーザー指摘 — `blume/kemono-image-api` は自社管理の HF Space であり、そのデプロイ元が「GitHub Actions パイプライン用スクリプト置き場 `scripts/`」内にあると位置づけがわかりづらい。2026-10-14 の決定（`2026-10-14-memory-bank-cleanup-script.md`）でも `scripts/hf-space/` は本番コンポーネントとして `scripts/` に留置していたが、今回の整理でトップレベルへ昇格する。

**Rejected Alternatives**:

- `scripts/hf-space/` に留置: パイプラインスクリプトの中に本番インフラのソースが埋もれ、発見しにくい（ユーザー否決）
- `maintenance/` へ移動: `maintenance/` は「開発用ツール（本番パイプライン外）」置き場であり、本番のデプロイ元を置く不適切な場所

**Impact**:

- 移動: `scripts/hf-space/{app.py,requirements.txt,TEST_RULES.md}` → `hf-space/`（`git mv`）
- 参照更新: `README.md`（構造ツリー）、`docs/ai/architecture.md`（新コンポーネントセクション + デプロイ手順）、`AGENTS.md`（プロジェクト構成）、`hf-space/TEST_RULES.md`（アップロードパス + duration=20 への整合）
- 過去のタスク・決定記録（`tasks/2026-10-05〜15-*`、`decisions/2026-10-14-*`）の `scripts/hf-space/` 参照は歴史記録のため不変
- `docs/ai/tasks/2026-10-14-move-oneoff-scripts.md`（保留）の対象外リストの `scripts/hf-space/` 行は本タスクにより失効（当該タスクは `_test_hf_space.py` 等のワンオフスクリプト移動のみが残る）
- CI（`.github/workflows/`）は `hf-space/` を参照していない（2026-10-17 grep 確認）ため影響なし
