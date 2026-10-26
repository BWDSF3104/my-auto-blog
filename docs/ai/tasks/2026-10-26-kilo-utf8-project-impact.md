# Kilo PowerShell UTF-8 変更のプロジェクト内影響調査

**Status**: 完了
**Date**: 2026-10-26
**Backlog**: なし（外部プラグイン調査の続行）
**Next Action**: 調査結果の検討: (1) pwsh 7 導入か (2) プラグイン注入削除か (3) 現状維持

## 意図 / 背景

Kilo Code の PowerShell UTF-8 対策（外部プラグイン `C:\Users\fujim\.config\kilo\plugin\powershell-utf8.js`）の続行調査。プラグインは各コマンドに UTF-8 初期化コード注入（コンソールエンコーディング設定・`$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'`）し、`shell.env` で `PYTHONUTF8`/`PYTHONIOENCODING` を設定する。
本調査の目的:
- コマンド注入（特に Get-Content 一部）を削除してもプロジェクトは破綻しないか
- Kilo シェルを PowerShell 7 (pwsh) に切替した場合（未導入）にプロジェクト内で何が変わるか
- 変更が 5.1 の既存経路（.cmd ラッパー等）に悪影響を及ぼさないか

前提（前回の調査で確定・ソース確認済み）:
- Kilo 7.8.15。現在実働シェルは Windows PowerShell 5.1.19041.7725。pwsh 未インストール
- Kilo 是 `powershell.exe -NoLogo -NoProfile -NonInteractive -Command` で起動 → **プロファイル読込なし**（env+profile 案は不成立）
- Kilo 内蔵層: `@opencode-ai/core/kilocode/powershell` がコンソールエンコーディング設定を既に行っている
- Kilo の Windows シェル選択は `win()` = `[pwsh, powershell, gitbash, cmd]` 順（pwsh があれば pwsh）

## 調査結果 / 変更内容

### 1. Windows 削除スクリプト: 影響なし

- `kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd` は **`powershell.exe`（5.1）を明示的に起動**している。Kilo が pwsh に切替しても、これらは 5.1 のまま → 動作不変。
- `.ps1` は自足型: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` を自身で設定（safe-remove.ps1:9 / safe-rmdir.ps1:9）。`Get-Content` パイプラインは使用していない（`Get-Item`/`Test-Path` 中心）→ プラグインの注入に依存しない。
- BOM 実態（検証済み）:
  - `safe-remove.ps1`: BOM 有（`efbbbf`）— 日本語コメント・メッセージ含みで**必須**（PS 5.1 は BOM なし .ps1 を ANSI 解釈）
  - `safe-rmdir.ps1`: BOM 無（`5b436d6c` = `[Cmdlet`）— 英語のみで**不要・問題なし**
- 将来 `.cmd` を `pwsh.exe` に変更した場合の残リスクも無: BOM 付きファイルは pwsh 7 でも問題なく解析される。

### 2. Python パイプライン: 低影響（環境変数依存のみ）

- 全エントリ点に win32 ガード + `sys.stdout.reconfigure(encoding="utf-8")` あり（generate_article.py:14-16, fetch_topics.py:39-40, fix_affiliate_links.py:25-26, fix_descriptions.py:12-13, genre_score.py:41-42, test_real_apis.py:40-41, maintenance/task_manager.py:33-35）→ **stdio は自保護済み**。
- ファイル I/O は全件明示 `encoding="utf-8"`（例: trends.py:26, archive_memory_bank.py:79/162/221）。
- subprocess 起動は全件出力 `encoding="utf-8"` 明示:
  - `trends.py:148`: `fetch_topics.py` 再実行（`[sys.executable, "-u", ...]`, `encoding="utf-8"`）
  - `archive_memory_bank.py:162`: `kilo-safe-*` 委譲（`encoding="utf-8"`）
  - `equivalence_check.py:57/307`: pytest ラナー（`PYTHONIOENCODING` 環境変数設定）
- **残る依存**: 直結 `pytest` / ad-hoc `python` の本体 stdout は ロケール cp932 フォールバック（Kilo が stdout をキャプチャするため）で、**プラグイン `shell.env` の `PYTHONUTF8`/`PYTHONIOENCODING` に依存**。現行 Python は **3.10.8**（PEP 686 未導入; 3.15 導入は `pillow-avif-plugin` cp315 wheel 未公開で保留、`2026-10-14-python315-upgrade.md`）。
  - この env 設定を削除すると: pytest 出力・ad-hoc python 実行で絵文字・cp932 未収録文字で `UnicodeEncodeError` / 文字化けのリスクが復活。パイプライン本体は再構成済みなので影響は限定的だが、**削除前に Python 3.15 移行を待たず削除するのは非推奨**。

### 3. docs / ルール: 変更不要

- AGENTS.md「Get-Content/Set-Content パイプライン禁止」: pwsh 7 移行後も維持。理由: (a) .cmd ラッパーは 5.1 を明示起動しており、その経路では 5.1 の ANSI 既定が効く (b) 防衛的。
- AGENTS.md「インラインコード禁止」の理由に「PowerShell 5.1 クォーティング/エンコーディング」がある。pwsh 7 移行で圧力は緩和されるが、ルール自体は維持。
- `docs/ai/workflow-test-procedure.md` の `$env:PYTHONUTF8="1"` 手動手順: 維持（3.10.8 現行。3.15 移行時に簡素化、`2026-10-14-python315-upgrade.md` next action #4）。
- スクラッチ .ps1 実行（`powershell docs\ai\tmp\<file>.ps1`）: 日本語含みなら BOM 付与・ASCII 維持方針は 5.1/pwsh 両方で有効。

### 4. VS Code 再起動バッチ / npm / CI: 影響なし

- `restart-vscode.bat`（ASCII のみ・CRLF）+ Python worker（subprocess は `encoding="utf-8"`）は powershell を使用しない。
- Node は stdio 既定 UTF-8。GitHub Actions CI は ubuntu → 無関係。

### 5. pwsh 7 導入時の変化（Kilo 内）

- Kilo シェル → pwsh 7: Get-Content 既定 utf8NoBOM 化でプラグインの注入部分が不要、コンソール設定も内蔵/既定で不要（無害）。`chcp 65001` 不要化。
- 5.1 への影響: **無**（`powershell.exe` 本体不変、.cmd ラッパーは 5.1 専用に固定、BOM 方針不変）。
- 確認方法（導入後）: 新セッションで `$PSVersionTable.PSVersion` = 7.x、`(Get-Process -Id $PID).Path` が pwsh.exe、`powershell.exe` 起動時は 5.1 維持の確認。

## 影響要約

| 変更に際し | プロジェクト内影響 |
|------------|--------------------|
| プラグインの Get-Content 注入削除 | **なし**（依存するプロジェクト内コンポーネント不存在） |
| プラグイン `shell.env`（PYTHONUTF8/PYTHONIOENCODING）削除 | **低**（pytest/ad-hoc python の cp932 フォールバックリスク。パイプライン本体は再構成済みで自保護） |
| pwsh 7 導入（Kilo シェル切替） | **5.1 非破壊**（.cmd ラッパーは 5.1 専 dụng、BOM 方針不変）。プラグイン注入は冗長化 |
| Python 3.15 移行 (PEP 686) | PYTHONUTF8 回避策簡素化可能（cp315 wheel 未公開で保留中） |

## Verification

- `python maintenance\task_manager.py add --slug kilo-utf8-project-impact ...` → タスクファイル作成、2 path staged
- `python maintenance\archive_memory_bank.py`（+ `--apply`）→ 0 action(s)（no-op）
- `python docs\ai\tmp\check_bom.py <2 .ps1>` → safe-remove.ps1: BOM True / safe-rmdir.ps1: BOM False
- `python --version` → 3.10.8
- grep: `generate_article.py`・`article/` に subprocess なし（`trends.py:148` のみ・encoding utf-8 明示）、全エントリ点 reconfigure 有、restart-vscode 系に powershell 使用なし
- 本調査はファイル変更なし（スクリッチのみ `docs\ai\tmp\check_bom.py`、gitignore 対象）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] `known-issues/` ファイルの archive 移動（該当なし）
- [ ] `backlog.md` の完了項目削除（該当なし）
