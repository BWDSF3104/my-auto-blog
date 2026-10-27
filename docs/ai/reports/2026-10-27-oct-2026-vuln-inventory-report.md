# 2026年10月脆弱性対応 環境棚卸し報告（読み取り専用）

- 実施日時: 2026-10-27（現地時間）
- 対象: ローカルPC（読み取り専用のみ。更新・インストール・設定変更・再起動・ファイル削除・PoC実行・外部へのスキャン/送信は行っていません）
- 秘密情報: 値は出力していません。存在のみ報告（ユーザー名は `<user>` に伏字）
-  tasks file: `docs/ai/tasks/2026-10-28-oct-2026-vuln-inventory.md`

## 要約（3行）

1. **目安到達**: Node.js 24.22.1、PowerShell 7.6.9、.NET 8.0.33 / 9.0.22 / 10.0.14、VS2026 18.11.2、VS2022 Community 17.14.43、VS2019 16.11.61、Chrome 156.0.8078.48、Edge 156.0.4314.42、Defender定義（1.461.226.0 / 2026-10-27 15:49:53）、cFosSpeed 12.01（数値のみ）
2. **目安未達**: Firefox 127.0（158未満）、WSL内 libbrotli1 1.0.9-2build6（修正版 1.0.9-2ubuntu0.1 未適用）、Miniconda brotlipy 0.7.0、Windows Update自動更新が無効（10月KBは10/15・10/27分のみ）、curl 8.13.0（brotli機能なし）、EOL系列（.NET 2.1/3.1/5.0、Java 8/16、Python 3.7、Windows PowerShell 5.1）
3. **不明**: PHP（未インストール・比較不能）、Docker/Podman（未インストール）、Nextcloud・GitLab・Metabase・WordPress（検出できず）、OneDrive（バージョン取得できず）、KB番号とCVEの対応関係、cFosSpeed 11.02.1700 の修正版 claims（ベンダー公告未照合）

---

## 1. OSとWindows Update

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| Windows エディション | 有 | Windows 10 Home | `Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion` | 目安なし |
| バージョン / ビルド | 有 | DisplayVersion `22H2` / CurrentBuild `19045` / UBR `7807` / ReleaseId `2009` | 同上（`BuildNumber` プロパティは不存在） | 目安なし |
| 直近15件の更新（新しい順） | 有 | KB5127689(2026-10-27 Update), KB5126657(2026-10-27 Security Update), KB5127308(2026-10-15 Security Update), KB5122877(2026-09-11), KB5104021(2026-07-17), KB5094145(2026-06-12), KB5084130(2026-04-18), KB5072653(2025-12-22), KB5071982(2025-11-13), KB5066790(2025-10-17), KB5063979(2025-10-15), KB5063261(2025-08-15), KB5063706(2025-07-11), KB5059504(2025-06-13), KB5058526(2025-05-15) | `Get-HotFix` | 10月分は3件適用済み |
| 2026年10月の累積更新 | 有（KBのみ） | KB5127308 / KB5126657 / KB5127689 | `Get-HotFix` | KB→CVEマッピングはローカル数据から**不明** |
| Windows Defender | 有 | AMEngine `1.1.26090.9` / AMProduct `4.18.26090.9`（AMService `4.18.26090.9`） | `Get-MpComputerStatus` | — |
| 定義の最新度 | 最新 | `1.461.226.0`（Antivirus/Antispyware/NIS 共通）更新 `2026-10-27 15:49:53`（Age 0）, `DefenderSignaturesOutOfDate=False` | `Get-MpComputerStatus` | **達している** |
| スキャン状態 | — | QuickScan 最終 `2026-10-08 02:34:26`（`QuickScanOverdue=True`）, FullScan 最終 `2023-02-13`（Age 1352） | `Get-MpComputerStatus` | 不明（未実行） |
| 自動更新 | 無効 | `NoAutoUpdate=1`, `AUOptions=2`（検知・通知） | `Get-ItemProperty HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU` | **達していない**（自動適用されない） |

## 2. Microsoft Office / Outlook

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| Office（M365 Apps / LTSC / Click-to-Run） | なし | Click-to-Run 設定キーなし | `Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration` | 目安なし |
| Office 互換コンポーネント | 有 | Microsoft Visual Studio 2010 Tools for Office Runtime (x64) `10.0.60915` / Open XML SDK 2.5 for Microsoft Office `2.5.5631` | uninstall レジストリ | — |
| Outlook（classic） | なし | プロファイルフォルダなし | `Test-Path C:\Users\<user>\AppData\Local\Microsoft\Outlook` = False | — |
| Outlook（new / Outlook for Windows） | 有 | `1.2026.818.0`（appx: `Microsoft.OutlookForWindows_8wekyb3d8bbwe`） | `winget list` / `AppData\Local\Packages`（`Get-AppxPackage` は環境エラーで実行不可） | 目安なし |
| OneNote（UWP） | 有 | `16001.14326.22594.0` | `winget list` | — |

## 3. ブラウザ

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| Google Chrome | 有 | `156.0.8078.48` | exe VersionInfo（`C:\Program Files\Google\Chrome\Application\chrome.exe`）/ `winget list` | **達している**（155.0.8059.79/.80 以降） |
| Microsoft Edge | 有 | `156.0.4314.42` | exe VersionInfo / `winget list` | 目安なし（Chrome同系統で十分） |
| Edge WebView2 Runtime | 有 | `155.0.4283.62` | `winget list` | 判定不能 |
| Firefox | 有 | `127.0` | exe VersionInfo（`C:\Program Files\Mozilla Firefox\firefox.exe`）/ `winget list` | **達していない**（158 未満） |
| Mozilla Maintenance Service | 有 | `104.0.2` | `winget list` | — |
| その他ブラウザ | なし | NoxPlayer `7.0.1.9`（Androidエミュレータ） | `winget list` | — |

## 4. .NET / PowerShell / Visual Studio

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| .NET ランタイム | 有 | AspNetCore.App: `2.1.30`, `3.1.25`, `3.1.32`, `5.0.4`, `5.0.9`, `5.0.17`, **`8.0.33`**, **`9.0.22`**, **`10.0.14`** / NETCore.App: 同 / WindowsDesktop.App: `3.1.25`, `3.1.32`, `5.0.4`, `5.0.9`, `5.0.17`, `8.0.33`, `9.0.22`, `10.0.14` | `dotnet --list-runtimes` | 8/9/10は**達している**、2.1・3.1・5.0はEOL（修正なし） |
| .NET SDK | 有 | `5.0.104`, `5.0.303`, `5.0.416`, `8.0.427`, `9.0.320`, `10.0.403` | `dotnet --list-sdks` | 5.x は EOL |
| .NET Framework | 有 | `4.8`（Version `4.8.09221`, Release `533509`） | `HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full` | 該当KBは**不明** |
| Windows PowerShell | 有 | `5.1`（PowerShellVersion `5.1.19041.1`） | `HKLM:\SOFTWARE\Microsoft\PowerShell\3\PowerShellEngine` | 7系の目安（7.6.9/7.5.13/7.4.22）は適用外 |
| PowerShell 7 | 有 | `7.6.9` | `$PSVersionTable.PSVersion`（実行環境）/ `winget list` `7.6.9.0` | **達している** |
| Visual Studio 2026 | 有 | Community `18.11.2` | `winget list` / uninstall レジストリ | **達している** |
| Visual Studio 2022 | 有 | Community (2) `17.14.43` / Build Tools `17.14.42` | `winget list` | Community **達している**、Build Tools `17.14.42` は**達していない** |
| Visual Studio 2019 | 有 | Community `16.11.61` | `winget list` | **達している** |
| 自作 .NET（self-contained） | なし | `*.runtimeconfig.json`（selfContained 該当 0件） | `C:\Users\<user>\source\repos` 配下 grep | — |
| 自作 .NET ツール（.NET Framework 製） | 有 | 約40プロジェクト（TargetFrameworkVersion `v2.0`〜`v4.7.2`） | `*.csproj` / `*.sln`（例: `AnyFileDelete`(v4.7.2), `CaptureTool`(v4.7), `CheckTwinFiles`(v4.7.2), `ExifCopyTool`(v4.7.2), `FileAssorter`(v4.7), `ImageResizerGUI`, `MinecraftResourceManager`(v4.5), `PingTester`, `ProcessScaner`(v4.5.2), `SampleThumbnailView`(v4.6.1), `SendServerInformation`(v4.5), `UPnPSample`(v2.0), `VideoThumbnailMaker`(v4.7.2), `waifu2x-ncnn-vulkan-GUI-1.0.6`(v4.5.2), `DGMLAnalizer`, `ExplorerHistory`(v4.5.2), `BatchStarter`, `SerialNumberFilesAssorter` ほか） | 実行時 4.8 依存 → 該当KBは**不明** |
| ビルド時期（bin の LastWriteTime） | 有 | 最新 `2026-05-02 03:44:29`（PingTester.exe）, `2026-04-30 20:18:01`, `2026-04-11 22:37:19`（psping.exe）, `2022-06-25`（SendServerInformation.exe）, `2022-01-06`（CaptureTool.exe） | `Get-ChildItem ... -Filter *.exe | Sort LastWriteTime` | — |

## 5. PHP（確認）

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| PHP（Windows） | なし（未インストール／コマンドなし） | — | `php -v` = コマンドなし、`where.exe php` = 該当なし | 比較不能（8.5.12/8.4.27/8.3.36/8.2.35 目安は該当なし） |
| php.exe（ディスク検索） | なし | — | `C:\`, `C:\Program Files`, `C:\Program Files (x86)`, `S:\` を深度3検索（0件） | — |
| PHP拡張 `brotli` / `curl` | なし | — | `php -m` 実行不可 | — |
| -1 ビルド（Brotli対応） | 該当なし | — | — | — |
| Webサーバー（Apache/IIS/nginx） | なし（未起動） | httpd.exe・nginx.exe 0件、IIS `WebManagement`=Stopped | `Get-Service` / ファイル検索 | — |
| IIS Express | 有（インストールのみ） | `10.0.08608` / ASP.NET Core Module for IIS Express `12.2.18292.0` | `winget list` | — |
| 04WebServer | 有（未起動） | `1.92.0`（Soft3304） | `winget list` | PHP連携なし |
| PHP接続方式（mod_php / PHP-FPM / FastCGI） | なし | — | — | — |

## 6. Brotli CVE-2026-111497 の内部コピー

上游確認済みの事実: Brotli C実装のデコーダ `c/dec/decode.c` の境界外書き込み、影響 **1.0.3〜1.2.0**、修正版 **1.0.10 / 1.1.1 / 1.2.1**（CVE.org・JPCERT-AT-2026-0034）。Node.js は **v24.22.1** で cherry-pick 修正（Red Hat bug 2558973）。PHP Windows ビルド `8.5.12-1 / 8.4.27-1 / 8.3.36-1 / 8.2.35-1` に Brotli 1.2.1 同梱（php.net archive 2026）。

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| Node.js | 有 | `v24.22.1` | `node -v` | **達している**（24.22.1） |
| npm / npx | 有 | `11.19.1` / `11.19.1` | `npm --version`, `npx --version` | — |
| Node 20系（EOL） | なし | — | `node -v` | 修正なし系列の該当なし |
| Bun | なし（コマンドなし） | — | `bun --version` | — |
| Deno | なし（コマンドなし） | — | `deno --version` | — |
| Python（既定） | 有 | `3.10.8` / pip `22.2.2` | `python --version`, `pip --version` | — |
| Python（py --list） | 有 | `3.13*`, `3.12`, `3.11`, `3.10`, `3.7`, `ContinuumAnalytics/Anaconda39-64` | `py --list` | 3.7系 EOL |
| Python 3.13 パッケージ | — | `pip 26.1.2` のみ | `py -3.13 -m pip list` | — |
| brotli / brotlicffi（3.10） | なし | — | `pip list` | — |
| urllib3 / requests / httpx（3.10） | 有 | urllib3 `2.8.0`, requests `2.34.2`, httpx `0.28.1`（httpcore `1.0.9`）, aiohttp なし, Scrapy なし | `pip list` | Brotli依存なし |
| Miniconda3 (py39) | 有 | **brotli（brotlipy `0.7.0`）**, requests `2.27.1`, urllib3 `1.26.9`, cffi `1.15.0` | `C:\Users\<user>\Miniconda3\Lib\site-packages` | **達していない**（1.2.1 / 1.2.1.0 未満） |
| Miniconda3 (py310) | 有 | `py310_24.5.0-0`（Python 3.10.14） | `winget list` | brotli 導入確認できず |
| Anaconda3 | 有 | `2023.07-2`（Python 3.11.4） | `winget list` | 未確認 |
| Ruby / brotli gem | なし（コマンドなし） | — | `ruby -v` | — |
| Go | なし（コマンドなし） | — | `go version` | — |
| Java | 有 | JDK `16.0.2`（build 16.0.2+7-67）, JRE `8 Update 301` (`8.0.3010.9`) | `java -version` / `winget list` | EOL系列 |
| Rust (rustc/cargo) | なし（コマンドなし） | — | `rustc --version` | — |
| curl（Windows） | 有 | `curl 8.13.0` / libcurl `8.13.0`（Schannel, zlib 1.3.1, WinIDN, Release-Date 2025-04-02）— **Features に brotli なし** | `curl --version` | Brotli組み込みなし |
| WSL `libbrotli1` | 有 | **`1.0.9-2build6`** | `wsl dpkg -l` | **達していない**（修正版 `1.0.9-2ubuntu0.1` / USN-8956-1 未適用） |
| WSL `curl` | 有 | `7.81.0`（brotli/1.0.9, zstd/1.4.8, nghttp2/1.43.0） | `wsl curl --version` | **達していない** |
| 7-Zip | 有 | `19.00`（winget 表示: 可用 `26.05`） | exe VersionInfo / `winget list` | 比較目安なし |
| NanaZip | なし | — | `winget list` | — |

## 7. パッケージマネージャー / 開発ツール / WSL

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| winget | 有 | `1.29.380`（App Installer `1.29.380.0`） | `winget --version` | — |
| Chocolatey | なし（コマンドなし） | — | `choco --version` | — |
| Scoop | なし（コマンドなし） | — | `scoop --version` | — |
| Git | 有 | `2.53.0.windows.3`（Git LFS `3.4.1`, 可用 `3.8.0`） | `git --version` | — |
| Git Credential Manager | 有 | `2.7.3+5fa7116896c82164996a609accd1c5ad90fe730a`（helper=`manager`） | `git credential-manager --version` | — |
| GitHub CLI | 有 | `2.102.0`（2026-09-30, 可用 `2.103.3`） | `gh --version` | — |
| GitLab CLI (glab) | なし（コマンドなし） | — | `glab --version` | — |
| VS Code | 有 | `1.143.1`（commit `e646868227c3e3a9e3f24277c8c7220be42c0be7`, x64） | `code --version` | — |
| VS Code 拡張 | 有 | astro-vscode `2.16.20`, google-antigravity `1.4.0`, kilo-code `7.8.18`, language-pack-ja `1.131.2026090407`, debugpy `2026.6.0`, isort `2026.6.0`, python `2026.10.0`, pylance `2026.4.1`, python-envs `1.40.0`, jupyter `2025.9.1`, jupyter-keymap `1.1.2`, jupyter-renderers `1.3.0`, jupyter-cell-tags `0.1.9`, jupyter-slideshow `0.1.6`, remote-wsl `1.104.6`, remote-explorer `0.5.0`, remote-server `1.5.4`, uwsc-support `0.0.3`, debugmcpextension `2.4.4`, refstack `0.0.0` | `code --list-extensions --show-versions` | — |
| Docker Desktop / Engine | なし（コマンドなし） | — | `docker --version` | — |
| Podman | なし（コマンドなし） | — | `podman --version` | — |
| WSL | 有 | WSL `3.0.3.0` / kernel `6.18.54.1-1` / wslg `1.0.79` / MSRDC `1.2.7391` / Direct3D `1.611.1-81528511` / DXCore `10.0.26100.1-240331-1435.ge-release` | `wsl --version` | — |
| WSL ディストリ | 有 | `Ubuntu`（Stopped, Version 2, 既定） | `wsl -l -v` | — |
| WSL内 `/etc/os-release` | 有 | `Ubuntu 22.04.2 LTS (jammy)`（`VERSION_ID=22.04`） | `wsl cat /etc/os-release` | — |
| WSL内 php / node / dotnet | なし | `command not found` | `wsl php -v`, `wsl node -v` | — |
| WSL内 python3 | 有 | `3.10.6`（`python3-pip` `22.0.2+dfsg-1ubuntu0.2`） | `wsl python3 --version` / `wsl dpkg -l` | — |
| WSL内 curl | 有 | `7.81.0`（`libcurl4` `7.81.0-1ubuntu1.10`） | `wsl curl --version` | **達していない** |

## 8. コンテナとプロジェクト

| 項目名 | 有無 | 内容（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| `docker images` | 実行不可 | Docker 未インストール | `docker --version` | — |
| `docker ps -a` | 実行不可 | 同上 | `docker --version` | — |
| ワークスペース `S:\Documents\AutoBlog\my-auto-blog` | 有 | `package.json`（Astro `7.3.5`, tailwindcss `4.3.3`, @tailwindcss/vite `4.3.3`; devDep @tailwindcss/typography `0.5.20`, js-yaml `5.4.2`; engines node `>=22.12.0`）, `package-lock.json`, `scripts/requirements.txt`（python-dotenv, pyyaml, requests, google-auth, pytest）, `hf-space/requirements.txt`（torch, torchvision, diffusers, transformers, accelerate, safetensors, spaces, huggingface_hub, omegaconf） | `Read` / glob | Brotli 依存なし（node_modules にも brotli 系 0件） |
| `.env` | **存在**（内容未読） | `S:\Documents\AutoBlog\my-auto-blog\.env` | 名前のみ | — |
| `.env`（ユーザー領域） | 存在（内容未読） | `C:\Users\<user>\.vscode\extensions\ms-python.python-2021.10.1365161279\pythonFiles\.env`, `...ms-toolsai.jupyter-2021.8.1236758218\pythonFiles\.env`, `...ms-toolsai.jupyter-2024.3.1-win32-x64\pythonFiles\.env`（拡張由来） | 名前のみ | — |
| ローカルリポジトリ（使用技術） | 有 | Java/Maven: `C:\Users\<user>\git\example-projects\maven-simple-bot\pom.xml`, `maven-spring-bot\pom.xml`；Node.js: `C:\Users\<user>\.config\kilo\package.json`, `C:\Users\<user>\source\repos\NodejsConsoleApp1\...`；C#/.NET Framework: `C:\Users\<user>\source\repos\` 約40（.csproj/.sln）；C++: `Desktop\FO3AutoJapanize\fose\fose.sln`；Python: `pyproject.toml`（pylance/jupyter 由来）；Dockerfile: `C:\Users\<user>\source\repos\ftl-sdk-master\Dockerfile` | glob（名前のみ） | Brotli 依存名なし |

## 9. 自宅／セルフホスト系ソフト

| 項目名 | 有無 | バージョン（正確に） | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| Nextcloud（サーバー） | なし | — | `winget list`, `Get-Process`, `Get-Service` | — |
| Nextcloud（デスクトップクライアント） | なし | — | 同上 | — |
| GitLab（自己管理型） | なし | — | 同上 | — |
| GitLab Runner | なし | — | 同上 | — |
| Metabase | なし | — | 同上 | — |
| WordPress ローカル環境（XAMPP / Local / DevKinsta / Docker） | なし | — | `Test-Path C:\xampp` = False, `Test-Path C:\laragon` = False, `winget list` | — |
| VPNクライアント | 有 | **Radmin VPN `2.0.9`**（ビルド `2.0.4899.9`, 可用 `2.1.4951.1`） | `winget list` | 製品名とバージョンのみ |
| NAS/ルーター管理・ネットワーク常駐 | 有 | **cFosSpeed `12.01`**（ドライバ常駐 `cFosSpeedS` Running, `C:\Program Files (x86)\cFosSpeed`）, MSI Dragon Center `2.0.133.0`, Process Lasso `17.0.2.20`, Intel(R) Extreme Tuning Utility `7.14.2.14`, SQL Writer `sqlwriter` Running | `Get-Service` / `Get-Process` / `winget list` | cFosSpeed: 実測 `12.01`。**「11.02.1700 で修正済み」という主張はベンダー公告を未照合のため不明**（12.01 ≥ 11.02.1700 なら達している） |
| UPnP / SSDP / LLT | 部分 | `upnphost`=Stopped, `SSDPSRV`=Running, `lltdsvc`=Stopped, `SharedAccess`=Running, `IKEEXT`=Running | `Get-Service` | — |

## 10. 常駐・ネットワーク

| 項目名 | 有無 | 状態 / バージョン | 確認方法 | 目安との比較 |
|---|---|---|---|---|
| リモートデスクトップ（待ち受け） | 無効 | `TermService` = Running だが `fDenyTSConnections=1`（接続不可）, `UmRdpService`=Running；クライアント: Microsoft リモート デスクトップ `10.2.4012.0` | レジストリ `Terminal Server` / `Get-Service` | — |
| SSHサーバー | なし（停止） | `sshd`=Stopped（OpenSSH サービスが存在）, `ssh-agent`=Stopped, `SshdBroker`=Stopped | `Get-Service` | — |
| WinRM | なし（停止） | `WinRM`=Stopped | `Get-Service` | — |
| RemoteRegistry | なし（停止） | `RemoteRegistry`=Stopped | `Get-Service` | — |
| ファイル共有（SMB） | 待ち受け | `LanmanServer`=Running（`LanmanWorkstation`=Running） | `Get-Service` | — |
| Chrome Remote Desktop Host | 有（常駐） | `154.0.8037.40`（`chromoting` Running） | `Get-Service` / `winget list` | — |
| WSL 関連常駐 | 有 | `WSLService`=Running, `vmcompute`=Running, `wslrelay`/`vmmem` プロセス稼働 | `Get-Service` / `Get-Process` | — |
| 印刷スプール | 待ち受け | `Spooler`=Running | `Get-Service` | — |
| ネットワークDiscovery系 | 有 | `FDResPub`=Running, `NlaSvc`=Running, `Dnscache`=Running | `Get-Service` | — |
| クラウド同期 | 有（稼働） | **Google Drive `133.0.2.0`**（`GoogleDriveFS` プロセス稼働, `I:` VDF）, Backup and Sync from Google `3.57.4256.0809` | `Get-Process` / `winget list` | — |
| OneDrive | 不明 | `C:\Users\<user>\AppData\Local\Microsoft\OneDrive` 存在（exe/バージョン取得できず, プロセス未起動） | `Test-Path` / レジストリ（読み取り） | — |
| Dropbox | なし | — | `winget list` | — |
| その他常駐（開発/運用関連） | 有 | `TGitCache`（TortoiseGit `2.18.0.1`）, `code-tunnel`, `node`, `python`, `pwsh`, `kilo`, `remoting_host`, `spd`（cFosSpeed）, `RvControlSvc`, `Backupper Service`（AOMEI `8.0.0`）, `LightKeeperService`, `Mystic_Light_Service`, `MSI_Central_Service`, `RstMwService`, `LogiRegistryService`, `nvagent` | `Get-Process` / `Get-Service` | — |

## 11. 付録：インストール済みアプリ一覧（`winget list`）

ライセンスキー・シリアル番号・アカウント名は含めていません。Steam/VR アプリ（バージョン `Unknown`）は末尾に名前のみ集約。

### ランタイム / 開発

| 名前 | バージョン |
|---|---|
| Node.js | 24.22.1 |
| Python 3.10.8 (64-bit) | 3.10.8 |
| Python 3.11.9 (64-bit) | 3.11.9 |
| Python 3.12.2 (64-bit) | 3.12.2 |
| Python 3.13.14 (64-bit) | 3.13.14 |
| Python 3.7.8 (64-bit) | 3.7.8 |
| Python Launcher | 3.15.150.0 |
| Python Install Manager | 26.2.240.0 |
| Miniconda3 py310_24.5.0-0 | py310_24.5.0-0 |
| Miniconda3 py39_4.12.0 | py39_4.12.0 |
| Anaconda3 2023.07-2 | 2023.07-2 |
| uv | 0.13.1 |
| Java 8 Update 301（x86・x64） | 8.0.3010.9 |
| Java(TM) SE Development Kit 16.0.2 (64-bit) | 16.0.2.0 |
| Java Auto Updater | 2.8.301.9 |
| PowerShell 7-x64 | 7.6.9.0 |
| Git LFS version 3.4.1 | 3.4.1 |
| GitHub CLI | 2.102.0 |
| RipGrep MSVC | 15.2.0 |
| winget（アプリ インストーラー） | 1.29.380 |
| .NET SDK (x64) | 5.0.104 / 5.0.303 / 5.0.416 / 8.0.427 / 9.0.320 / 10.0.403 |
| .NET Runtime / Desktop Runtime / ASP.NET Core Runtime (x86・x64) | 8.0.33 / 9.0.22 / 10.0.14（ほか 2.1.30, 3.1.32, 5.0.4, 5.0.9, 5.0.17） |
| .NET Targeting Pack / AppHost Pack | 8.0.33 / 9.0.22 / 10.0.14 / 5.0.0 / 3.1.32 |
| .NET Native Framework / Runtime Package | 1.7.27413.0 / 2.2.29512.0 / 2.2.28604.0 / 1.7.27422.0 |
| TypeScript SDK | 4.3.5.0 |
| Entity Framework Tools (VS2022 / VS2019) | 6.5.0.0 / 6.2.0.0 |
| Microsoft Visual Studio Code (User) | 1.143.1 |
| Visual Studio Community 2026 | 18.11.2 |
| Visual Studio Community 2022 (2) | 17.14.43 |
| Visual Studio Community 2019 | 16.11.61 |
| Visual Studio Build Tools 2022 | 17.14.42 |
| Microsoft Visual Studio Installer | 4.11.24.2075 |
| Microsoft Web Deploy 4.0 | 10.0.8215 |
| IIS 10.0 Express | 10.0.08608 |
| ASP.NET Core Module for IIS Express | 12.2.18292.0 |
| Microsoft Visual Studio 2010 Tools for Office Runtime (x64) | 10.0.60910 / 10.0.60915 |
| Open XML SDK 2.5 for Microsoft Office | 2.5.5631 |
| Microsoft SQL Server 2016 LocalDB | 13.1.4001.0 |
| Microsoft ODBC Driver 17 for SQL Server | 17.10.6.1 |
| Microsoft System CLR Types (SQL Server 2019) | 15.0.1200.24 / 15.0.2000.5 |
| Active Directory Authentication Library for SQL Server | 15.0.1300.359 |
| .NET Framework SDK / Targeting Pack | 4.8.03928 / 4.8.03761 / 4.7.2 / 4.7.1 / 4.7 / 4.6.2 / 4.6.1 / 4.6 / 4.5.x / 4.0（Intellisense Pack 4.8.09037） |
| Windows SDK | 10.1.19041.5609 / 10.1.16299.15 / 10.1.0.0 |
| Microsoft Visual C++ Redistributable | 2005 8.0.61001 / 2008 9.0.30729.17・9.0.30729.6161・9.0.30729.4148・9.0.21022 / 2010 10.0.40219 / 2012 11.0.61030 / 2013 12.0.30501・12.0.40649 / 2015+ 14.51.36247（UWP Runtime 14.0.30035〜14.0.33728） |
| TortoiseGit 2.18.0.1 (64 bit) | 2.18.0.1 |

### ブラウザ / セキュリティ / 更新

| 名前 | バージョン |
|---|---|
| Google Chrome | 156.0.8078.48 |
| Microsoft Edge | 156.0.4314.42（MSIX 152.0.4191.53） |
| Microsoft Edge WebView2 Runtime | 155.0.4283.62 |
| Copilot | 156.0.4314.42 |
| Mozilla Firefox (x64 ja) | 127.0 |
| Mozilla Maintenance Service | 104.0.2 |
| cFosSpeed 12.01 | 12.01 |
| Radmin VPN 2.0.9 | 2.0.4899.9 |
| Chrome Remote Desktop Host | 154.0.8037.40 |
| Microsoft リモート デスクトップ | 10.2.4012.0 |
| Windows PC 正常性チェック | 4.0.2410.23001 / 3.6.2204.08001 |
| Microsoft Update Health Tools | 3.74.0.0 |
| Update for x64-based Windows Systems (KB5001716) | 8.94.0.0 |
| Update for (KB2504637) | 1 |
| Windows Subsystem for Linux Update | 5.10.102.1 |
| Linux 用 Windows サブシステム | 3.0.3.0 |
| Ubuntu (Canonical.Ubuntu) | 2604.1.75.0 |

### 開発・運用ツール

| 名前 | バージョン |
|---|---|
| 7-Zip 19.00 (x64) | 19.00 |
| WinMerge x64 | 2.16.54.4 |
| WizTree v4.32 | 4.32 |
| TechPowerUp GPU-Z | 2.65.1 |
| CPUID CPU-Z 2.15 | 2.15 |
| CrystalDiskMark 8.0.4c | 8.0.4c |
| Process Lasso | 17.0.2.20 |
| AOMEI Backupper | 8.0.0 |
| 04WebServer 1.92 | 1.92.0 |
| GIMP 2.10.32-1 | 2.10.32 |
| XnView 2.51.1 | 2.51.1 |
| IrfanView 4.70 (64-bit) | 4.70 |
| MKVToolNix 68.0.0 (64-bit) | 68.0.0 |
| HandBrake 1.6.1 | 1.6.1 |
| MPC-BE x64 1.6.3 | 1.6.3 |
| XMedia Recode 64bit | 3.5.4.3 |
| BandiView | 7.28 |
| PictBear Version 2.04 | 2.04（ver不定） |
| Equalizer APO | 1.2.1 |
| XTRM Runtime | 10.1 |
| FontInstall version 1.5 | 1.5 |
| Borderless Gaming | 9.6 |
| DVDFab (x64) | 12.0.7.4 / 12.1.0.3 / 13.0.5.4 |
| Vortex | 2.4.0 |
| Minion | 3.0 |
| DeepL | Unknown |
| Discord | 1.0.9258 |
| µTorrent | 3.5.5.45852 |
| DMMGamePlayer 5.2.22 | 5.2.22 |
| Wargaming.net Game Center | 24.8.2.8277 |
| ModStation WOWS | 2.2.0.0 |
| REDlauncher | Unknown |
| Riot Client | Unknown |
| Rockstar Games Launcher | 1.0.102.2459 |
| Rockstar Games SDK (Social Club) | 2.4.0.77 |
| EA app | 13.501.1.6009 |
| Epic Online Services | 2.0.38.0 |
| Pinokio 2.15.1 | 2.15.1 |
| Comfy Desktop 1.0.47 | 1.0.47 |
| NiceHash Miner 3.1.1.3 (only current user) | 3.1.1.3 |
| NiceHash QuickMiner | v0.5.3.3 |
| Owl3D | 2.3.0 |
| MSI Afterburner 4.6.7 Beta 2 | 4.6.7 Beta 2 |
| RivaTuner Statistics Server 7.3.7 | 7.3.7 |
| Intel(R) Extreme Tuning Utility | 7.14.2.14 |
| Intel(R) Management Engine Components | 11.7.0.1037 |
| MSI SDK | 2.2023.0518.01 |
| DragonCenter | 2.0.133.0 |
| Logicool ゲームソフトウェア 9.02 | 9.02.65 |
| Razer Synapse | 3.5.1215.121019 |
| HyperX Orbit | 0.0.1 |
| WD_BLACK AN1500 / D50 / ENE 各種 | 1.0.12.0 / 1.0.9.0 / 1.0.5.1, 1.0.9.10, 1.0.2.0, 1.0.3.31 |
| NoxPlayer | 7.0.1.9 |
| PiService version 2.0 | 2.0 |
| PiTool | 1.0.1.275 |
| GnuWin32: Wget-1.11.4-1 | 1.11.4-1 |
| K-Lite Mega Codec Pack 18.3.0 | 18.3.0 |
| DirectX | 9.29.1974.0 |
| OpenAL | Unknown |
| OpenVR Advanced Settings | Unknown |
| ViGEm Bus Driver | 1.16.115 |
| PlayStation® Accessories | 2.2.0.3 |
| PlayStation® PC SDK Runtime | 5.50.0011 |
| NVIDIA App | 11.0.9.251 |
| NVIDIA グラフィックス ドライバー | 596.49 |
| NVIDIA Control Panel | 8.1.969.0 |
| NVIDIA PhysX システム ソフトウェア | 9.23.1019 |
| NVIDIA CUDA Toolkit | 12.6（ほか 9.0/10.2/11.3/11.8 コンポーネント） |
| NVIDIA Nsight Compute | 2024.3.2 |
| NVIDIA Nsight Systems | 2019.5.2 / 2021.1.3 / 2022.4.2 / 2024.5.1 |
| NVIDIA Nsight Visual Studio Edition | 2024.3.0.24164 |
| NVIDIA FrameView SDK | 1.9.12728.38614306 |
| NVIDIA HD オーディオ ドライバー | 1.4.5.7 |
| NVIDIA Virtual Audio | 4.92.0.0 |
| NVIDIA ShadowPlay | 11.0.9.500 |
| Unity | 2018.3.5f1 / 6000.2.12f1 |
| Unity Hub 3.15.2 | 3.15.2 |
| Meta Horizon Link | 1.115.0 |
| Virtual Desktop Service | 1.18.56 |
| DLSS 5 Swapper 2.2.1 | 2.2.1 |
| Game Bar | 7.326.10141.0 |
| GameInput | 4.0.302.0 |
| pvr_steamvr_driver / pvr runtime / PVR Home | 0.1 |

### UWP / MSIX（名前とバージョン）

3D ビューアー 7.2602.8012.0 / AV1 Video Extension 2.0.35.0 / Bing 1.1.40.0 / Cortana 4.2308.1005.0 / HEIF 1.2.48.0 / HEVC 2.4.149.0 / MPEG-2 1.2.32.0 / VP9 1.2.20.0 / Web メディア拡張 1.2.42.0 / Webp 1.2.31.0 / Microsoft Store 22609.1401.6.0 / Store エクスペリエンス 22608.1401.1.0 / ヒント 10.2312.1.0 / フォト 2026.11090.22001.0 / 電卓 11.2607.0.0 / クロック 11.2607.6.0 / マップ 11.2506.3.0 / 切り取り & スケッチ 10.2008.3001.0 / ペイント 3D 6.2410.13017.0 / Print 3D 3.3.791.0 / Windows カメラ 2026.2608.1.0 / ボイス レコーダー 10.2103.28.0 / OneNote for Windows 10 16001.14326.22594.0 / Skype 15150.3125.0 / People 10.2202.100.0 / 付箋 6.1.4.0 / 翻訳 5.6.0.0 / 問い合わせ 10.2409.41132.0 / フィードバック Hub 1.2608.17301.0 / 正常性チェック 4.0.2410.23001 / スマートフォン連携 1.25072.81.0 / クロス デバイス エクスペリエンス ホスト 0.25072.59.0 / Windows Advanced Settings (DevHome) 0.2100.858.0 / Mixed Reality ポータル 2000.21051.1282.0 / Xbox 2611.1001.8.0 / Xbox コンソール コンパニオン 48.104.4001.0 / Xbox TCUI 1.24.10001.0 / Xbox Identity Provider 12.130.16001.0 / Xbox Game Speech Window 1.21.13002.0 / Xbox Game Bar Plugin 1.54.4001.0 / Raven for Network 70.0.4.0 / Neat Office 3.4.15.0 / 日本語 ローカル エクスペリエンス パック 19041.80.275.0 / Microsoft Pay 2.4.18324.0 / Microsoft Engagement Framework 10.0.23012.0 / Windows Package Manager Source (winget) V2 2026.1027.1546.30 / WindowsAppRuntime 1.2.5 / 1.3.2〜1.3.3 / 1.4.7 / 1.5.3〜1.5.9 / 1.6.4〜1.6.8 / 1.7.5〜1.7.9 / 1.8.6〜1.8.10 / 2.3.1.0〜2.5.1.0 / Microsoft.UI.Xaml 2.0〜2.8（2.1810.18004.0 / 2.11906.6001.0 / 2.32002.13001.0 / 2.42007.9001.0 / 2.52012.2002.0 / 2.62112.3002.0 / 7.2207.21001.0 / 7.2208.15002.0 / 7.2409.9001.0 / 8.2310.30001.0 / 8.2501.31001.0） / Microsoft .Net Native Framework 1.7.27413.0・2.2.29512.0 / Runtime 1.7.27422.0・2.2.28604.0

### Google ドキュメント系（PWA, バージョン 1.0）

Gmail 1.0 / スライド 1.0 / ドキュメント 1.0 / スプレッドシート 1.0 / YouTube 1.0 / Google ドライブ 1.0

### Steam / VR アプリ（すべて `Unknown`）

Aeon's End, AI創作呪文, Amber Isle, Angels with Scaly Wings, Anthro Heat, ARMORED CORE VI FIRES OF RUBICON, ATLYSS, Beat Saber, Besiege, BLEACH Rebirth of Souls, Cyberpunk 2077 Bonus Content, Deus Ex: Human Revolution - Director's Cut, Dinoblade, Dominion, Drag'n Wash, Dragon Sleuth Brittany, Eleven Table Tennis, FarmD, Forza Horizon 6, Grand Theft Auto III - The Definitive Edition, Gun Club VR, Half Minute Hero: Super Mega Neo Climax Ultimate Boy, HEART of CROWN Online, Hunt and Snare, IN HEAT: Lustful Nights, Kaichu - A Kaiju Dating Sim, Knights College -ナイツカレッジ-, Lobotomy Corporation, Lossless Scaling, METAL GEAR SOLID 2 SONS OF LIBERTY (MASTER COLLECTION版), METAL GEAR SOLID 4 GUNS OF THE PATRIOTS (MASTER COLLECTION版), METAL GEAR SOLID MASTER COLLECTION Vol.2 BONUS CONTENT, Mutant Alley: Dinohazard, Mystic Vale, Nekojishi, Oh So Hero!, Percona(略: ペルソナ4 ザ・ゴールデン), Rock of Ages 2, SILENT HILL f - Digital Soundtrack, Slay the Spire 2, STARFIELD OFFICIAL SOUNDTRACK, SteamVR, Them's Fightin' Herds, UNDER NIGHT IN-BIRTH II Sys:Celes, Virtual Desktop, VRChat, Yu-Gi-Oh! Master Duel, ことばのパズル もじぴったんアンコール, でびるコネクショん, みんなで推理, ストレンジシード Strange Seed, 晶霊スクワッド Shard Squad, 漢字でGO! 集英社マンガ祭, 餓狼伝説 City of the Wolves, 首都高バトル, 黄泉に落ちても麻雀, 龍が如く8, ファイナルファンタジーVII インターナショナル for PC (2.0.0), The Sims 4 (Unknown), 2XKO (Unknown), Cyberpunk 2077 Bonus Content

### その他の検出（ドライバ/メーケティングソフト）

Realtek High Definition Audio Driver 6.0.8746.1 / CyberLink Media Suite 10 (10.0) / CyberLink PowerDVD 12 (12.0.5522.55) / ENE X-JMI HAL 1.0.5.1 / ENE EHD_M2_HAL 1.0.9.10 / ENE MousePad HAL 1.0.2.0 / ENE DRAM_RGB_AIO 1.0.3.31 / Update for x64-based Windows Systems (KB5001716) 8.94.0.0 / Windows SDK AddOn 10.1.0.0 / Windows ドライバ パッケージ - GigaDevice (GDDFUDriver) USB 09/03/2019 7.54.5.81 / SQL Server 2019 CTP2.2 用 Microsoft System CLR Types 15.0.1200.24

---

## 参考（上流情報・確認済み）

- CVE-2026-111497: Brotli C 実装 `c/dec/decode.c` の境界外書き込み、影響 1.0.3〜1.2.0、修正版 1.0.10 / 1.1.1 / 1.2.1（CVE Record, JPCERT-AT-2026-0034）
- Node.js: v24.22.1 で cherry-pick 修正（Red Hat Bugzilla 2558973）
- PHP: Windows ビルド 8.5.12-1 / 8.4.27-1 / 8.3.36-1 / 8.2.35-1 に Brotli 1.2.1 同梱（php.net アーカイブ 2026）。セッションアップロード進捗（`session.upload_progress.enabled=0`）に関する情報提供 advisories も 2026年10月分として別扱い
- .NET: 2026年10月25日 OOB セキュリティ更新（.NET 8/9/10）で Brotli 問題対処。既定構成では Brotli 展開は有効化されず、`ASP.NET Core` 要求解凍または `HttpClient` 応答解凍を明示的に有効化した場合のみ影響（Microsoft Update Guide）
- Ubuntu 22.04 LTS (jammy): `brotli` は `1.0.9-2ubuntu0.1` で修正（USN-8956-1, 2026-10-26）。本机的 WSL は `1.0.9-2build6`（未適用）。jammy の nodejs はシステム brotli 使用のため「Not affected」判定
- cFosSpeed 11.02.1700 修正 claims: 会話内で示された主張であり、ベンダー公告は照合できていない → **未検証**（実測バージョン 12.01）

## 次に更新すべきだと思うもの（優先順、実行はしていない）

1. Firefox 127.0 → 158 以降（明示的な目安未達の唯一のブラウザ）
2. WSL Ubuntu 22.04 の `libbrotli1` `1.0.9-2build6` → `1.0.9-2ubuntu0.1`（USN-8956-1）／curl 7.81.0 系統
3. Miniconda3 (py39) の `brotlipy 0.7.0` → brotli 1.2.1 / brotlicffi 1.2.1.0（あわせて pip 22.2.2, urllib3 1.26.9, requests 2.27.1）
4. Windows Update の自動更新設定（`NoAutoUpdate=1` / `AUOptions=2`）を見直し、10月以降の累積更新を確実に適用。あわせて QuickScan 未実行（Overdue）と FullScan 2023年の状態を確認
5. Windows 10 22H2 の扱い（サポート終了時期を過ぎたエディション。Windows 11 移行 or ESU の可否を確認）
6. Java 8 Update 301 / JDK 16.0.2（EOL）→ LTS 移行
7. Python 3.7.8（EOL）の除去、Python 3.10.8 と pip 22.2.2 の更新
8. Visual Studio Build Tools 2022 `17.14.42` → `17.14.43`（同シリーズ目安に1差分未達）
9. 7-Zip `19.00` → `26.05`（brotli 展開経路のアーカイバ）
10. EOL な .NET 系列（2.1.30 / 3.1.25・3.1.32 / 5.0.4・5.0.9・5.0.17）と Windows PowerShell 5.1 依存の停止。自作 .NET Framework ツール（v2.0〜v4.7.2, `C:\Users\<user>\source\repos`）は .NET Framework 4.8 累積更新依赖で、該当 KB の CVE マッピングは不明

## 注記

- `Get-AppxPackage` はこの環境ではモジュール読込エラー（0x80131539）で実行できず、Outlook（new）のバージョンは `winget list` の値を採用しています。
- 秘密情報（APIキー、トークン、Cookie、.env の内容）は読まず、存在のみ報告しています。
- cFosSpeed のバージョン claims は会話内の未検証情報として扱い、実測値（12.01）のみを事実として記録しています。
