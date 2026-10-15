# 2026-10-15: Temp\kilo クリーンアップ + スクラッチ置き場を docs/ai/tmp/ へ転用

**Status**: 完了（2026-10-15）
**Date**: 2026-10-15

## 背景

`C:\Users\fujim\AppData\Local\Temp\kilo\` が 2,801 ファイル / 約 105.7MB まで蓄積。原因は AGENTS.md の scratch 指定と Kilo sandbox の `TEMP`/`TMP`/`TMPDIR` リダイレクト（kilocode `packages/opencode/src/kilocode/sandbox/policy.ts:273-275`）が重畳し、自動クリーンアップ機構がなかったこと。scratch 置き場をリポジトリ内 `docs/ai/tmp/`（`.gitignore:34` の `tmp/` ルールと `archive_memory_bank.py` のタスク開始時全削除が既に定義済み）へ転用し、%TEMP%\kilo は初回クリーンアップ（インベントリ → 承認 → 削除）で解消する方針。新規スクリプト作成は不要（ユーザー指示）。

## 調査結果

- `serve\my-auto-blog`（311 ファイル 13.1MB）: 公式 CLI リファレンス（`kilo.ai/docs/code-with-ai/platforms/cli-reference`）で `kilo serve` は "headless Kilo server 起動" と確認 → 静的サイト staging 機能は存在しない。Astro build 出力の session scratch（再生成可能）→ **削除候補**
- `remote-attachments\`: Kilo 自前 scratch（`remote-attachments.ts` の `SCRATCH_DIRNAME`、`dispose()` で自削除）。1 日前より古い orphan → 削除候補
- `eq\`（2,396 ファイル 46.5MB）: 等価検証ワークエリア（タスク `2026-10-12-refactor-equivalence-verification.md` 完了・結果はコミット済み）→ 削除候補
- トップレベル `python-3.15.0-amd64.exe`（43MB）: Python 3.15 は `Python315\` に導入済み → 不要。`pillow_avif_pypi.json`: cp315 wheel 欠如（結論済み・backlog P3 #11）の調査データ → 不要
- `gh_actions_ips.txt` / `deploy_822e1d8_cp932.txt` 等: repo 参照ゼロの使い捨て調査成果物
- repo 内旧場所参照は 12 箇所、うちライブ参照 3 箇所（`AGENTS.md` / `docs/ai/manual-article-workflow.md` / `scripts/tests/equivalence_check.py`）。残り 9 件は `tasks/` 履歴（変更しない）

## 変更内容

- `AGENTS.md` Command Execution Rules: scratch → `docs\ai\tmp\`（gitignore + タスク開始時全削除の注記付き）
- `docs/ai/manual-article-workflow.md`: `Invoke-WebRequest -OutFile` の保存先 → `docs/ai/tmp/{name}.png`
- `scripts/tests/equivalence_check.py`: `EQ_DIR` 既定値 → `ROOT/docs/ai/tmp/eq`（環境変数 `EQ_TMP_DIR` 上書き可）・docstring「Temp 配下」→「scratch（docs/ai/tmp/eq）」
- `docs/ai/memory-bank-guide.md`: ファイル一覧表に `tmp/` 行追加（バッチクリーンアップ節は既に `tmp/` 全削除を定義済み）
- `docs/ai/backlog.md`: P3 #12 追加（`docs/ai/tmp/` の日付管理オプション。実装時は `archive_memory_bank.py` と AGENTS.md 文言を**同時に**改修する旨を明記）
- `docs/ai/tmp/` ディレクトリ新規作成（インベントリ TSV 格納先）
- `decisions/2026-10-15-scratch-location.md` を新規作成

## %TEMP%\kilo 初回クリーンアップ

- インベントリ: `docs/ai/tmp/kilo-temp-inventory.tsv`（2,801 ファイル）
- 削除候補: 2,796 ファイル 105.7MB — トップレベル 88 ファイル（1 日前より古い）+ `eq\` 2,396 ファイル + `serve\my-auto-blog` 311 ファイル + `remote-attachments\` orphan 1 ファイル
- 保持: 当日（10/15）のトップレベル 5 ファイル（`check_env.py` / `check_merge_drift.py` / `clean_merge_drift_data.py` / `make_cta_test_post.py` / `poll_space.py`）
- ユーザー指示: 削除対象を先にプロジェクトの `docs/ai/tmp/kilo-temp-quarantine` へ移動し、`kilo-safe-rmdir.cmd`（git 管理下のツール）で削除（%TEMP% への直接 `Remove-Item` は行わない）
- 実行: 移動 2,796 ファイル（105.7MB 確認）→ `./kilo-safe-rmdir.cmd docs/ai/tmp/kilo-temp-quarantine` → `Deleted: docs\ai\tmp\kilo-temp-quarantine`
- 結果: %TEMP%\kilo に KEEP 5 ファイルのみ残存（検証済み）

## Verification

- `python -m pytest scripts/tests/ -v` → **404 passed**（8.17s、エラー 0）
- `Temp[\\/]kilo` grep → 残 9 件すべて `tasks/` 履歴（ライブ参照 0）
- 隔離移動検証: %TEMP%\kilo 残 5 件 / 隔離 2,796 件・105.7MB（移動前照合 2,801 = 93 + 2,708）
- `./kilo-safe-rmdir.cmd docs/ai/tmp/kilo-temp-quarantine` → 削除成功
- 削除後検証: %TEMP%\kilo に KEEP 5 ファイルのみ・隔離フォルダ `quarantine_exists=False`

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] `plans/2026-10-15-kilo-temp-cleanup.md` を `plans/archive/` へ `mv`
