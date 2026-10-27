# ローカルLLM用ハードウェア棚卸し（読み取り専用）

**Status**: 完了
**Date**: 2026-10-28
**Next Action**: docs/ai/reports へ報告 md 記録

## 意図 / 背景

現行ローカルモデル `qwen3.8-flash-next-iq2_xs` より良いローカル向けモデルがあるかを判断するため、マシンで「どのサイズ・量子化が現実的な速度で動くか」を判定する材料としてハードウェア値を読み取り専用で棚卸しした。改善・アップグレード提案は含まない。

## 調査結果 / 変更内容

- 報告: `docs/ai/reports/2026-10-28-hardware-local-llm-audit.md`
- 判定に効く確認済み値（根拠コマンド併記）:
  - CPU `Intel Core i7-8700K` 6コア/12スレッド、MaxClockSpeed 3696 MHz（`Get-CimInstance Win32_Processor`）。AVX2 対応・AVX-512 非対応は Strata ログの `this CPU has no AVX-512: the expert kernels run on AVX-2` で確認。AMX 不明
  - RAM 64 GiB（68.7 GB）= 16 GiB × 4枚、Speed/ConfiguredClockSpeed 2667、ChannelA/B 各2枚、スロット 4/4（空き0）、SMBIOS MaxCapacity 67108864 KB = 64 GiB（`Win32_PhysicalMemory`, `Win32_PhysicalMemoryArray`）。規格 DDR4/DDR5 は CIM フィールドなし → 不明
  - GPU `NVIDIA GeForce RTX 3090` 1枚、VRAM `nvidia-smi` 24576 MiB（24 GiB）、使用 23517 MiB、driver 596.49、CUDA Version 13.2（`nvidia-smi`）。WMI `AdapterRAM` は 4,293,918,720 B（4.0 GiB）で4 GiB上限切り詰め。物理GPUは1枚のみ（`Meta Virtual Monitor` は仮想ディスプレイ）
  - ストレージ: モデル実体は **C**（NVMe Samsung 970 EVO Plus 1TB、空き 261.5 GiB／280.8 GB）。内部最大空きは **S**（SATA HDD 8TB、5444.0 GiB）（`Get-PhysicalDisk`, `Get-Volume`）
  - 実行環境: Ollama・LM Studio・Jan・Atomic Chat・text-generation-webui 等は未インストール（`Get-Command`、Uninstall レジストリ）。実行アプリは **Strata**（terminal 0.1.51、engine 0.1.50 CUDA13ビルド）＋同梱 llama.cpp version 0.4.1（`CMakeLists.txt`）
  - 現モデル: GGUF 分割2ファイル・**IQ2_XS**、合計 68,026,093,024 バイト（63.35 GiB／68.0 GB）。`--ple-gguf`（native experts）構成。実行中 `--max-context 262144`（log 2026-10-27 23:55:27 の engine started 行）。VRAM free 507〜938 MiB の警告＝256K 運用で VRAM がほぼ上限
  - CUDA Toolkit 12.6（V12.6.85、`nvcc --version`）、Python 3.10.8（`python --version`）
- 不明（記録）: AMX、メモリ規格、boost クロック、OSビルド末尾（UbrBuildNumber 空）、共有GPUメモリ、PCIeスロット空き（SMBIOS に PCI Slot レコードなし）、電源容量（W）、Strata 同梱 Python バージョン

## Verification

- 読み取り専用のみ（インストール・設定変更・再起動・削除・ベンチマーク・ドライバ更新なし）。このタスクは docs/ai の記録更新のみで、プロジェクトコードの変更はない → pytest / build 不要（AGENTS.md 例外）
- 秘密情報の値は出力せず。モデルフォルダはファイル名とサイズのみ確認（`.env` 等未読）。ユーザー名は `<user>` に伏字
- 数値の根拠コマンド: `Get-CimInstance`（Win32_ComputerSystem / OperatingSystem / SystemEnclosure / Processor / PhysicalMemory / PhysicalMemoryArray / VideoController / BaseBoard / BIOS / Battery / OnBoardDevice / PnPEntity）、`Get-ItemProperty`（HKLM CurrentVersion）、`nvidia-smi`、`Get-PhysicalDisk`、`Get-Volume`、`nvcc --version`、`python --version`、`Get-Command`、`Test-Path`、`Get-ChildItem`（Length）、`Measure-Object`、`Get-HotFix` 不使用

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
