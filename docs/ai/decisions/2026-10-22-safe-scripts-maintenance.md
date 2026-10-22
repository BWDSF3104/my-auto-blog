# safe系スクリプトを maintenance/ へ移動・.kilo/ を検証免除除外

**Date**: 2026-10-22

**Decision**:
- `safe-remove.ps1` / `safe-rmdir.ps1` を `.kilo/scripts/` から `maintenance/`（開発用ツール置き場）へ移動。ルートの `.cmd` ラッパー（`kilo-safe-{remove,rmdir}.cmd`）は名称・位置不変、内部の ps1 パスのみ更新（`%~dp0maintenance\`）。
- projectRoot 解決を **1 段階 `..` の直接解決** に変更: `$projectRootFull = GetFullPath(Join-Path $PSScriptRoot '..')`（元 `..\..` を代替）。
- AGENTS.md「コード検証」例外から `.kilo/` を削除（`.kilo/` は Kilo 設定・ランタイム領域で、通常操作しない場所）。
- `.gitignore` から `.kilo/screenshots/` 行を削除（スクリーンショット保存先は廃止済み）。

**Background**:
- AI が `.kilo/` を作業スペースとして用いていた原因: (a) AGENTS.md 検証免除例外に `.kilo/` が含まれること、(b) 2026-10-14 決定で `.kilo/scripts/` が ps1 の置き場と指定され使い捨て ps1 への最低摩擦経路となっていたこと、(c) Kilo システムプロンプト `<env>` の「新規コマンド・エージェントは `.kilo/` に放置」、(d) `.kilo/` 一部が git 不可視。
- 移動は projectRoot 解決に影響: 元コードの `..\..` は `.kilo/scripts/` の深度 2 を前提（`.kilo` 1 段階 + `scripts` 1 段階）。`maintenance/`（深度 1）では `..\..` がプロジェクトルートの**1つ上**に解決 → スモークテストで全削除が「対象が存在しない」で失敗（影響確認済み）。
- 修正案 `.git` まで遡上するループは**ユーザー却下**（「非常に効率が悪く、.git が前提でしか動かない」）。最終: スクリプトが深度 1 で固定されている以上、`..` の1段階解決は決定的で、ループも `.git` 前提も不要。

**Impact**:
- 参照変更: `.cmd` ×2（内部パス）、ps1 ヘッダーコメント ×2、ps1 projectRoot 解決行 ×2。それ以外はドキュメントのみ。
- `.git` / `.kilo` 保護領域ガード不変。
- Python 変更なし（`archive_memory_bank.py` は `<root>\kilo-safe-{remove,rmdir}.cmd` 経由委譲、.cmd 名・位置不変）。テスト変更不要。
- Astro 変更なし → build 不要。
- 最終スモーク: ファイル削除・ディレクトリ削除・`.kilo` 保護領域 2 拒否、全 PASS。

**Unchanged**:
- `.cmd` ラッパーの名称・配置（`archive_memory_bank.py`、AGENTS.md、bash allow パターン `kilo-safe-*` が参照）
- `.git` / `.kilo` 保護
- `.kilo/.gitignore` の `agent-manager.json` 除外（UI/リカバリ状態の意図的 git 管理外）

**Residual**:
- `.kilo/scripts/` 空ディレクトリが残存（ガードにより `.kilo/` 削除を拒否。意図的保護のため放置。`known-issues/` に記録）。
