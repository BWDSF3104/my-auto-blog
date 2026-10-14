# インライン Python 実行例外の廃止 + Python 3.15 アップグレード影響調査

**Status**: 完了（未コミット）
**Date**: 2026-10-14

## 背景

ユーザー指示 (2026-10-14): 「Pythonスクリプト実行時の例外を廃止する。理由として大抵実行失敗しているから」。併せて「Pythonアップグレードによるプロジェクトへの影響はあるか？」を調査。

## 変更内容

- `AGENTS.md` `## Command Execution Rules`: Rule 2 の「Exception: 一行・副作用なし確認は allow」を廃止 → **例外なし**。全ての Python コード（一行確認含む）は `C:\Users\fujim\AppData\Local\Temp\kilo\` へのスクリプトファイル書き出し + `python <file>` 実行。理由: インライン `python -c` は PowerShell 5.1 のクォート/エスケープ・cp932 コマンドラインで実行失敗が多い
  - 2026-10-14 同日: 冗長だった独立ブレット `No exceptions: even one-line or side-effect-free checks...`（主文の禁止の反復）を削除し、理由部分のみ主文に括弧補足として統合
- `kilo.jsonc` は**不変**: `python -c *` / `python - *` は `allow` のまま（承認ゲート層と行動ルール層の分離設計（`decisions/2026-10-13-command-approval-global.md`）は維持。ゲート層で `ask` 化したい場合は要指示）

## 調査結果: Python 3.10.8 → 3.15 アップグレード影響

### 結論

- コードへの**ネガティブ影響なし**。アップグレードは安全（依存パッケージの再インストール・cp315 wheel 検証が必要）
- 主benefit: **PEP 686**（UTF-8 mode 既定有効化）が Python 3.15.0（2026-10-09 リリース）で実装。パイプ接続 stdio の cp932 フォールバックが解消され、文字化け・絵文字 `UnicodeEncodeError`（`tasks/2026-10-09-windows-console-encoding.md`）が解消。`PYTHONUTF8=1` / `-X utf8` 回避策が不要になる
- PowerShell 5.1 `Get-Content`/`Set-Content` パイプライン破損は **PowerShell 側の問題で Python アップグレードでは直らない**（AGENTS.md 禁止ルール継続）

### 検証済み項目（全て問題なし）

- ファイル I/O は全件 `encoding="utf-8"` 明示指定（encoding 未指定 `open()` なし。`Image.open` / `tarfile.open` はバイナリ）
- 6 スクリプトの `sys.stdout.reconfigure(encoding="utf-8")` → 3.15 では no-op（安全・維持可）
- `subprocess` は `trends.py:150` / `equivalence_check.py:309` が `encoding="utf-8"` 明示。`equivalence_check.py:515`（git rev-parse）のみ encoding 未指定 `text=True` だが出力は ASCII → 問題なし
- 3.12/3.13 で削除されたモジュール（`distutils` / `imp` / `cgi` / `smtpd` / `asynchat` / `msilib` / `tkinter`）不使用
- `locale.getpreferredencoding()` 不使用（3.15 で utf-8 を返すようになり得るが影響なし）

### 環境

| 項目 | 現状 |
|------|------|
| ローカル | Python 3.10.8（グローバル・venv なし: `C:\Users\fujim\AppData\Local\Programs\Python\Python310\`） |
| CI | GitHub Actions `python-version: '3.11'`（`deploy.yml` / `genre-score.yml`） |
| README | 「Python 3.10+」 |
| 依存 | `python-dotenv` / `pyyaml` / `requests` / `pytest` + パイプライン実使用 `google-genai` / `gradio_client` / `Pillow` + `pillow-avif-plugin` |

> 注: 「ローカル 3.10.8」は `python`（PATH 解決）ベース。`py --list` 上は 3.13.14 / 3.12.2 / 3.7.8 / Anaconda py39 も共存（詳細は `2026-10-14-python315-upgrade.md` を参照）。

### 注意点・次のステップ候補

- venv なしのグローバル運用 → 3.15 導入後、依存を再インストールし import 検証が必要。C 拡張系（`Pillow` / `pillow-avif-plugin`）は cp315 wheel の有無を確認（`pillow-avif-plugin` は wheel なしなら Windows ソースビルドで摩擦）
- アップグレード後 `pytest scripts/tests/ -v` で全テスト確認
- オプション: CI の `python-version` を 3.15 へ、README のバージョン表記更新、`workflow-test-procedure.md` の `PYTHONUTF8` 回避策の簡素化（検証完了まで維持推奨）

## Verification

- コード変更なし（`AGENTS.md` + `docs/ai/` のみ）→ AGENTS.md 例外規定により pytest / `npm run build` 不要
- `git status` 編集前: クリーン。Edit ツール使用（UTF-8 破損リスクなし）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv`: 参照行不要（本タスクは作成時点で完了・未コミット）
- [x] `decisions/`: 設計判断（ゲート/行動ルール分離）は不変 → 新ファイル不要
