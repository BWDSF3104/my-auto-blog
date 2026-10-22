# safe系を maintenance へ移動 / .kilo/ 検証免除除外 / ルール衛生

**Status**: 完了
**Date**: 2026-10-22
**Next Action**: commit + push（git add -A; git commit; git push）

## 意図 / 背景

- AI が `.kilo/` を作業スペースとして使う傾向の成因（2026-10-22 調査）:
  - AGENTS.md「コード検証」例外に `.kilo/` が含まれる → 検証不要ゾーン（書き込み摩擦ゼロ）
  - 2026-10-14 決定で `.kilo/scripts/` を「Kilo 設定・削除検証スクリプト（`safe-*.ps1`）の置き場」に指定 → ps1 使い捨ての非本番置き場は `.kilo/scripts/` のみ
  - Kilo システムプロンプト `<env>` ブロックの「新規コマンド・エージェントは `.kilo/` に放置」
  - `.gitignore`（`.kilo/screenshots/`）と `.kilo/.gitignore`（`agent-manager.json`）で部分 git 不可視
- 本タスク:
  1. `.kilo/` を AGENTS.md 検証免除リストから除外（通常操作しない場所）
  2. `safe-remove.ps1` / `safe-rmdir.ps1` を `maintenance/` に移動（影響調査付き）
  3. `.gitignore` の `.kilo/screenshots/` 行を削除（スクリーンショット流は廃止済み）

## 調査結果 / 変更内容

### 影響調査（safe系移動）
- 直接参照: `.kilo\scripts\safe-*.ps1` を指すのはルートの 2 `.cmd` と 2 ps1 ヘッダーコメントのみ。残りはドキュメント（決定・タスク記録=歴史記録）。
- **projectRoot 解決（影響あり）**: 元コード `Resolve-Path(Join-Path $PSScriptRoot '..\..')` は `.kilo/scripts/` の深度 2 を前提。`maintenance/`（深度 1）では `..\..` がプロジェクトルートの 1 つ上（`AutoBlog`）に解決 → 全削除が「対象が存在しない」で失敗。
  - 修正案 A（`.git` まで遡上ループ）: 動作は確認されたが、ユーザー却下（「非常に効率が悪く、.git が前提でしか動かない」）。
  - 修正案 B（**採用**）: 1 段階 `..` の直接解決 — `$projectRootFull = GetFullPath(Join-Path $PSScriptRoot '..')`。スクリプトは `.cmd` から深度 1 で呼ばれ固定 → 決定的・ループ不要・`.git` 前提なし。
- `.git` / `.kilo` 保護領域ガード不変（スモークで `.kilo\agent-manager.json`・`.kilo\scripts` の拒否確認）。
- Python 変更なし（`archive_memory_bank.py` は `.cmd` 名・位置不変の委譲）。テスト変更要件なし（fake runner）。
- Astro 変更なし → build 不要。
- 初期スモークで `.cmd` 内部パスの誤りも検出・修正: 元コードの `%~dp0.kilo\` は `.kilo` がディレクトリ名（ドット込み）だったのに対し、`maintenance` はドットなし → 正解は `%~dp0maintenance\`。

### 変更内容
- `maintenance/safe-{remove,rmdir}.ps1`: `.kilo/scripts/` から `git mv`。ヘッダーコメント更新。projectRoot 解決行を 1 段階 `..` に変更
- `kilo-safe-{remove,rmdir}.cmd`: 内部パス → `%~dp0maintenance\safe-*.ps1`
- `AGENTS.md`: 検証免除例外から `.kilo/` を削除
- `.gitignore`: `.kilo/screenshots/` 行削除
- 決定記録: `docs/ai/decisions/2026-10-22-safe-scripts-maintenance.md`
- known-issues: `KI-20261022-02-kilo-scripts-empty-dir.md`（`.kilo/scripts/` 空ディレクトリ削除不能）

### 回答（質問項目）
- 「システム情報」: Kilo システムプロンプトの `<env>` ブロック（リポジトリ外。リポジトリでは変更不可。Kilo バージョンが決定する）。
- `.gitignore` `.kilo/screenshots/`: **2026-10-01 commit 23fb19e**（「chore: add deploy workflow rule and screenshot directory to AGENTS.md」）で追加。意図: Kilo CLI のローカルスクリーンショットキャッシュを git 外に。2026-10-15 以降は `I:\マイドライブ\kilo` への送付フローへ移行し、ディレクトリは存在しない → 削除済み（本タスク）。
- `.kilo/.gitignore` の `agent-manager.json`: 意図は「agent-manager.json は UI/リカバリ状態（セッション一覧・タブ順・active target）で、マシン/ユーザー固有の運行データであり設定ではない」ため commit 排除。`.kilo/.gitignore` 自体は未追跡（自己 gitignore により git history 不存在）→ 追加日は記録不可。ファイル生成 2026-09-29、agent-manager.json 初セッション 2026-10-04（mtime 2026-10-11）。

## Verification

- `pytest scripts/tests/ -v`: **454 passed** (9.11s)
- `pytest maintenance/tests/ -v`: **53 passed** (3.99s)
- スモークテスト（最終 `..` 解決・2026-10-22 11:43 前後）:
  - `./kilo-safe-remove.cmd docs\ai\tmp\kilo-move-smoke.txt` → 「ゴミ箱に移動」、消失 ✓
  - `./kilo-safe-rmdir.cmd docs\ai\tmp\kilo-move-smoke-dir` → 「Sent to Recycle Bin」、消失 ✓
  - `./kilo-safe-remove.cmd .kilo\agent-manager.json` → 「保護された領域の削除は禁止されています」、対象無傷 ✓
  - `./kilo-safe-rmdir.cmd .kilo\scripts` → 「Deleting protected area is not allowed」、対象無傷 ✓
- 初期スモーク: 全失敗（`.maintenance` 誤パス）→ `.cmd` 修正
- 2 回目スモーク: 全失敗（`..\..` 深度誤差 → ルートが 1 つ上）→ ps1 projectRoot 解決修正
- 最終スモーク: 全 PASS
- 編码: safe-remove.ps1 BOM 保持（HEAD と一致）、safe-rmdir.ps1 BOM なし（HEAD と一致）
- build 不要（Astro 変更なし）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
