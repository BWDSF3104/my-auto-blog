# ローカルLLM用ハードウェア棚卸し報告（読み取り専用）

- 実施日時: 2026-10-28（現地時間）
- 目的: 現行モデル `qwen3.8-flash-next-iq2_xs` より良いローカルモデルを選定するため、マシンで「どのサイズ・量子化が現実的な速度で動くか」を判定する材料として hardware 値を取得
- 制約遵守: 読み取り専用のみ。更新・インストール・設定変更・再起動・ファイル削除・ベンチマーク実行・ドライバ更新は行っていません
- 秘密情報: 値は出力していません。モデルフォルダではファイル名とサイズのみ確認（`.env` 等は読んでいない）。ユーザー名は `<user>` に伏字
- task file: `docs/ai/tasks/2026-10-28-hardware-local-llm-audit.md`

## 要約（5行）

1. **CPU**: Intel Core i7-8700K（6コア／12スレッド、MaxClockSpeed 3696 MHz）。AVX2 対応・AVX-512 非対応（Strata ログで確認）。AMX 不明
2. **RAM**: 64 GiB（=68.7 GB）＝ 16 GiB × 4枚、動作 2667 MHz、ChannelA/B 各 DIMM0+DIMM1、スロット 4/4 使用（空き 0）、SMBIOS MaxCapacity 64 GiB
3. **GPU**: NVIDIA GeForce RTX 3090 1枚のみ、VRAM `nvidia-smi` 表示 24576 MiB（24 GiB）、driver 596.49、CUDA Version 13.2。物理GPUは1枚（`Meta Virtual Monitor` は仮想ディスプレイ）
4. **ストレージ空き**: モデル実体は **C**（NVMe Samsung 970 EVO Plus 1TB）＝空き 261.5 GiB（280.8 GB）。最大の空きは **S**（SATA HDD 8TB）＝5444.0 GiB
5. **現行モデル**: GGUF 分割2ファイル／**IQ2_XS**、合計 68,026,093,024 バイト（63.35 GiB／68.0 GB）、実行アプリ **Strata**（llama.cpp 0.4.1 ベースの CUDA13 ビルド）、実行中 `--max-context 262144`

---

## 1. PC全体

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| 形態 | デスクトップ | `Get-CimInstance Win32_SystemEnclosure` → ChassisTypes `{3}`（=Desktop）、`Win32_Battery` 結果なし | — |
| メーカー／機種名 | Manufacturer・Model・SystemFamily すべて `To Be Filled By O.E.M.` | `Get-CimInstance Win32_ComputerSystem` | 自作構成（マザーボード ASRock Z370 Pro4） |
| OS | Microsoft Windows 10 Home / Version `10.0.19045` / BuildNumber `19045` / 64bit / DisplayVersion `22H2` / ReleaseId `2009` | `Get-CimInstance Win32_OperatingSystem`、`Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion` | `UbrBuildNumber` は空 → ビルド末尾（19045.xxxx）不明 |

## 2. CPU

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| 型番 | `Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz` | `Get-CimInstance Win32_Processor` | Intel64 Family 6 Model 158 Stepping 10 |
| 物理コア／論理 | 6 / 12 | 同上（`NumberOfCores` / `NumberOfLogicalProcessors`） | — |
| クロック | MaxClockSpeed 3696 MHz / CurrentClockSpeed 3696 MHz | 同上 | boost 最大値は WMI から不明 |
| AVX2 | 対応 | `docs` 外ログ `C:\Users\<user>\AppData\Local\Strata\install\strata-iq2_xs.log` | `this CPU has no AVX-512: the expert kernels run on AVX-2` |
| AVX-512 | 非対応 | 同上のログ行 | CPU-Z 未インストール（`C:\Program Files*\CPUID\CPU-Z` なし） |
| AMX | 不明 | 確認手段なし（ログ・CIM に記載なし） | — |

## 3. メモリ（RAM）

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| 総容量 | 68,719,476,736 バイト = **64 GiB**（68.7 GB） | `Get-CimInstance Win32_PhysicalMemory`（Capacity 17179869184 × 4） | — |
| 枚数／構成 | 16 GiB × 4枚（Manufacturer `Samsung`、PartNumber `M378A2K43CB1-CTD`、FormFactor `8`=DIMM） | 同上 | シリアル番号は未取得 |
| 規格 | **不明**（CIM に DDR4/DDR5 フィールドなし） | 同上 | 製品仕様・品番からの表記は推定になるため記録しない |
| 動作クロック | Speed `2667` / ConfiguredClockSpeed `2667`（MHz 表記） | 同上 | — |
| スロット使用 | `MemoryDevices 4`、4枚占有 → **空きスロット 0** | `Get-CimInstance Win32_PhysicalMemoryArray` | DeviceLocator: `ChannelA-DIMM0`, `ChannelA-DIMM1`, `ChannelB-DIMM0`, `ChannelB-DIMM1` |
| チャネル構成 | ChannelA・ChannelB の2組（各2枚） | DeviceLocator 表記 | 2チャネル占有と読める。仕様書確認はしていない |
| 最大搭載可能容量 | `MaxCapacity` 67108864 KB = **64 GiB** | `Win32_PhysicalMemoryArray`（SMBIOS） | 現搭載量と一致（フル搭載） |

## 4. GPU

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| GPU型番 | `NVIDIA GeForce RTX 3090`（1枚） | `nvidia-smi`、`Get-CimInstance Win32_VideoController` | 内蔵GPUなし。`Meta Virtual Monitor`（DriverVersion 5.3.57.114）は仮想ディスプレイ |
| VRAM（専用GPUメモリ） | `nvidia-smi` = `24576MiB / 24576MiB`（=24 GiB／25.7 GB）。当日使用量 23517 MiB | `nvidia-smi` | — |
| WMI の AdapterRAM | 4,293,918,720 バイト = 4.0 GiB | `Win32_VideoController` | WMI の 4 GiB 上限による切り詰め。実VRAMは 24 GiB（nvidia-smi） |
| 共有GPUメモリ | 不明 | タスクマネージャー値はコマンドで取得不可 | — |
| ドライバ | `596.49`（nvidia-smi）／`32.0.15.9649`（WDDM表記） | `nvidia-smi`, `Win32_VideoController` | 同一ドライバの別表記 |
| CUDA Version | `13.2`（nvidia-smi 表示＝ドライバサポート上限） | `nvidia-smi` | CUDA Toolkit は 12.6（下記7項） |
| 電力 | `316W / 350W`（P2、GPU-Util 26%、Temp 63C、Fan 81%） | `nvidia-smi` | 参考値 |

## 5. ストレージ

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| C: | NVMe SSD `Samsung SSD 970 EVO Plus 1TB`（PhysicalDisk 1,000,204,886,016 B = 931.3 GiB）／Volume Size 999,462,277,120 B（930.7 GiB）／**空き 280,839,860,224 B = 261.5 GiB（280.8 GB）** | `Get-PhysicalDisk`（MediaType/BusType/Size）, `Get-Volume` | ラベル `Windows`。**モデル実体のあるドライブ** |
| G: | NVMe SSD `KIOXIA-EXCERIA PLUS G3 SSD`（2,000,398,934,016 B = 1862.6 GiB）／空き 162,213,355,520 B = **151.0 GiB（162.2 GB）** | 同上 | ラベル `NVMe2TB` |
| D: | HDD・SATA `ST3000DM007-1WY10G`（3,000,592,982,016 B = 2794.4 GiB）／空き 140,157,468,672 B = 130.5 GiB | 同上 | ラベルなし |
| S: | HDD・SATA `ST8000DM004-2U9188`（8,001,563,222,016 B = 7451.9 GiB）／空き 5,846,991,691,776 B = **5444.0 GiB（5.85 TB）** | 同上 | ラベル `SUBHDD`。内部ドライブでは最大の空き |
| F: | USB HDD `Seagate Expansion Desk`（MediaType `Unspecified`、8,001,563,221,504 B = 7451.9 GiB）／空き 737,905,664,000 B = 687.3 GiB | 同上 | ラベル `USB-HDD(DVDデータ等)` |
| H: | USB HDD `WD Elements 25A3`（16,000,867,106,816 B = 14899.2 GiB）／空き 6,305,031,962,624 B = 5874.0 GiB | 同上 | ラベル `USB-HDD(Backup)` |
| E: | Size 0（PhysicalDisk に対応レコードなし） | `Get-Volume` | 空のレター（光学/カードリーダーの可能性） |

## 6. マザーボード／拡張性

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| マザーボード型番 | Manufacturer `ASRock` / Product `Z370 Pro4` | `Get-CimInstance Win32_BaseBoard` | — |
| チップセット | `Intel(R) 300 Series Chipset Family SATA AHCI Controller` / `Intel(R) 300 Series Chipset Family LPC Controller (Z370) - A2C9` | `Get-CimInstance Win32_PnPEntity` | — |
| メモリ最大搭載 | 67108864 KB = 64 GiB（SMBIOS） | `Win32_PhysicalMemoryArray` | 製品仕様書からの確認はしていない |
| PCIeスロット空き | **不明** | `Win32_OnBoardDevice`（DeviceType `PCI Slot`）→ 該当レコードなし | — |
| BIOS | `American Megatrends Inc.` / `P4.30E` / ReleaseDate `2022-10-27 9:00:00` | `Get-CimInstance Win32_BIOS` | — |

## 7. ローカルAIの実行環境

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| Ollama | 未インストール／コマンドなし | `Get-Command ollama`、`Test-Path C:\Users\<user>\.ollama\models`、Uninstall レジストリ | — |
| LM Studio | 未インストール／コマンドなし | `Get-Command lmstudio`、`Test-Path ...\AppData\Roaming\LMC`・`\.lmstudio`、Uninstall レジストリ | — |
| Jan / Atomic Chat / text-generation-webui / KoboldCPP / GPT4All / TabbyAPI | 未インストール／コマンドなし | `Get-Command`、Uninstall レジストリ | — |
| llama.cpp | ソースツリー `C:\Users\<user>\AppData\Local\Strata\install\third_party\llama.cpp`、version **0.4.1**（`-dev` 分岐あり） | `CMakeLists.txt`（`LLAMA_VERSION_MAJOR 0` / `MINOR 4` / `PATCH 1`） | 単独インストールではなく Strata 同梱 |
| 実行アプリ | **Strata**（terminal `0.1.51`、engine `0.1.50-windows-x86_64-cuda-cuda13` の `strata.exe`／CUDA13ビルド、vision は `strata-vision.exe`）。port 8082 | `nvidia-smi` プロセス一覧、`strata-iq2_xs.log`、`run-iq2_xs*.bat` | Strata 単独 |
| 形式・量子化 | GGUF（分割2ファイル）／**IQ2_XS**：`Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf`（39,225,954,592 B）+ `-00002-of-00002.gguf`（28,800,138,432 B） | `Get-ChildItem`（Length） | `-00002` は `--ple-gguf`（native experts）として指定。pack は `tools/iq_pack.py` 生成（tensors 1079、pool 1,538,035,200 B） |
| モデル総サイズ | **68,026,093,024 バイト = 63.35 GiB（68.0 GB）** | `Measure-Object -Property Length -Sum` | 加えて `mmproj-Qwen3.8-Flash-Next-BF16.gguf` 907,543,008 B（0.85 GiB）、`mtp-q2_0.gguf` 889,017,216 B（0.83 GiB）、pack `dense.bin` 1,538,035,200 B（1.43 GiB） |
| 置きドライブ | **C** | 実パス | `C:\Users\<user>\AppData\Local\Strata\Strata-data\models\IQ2_XS\`（C の空き 261.5 GiB） |
| コンテキスト長 | 直近の engine 起動は `--max-context 262144`（`2026-10-27 23:55:27` の engine started 行） | `strata-iq2_xs.log` | 設定3種: `strata-iq2_xs.json` 32768 / `-128k.json` 131072 / `-256k.json` 262144。その他 `--kv int8`、`--kv-resident 32768`、`--spec 4`、`--spec-min-p 0.5`、`--vram-reserve-mib 1600`、`--vision`、`--expert-cache auto`、`--prefill auto` |
| VRAM余裕 | ログに「VRAM free 507〜938 MiB（1024 MiB 未満）」の警告あり → 256K 運用時に VRAM がほぼ上限 | `strata-iq2_xs.log` | 現モデルは 24 GiB VRAM にほぼ乗り切り（実測使用 23517 MiB） |
| Python | `Python 3.10.8`（`C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe`） | `python --version` | Strata 同梱 python（`...\terminal\current\python\python.exe`）は起動に使われているがバージョン未取得 |
| CUDA Toolkit | release `12.6`, `V12.6.85`（`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6`） | `nvcc --version` | 実行時ドライバは CUDA Version 13.2 を報告 |

## 8. 電源・その他

| 項目名 | 値（正確に） | 確認方法 | 備考 |
|---|---|---|---|
| 電源ユニット容量（W） | **不明** | ソフトウェアから読める情報源なし | nvidia-smi のカード cap 350W は参考値 |
| 駆動前提 | バッテリーなし（台式机＝AC接続前提） | `Win32_Battery` 結果なし、ChassisTypes `{3}` | — |

## 確認できなかった項目

- AMX 対応有無（および AVX2/AVX-512 のコマンド出力による独立確認。ログ記載のみ）
- メモリの規格（DDR4／DDR5）— CIM に規格フィールドなし
- CPU の boost 最大クロック（WMI は base 3696 MHz のみ）
- OS ビルド末尾（19045.xxxx）— `UbrBuildNumber` が空
- GPU の共有GPUメモリ（タスクマネージャー値）
- PCIeスロットの空き状況・Gen 世代（SMBIOS に PCI Slot レコードなし）
- メモリ最大搭載可能容量の製品仕様書による確認（SMBIOS の 64 GiB のみ）
- 電源ユニットの型番・容量（W）
- Strata 同梱 Python のバージョン
- Strata / engine のバージョンはパス（`terminal/0.1.51`、`engine/0.1.50`）から読んだ値で、アプリ自身のバージョン表示コマンドは実行していない
