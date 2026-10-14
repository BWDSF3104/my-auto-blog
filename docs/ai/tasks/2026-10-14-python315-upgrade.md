# 最新 Python（3.15.0）導入 — コマンドラインインストール調査

**Status**: 保留（バックログへ移行 2026-10-14）— `python` は 3.10.8 / cp315 wheel 待ち
**Date**: 2026-10-14

## 背景

ユーザー (2026-10-14): 「最新バージョンPythonはコマンドラインで導入可能か？また、その際のインストール際などはどうなる?」`2026-10-14-inline-python-exception-removal.md` のアップグレード影響調査の続行。

## 調査結果

### 利用可能性

- 最新安定版: **Python 3.15.0**（2026-10-09 リリース）。公式インストーラ URL の存在確認済み: `https://www.python.org/ftp/python/3.15.0/python-3.15.0-amd64.exe`（45,383,680 bytes、HTTP 200 OK）
- **winget 最新 = 3.14.7**（`Python.Python.3.14`）。**3.15 は winget に未登録**（`winget update` 後 `winget search --id Python.Python.3.15` → 該当なし、2026-10-14 時点）

### ローカル環境の実態（前タスクファイルの補正）

- `python`（PATH 解決）→ **3.10.8**（`C:\Users\fujim\AppData\Local\Programs\Python\Python310\`）
- `py --list`: **3.13.14（py 既定 `*`）** / 3.12.2 / 3.10.8 / 3.7.8 / Anaconda py39 → **複数 Python が共存**（前タスクの「ローカル 3.10.8 のみ」は `python` 解決ベースの記述で、py レジストリ上は 3.13 含む複数存在）
- 配置: `%LOCALAPPDATA%\Programs\Python\` に Python310 / 312 / 313（全て per-user）。`Program Files` 側に machine スコープの Python なし
- 3.12 / 3.13 のディレクトリは **PATH 未登録**（`where.exe python` は 3.10 と WindowsApps エイリアスのみ）→ `python` と `py -3`（3.13.14）で別バージョンを指す現状

### インストール挙動（winget マニフェスト実物で確認）

winget-pkgs `manifests/p/Python/Python/3/14/3.14.7/Python.Python.3.14.installer.yaml`:

- winget は公式 EXE（burn ブートストラッパー）をラップ。x64 user scope: `InstallerUrl: .../python-3.14.7-amd64.exe`、`InstallerSwitches.Custom: InstallAllUsers=0 PrependPath=1`、silent は `--quiet`
- `InstallAllUsers=0` → **per-user**（`%LOCALAPPDATA%\Programs\Python\Python3XX\`）、**UAC 不要**。machine scope（`InstallAllUsers=1`）は自己昇格（`elevatesSelf`）
- **`PrependPath=1` → 新 Python ディレクトリ（本体 + `Scripts\`）を PATH の先頭に追加** → インストール直後から新規ターミナルの `python` が新バージョンに切り替わる
- 既存バージョンとの共存（別ディレクトリ・別 ProductCode）。`UpgradeBehavior: install`
- `py` ランチャー: `py -3` は常に最新インストール版（導入後 3.15）を指す
- pip パッケージは**引き継がれない**: 新バージョン環境では `scripts/requirements.txt` + パイプライン依存（`google-genai` / `gradio_client` / `Pillow` + `pillow-avif-plugin`）の再インストールが必須。完了までパイプラインは壊れる
- リブート不要。既存ターミナルは旧 PATH のまま → 新ターミナルで確認
- 巻き戻し: 3.10.8 はそのまま残るため、新バージョンのアンインストール（`winget uninstall --id Python.Python.3.XX` / 設定→アプリ）で元に戻る

### インストールコマンド（例）

- winget（3.14.7）: `winget install --id Python.Python.3.14 --silent --accept-package-agreements --accept-source-agreements`
- 公式インストーラ直接（3.15.0）: `python-3.15.0-amd64.exe` をダウンロード後 `python-3.15.0-amd64.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0`

## 導入実施（2026-10-14 実施済み）

### 導入（ユーザー承認済み）

- 承認内容: per-user / `PrependPath=1`（新Python優先）/ 安全＝環境変数を破壊するな
- 導入前 PATH バックアップ: `C:\Users\fujim\AppData\Local\Temp\kilo\path_backup_user.txt`（409 chars）/ `path_backup_system.txt`（1551 chars）
- コマンド: `python-3.15.0-amd64.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1 Include_doc=0`
- 導入先: `C:\Users\fujim\AppData\Local\Programs\Python\Python315\`（per-user・UAC 不要）

### 導入後安全検証（全パス）

- SYSTEM PATH: バイト同一（1551 chars, match=True）
- USER PATH: 旧エントリ全保存（欠落 NONE）、先頭に `Python315\Scripts\` 追加（`PrependPath=1` 効果）
- 新ターミナル `python --version` → 3.15.0 確認

### 依存導入

- コア依存導入完了（3.15）: `pytest 9.1.1` / `google-genai 2.30.1` / `gradio_client 2.7.2` / `Pillow 12.3.0` / `python-dotenv 1.2.4` / `pyyaml 6.0.3` / `requests 2.34.2`
- **`pillow-avif-plugin` 導入失敗（cp315 wheel 不在）**: PyPI 全バージョンで cp315 wheel 不存在（最新 1.6.0 は cp310〜cp314/cp39 のみ、3.10.8 は cp310 wheel）。ソースビルドは libavif 必須 → 3.15 では導入不能

### 3.15 上での破綻確認

- `scripts/article/image.py:17` `import pillow_avif` → `ModuleNotFoundError: No module named 'pillow_avif'`
- `generate_article`（同 file import）→ テスト収集不能

### ユーザー判断（2026-10-14）

- 「今は 3.10.8 を python に戻し、wheel 待ち」

### 復元（実施済み）

- USER PATH を導入前バックアップから復元 → バイト一致（409 chars, match=True）
- SYSTEM PATH 不変（1551 chars, match=True）
- 新ターミナル `python --version` → 3.10.8（`Python310\python.exe`）確認
- 3.15 本体は `Python315\` に残置（待機。`py -3.15` で利用可）

### 3.10.8 でのテスト検証

- `py -3.10 -m pytest scripts/tests -v` → **397 tests PASS（7.60s）**

### wheel 公開後の次回アクション

1. `python` を 3.15 に再切替（PATH 先頭に `Python315\` + `Python315\Scripts\` を付与）
2. `py -3.15 -m pip install pillow-avif-plugin`（cp315 wheel 公開後）
3. `py -3.15 -m pytest scripts/tests -v` 全テスト確認
4. PEP 686 有効化確認（`PYTHONUTF8=1` / `-X utf8` 回避策の簡素化）
5. 任意: CI `python-version` 引き上げ、README バージョン更新

## Verification

- `winget update` + `winget search --id Python.Python.3.15` → 該当なし
- `winget search --id Python.Python.3` → 3.10.11 / 3.11.9 / 3.12.10 / 3.13.15 / 3.14.7（最新 3.14.7）
- `curl.exe -sI https://www.python.org/ftp/python/3.15.0/python-3.15.0-amd64.exe` → HTTP 200 OK（Content-Length 45,383,680、last-modified 2026-10-09）
- winget-pkgs マニフェスト（3.14.7）を取得し `InstallAllUsers=0 PrependPath=1` / `--quiet` を確認
- `python --version` / `where.exe python` / `py --list` / ディレクトリ一覧でローカル実態を確認

## 導入時の推奨手順（実施済み。詳細は上の「導入実施」を参照）

1. 3.15.0 インストーラ導入（`PrependPath=1`）→ 新ターミナルで `python --version` = 3.15.0 を確認
2. `py -3.15 -m pip install -r scripts/requirements.txt` + パイプライン依存のインストール（cp315 wheel 検証: `Pillow` / `pillow-avif-plugin`）
3. `pytest scripts/tests/ -v` 全テスト通過
4. 問題時は新バージョンをアンインストールして 3.10.8 に復旧（PATH は自動で元に戻る）
   - 安全策の代替: 先に `PrependPath=0` で導入し `py -3.15` で検証してから PATH 先頭へ切り替える

## Memory Bank 操作（2026-10-14）

- [x] `current-task.tsv`: 待機タスクとして参照行追加 → バックログへ移行したため参照行を削除
- [x] 導入実施時の結果（バージョン・依存・pytest）を本ファイルに追記し Status を更新
- [x] `backlog.md` P3 #11 へ登録（バックログ移行）
- [ ] cp315 wheel 公開後: `python` 再切替 → `pillow-avif-plugin` 導入 → pytest 全テスト確認 → PEP 686 有効化 → 完了時に `backlog.md` P3 #11 を削除
