# ログ・出力先の最小修訂（equivalence_golden 移動・new_urls クリーンアップ追加）

**Status**: 完了
**Date**: 2026-10-22
**Next Action**: equivalence_golden を scripts/tests/ へ移動し、new_urls に30日クリーンアップ関数を追加

## 意図 / 背景

ログ・出力先の最小修訂（`docs/ai/log-locations.md` 整理提案 #1 #2 対応）:
1. テストフィクスチャ `equivalence_golden/` がランタイムの `data/` に置かれ、置き場所のズレがある → `scripts/tests/` へ移動
2. `data/new_urls/` が無限蓄積 → 30日ベースの日付クリーンアップ追加
（#3 `drafts` 改名、#4 `api_test_results` 位置変更は任意/不要と判断し本次実施なし）

## 調査結果 / 変更内容

### 1. `equivalence_golden` を `scripts/tests/` へ移動
- `git mv data/equivalence_golden scripts/tests/equivalence_golden`
- `scripts/tests/equivalence_check.py:34`: `GOLDEN = ROOT / "data" / "equivalence_golden"` → `ROOT / "scripts" / "tests" / "equivalence_golden"`
- `build_golden.py:26`: `ROOT = Path(__file__).resolve().parents[2]` → `parents[3]`（移動後の `root/scripts/tests/equivalence_golden/build_golden.py` で repo root を指すため）
- `build_golden.py` ドキュメントストリング（3行: 再構築対象パス、19行: 使い方パス）を更新
- `docs/ai/log-locations.md`: 12番のパスを 2箇所で更新、12番セクションに移動歴追記

### 2. `new_urls` クリーンアップ追加
- `scripts/article/config.py`: `NEW_URLS_DIR = "data/new_urls"` 追加（`__all__` に）
- `scripts/generate_article.py`:
  - `_write_new_article_url()`: `out_dir = os.path.join("data", "new_urls")` → `out_dir = NEW_URLS_DIR`
  - 新規 `cleanup_old_new_urls(keep_days: int = LOG_CLEANUP_DAYS) -> int`: `data/new_urls/{YYYY-MM-DD}.txt` を日付（JST）で keep_days 日前のものを削除。.gitkeep・非日付ファイルは除外。削除件数を返す。`_cleanup_old_logs` と同方針（日付パース失敗・除外対象は安全側保持）
  - `finalize_and_save()`: `_write_new_article_url()` の**後**に `cleanup_old_new_urls()` を呼出（当日ファイルが先により消されないため）
- `scripts/tests/test_generate_article.py`: `TestCleanupOldNewUrls` 6件追加
  - 古い削除+最新保持 / 全て最近で保持 / .gitkeep 非削除 / 非日付ファイル非削除 / 不存在ディレクトリで例外なし / カスタム days しきい値（30日 vs 60日）

## Verification

- `pytest scripts/tests/ -v` → **454 passed** (7.55s)（新規 6 件含む、実 API 未消費）
- `grep data/equivalence_golden *.py` → **0 件**（コード残参照なし。ドキュメントの過去タスク記録のみ）
- `Get-ChildItem data -Directory` → equivalence_golden 消滅、実ランタイムディレクトリ8件のみ（affiliate_logs, drafts, genre_scores, new_urls, prompt_logs, topics, trend_usage_logs + 単一ファイル）
- 変更: Python 5ファイル（generate_article.py, config.py, equivalence_check.py, build_golden.py, test_generate_article.py）+ docs 1ファイル（log-locations.md）
- 変更が deploy.yml の paths（`src/**` 等）に該当しないため、自動デプロイはトリガーされない

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
