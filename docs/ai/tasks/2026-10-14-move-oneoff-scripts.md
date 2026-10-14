# 2026-10-14: scripts/ のワンオフスクリプトを maintenance/ へ移動

**Status**: 保留
**Next Action**: 未着手（`2026-10-14-archive-script.md` の Phase 5 完了後に着手予定）

## 概要

`scripts/`（本番パイプライン置き場）に混入しているパイプライン外のワンオフスクリプトを、開発用ツール置き場 `maintenance/` へ `git mv` する。`2026-10-14-memory-bank-cleanup-script` の決定に基づく後続タスク。

## 対象（8 ファイル・git 追跡済み）

| 種別 | ファイル | 備考 |
|------|---------|------|
| ワンオフ修正ツール | `fix_affiliate_links.py` / `fix_descriptions.py` | docstring に「パイプライン未組み込み」と明記 |
| 使い捨てデバッグ | `_check_html_desc.py` / `_check_space.py` / `_check_space_logs.py` / `_check_space_runtime.py` / `_scan_desc.py` | docs 内参照なし（2026-10-14 grep 確認） |
| HF 生成テスト | `_test_hf_space.py` | `docs/ai/architecture.md` の HF Space デプロイ手順が参照 → 移動時に参照更新が必要 |

## 対象外（`scripts/` 留置）

- `scripts/hf-space/`（`app.py` / `requirements.txt` / `TEST_RULES.md`）: HF Space のソース。architecture.md・README.md が参照する本番コンポーネント。削除しない（2026-10-14 に「空ディレクトリ」と誤報告したが誤り）
- `fetch_topics.py` / `generate_article.py` / `genre_score.py` / `generate-search-index.js` / `article/` / `prompts/` / `tests/` / `data/` / `requirements.txt`: パイプライン本体

## 手順

1. 8 ファイルへの参照 grep（`docs/ai/*.md`・`README.md`・CI・`package.json`）。過去記録（`tasks/archive/`・`plans/archive/`・`known-issues/archive/`・`decisions/archive/`）は変更しない
2. `git mv` 8 ファイル → `maintenance/`
3. 生存ドキュメントの参照更新（`docs/ai/architecture.md` :122 等）
4. `pytest scripts/tests/ maintenance/tests/ -v`（テスト収集への影響なしを確認。`_test_hf_space.py` は `scripts/tests/` 外のため pytest 収集対象外）
5. Verification 記録

## Verification

- TBD
