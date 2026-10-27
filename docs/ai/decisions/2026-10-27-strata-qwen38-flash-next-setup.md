# Strata + Qwen3.8-Flash-Next（IQ2_XS）配置の推奨値を決定

**Date**: 2026-10-27

**Decision**: この PC（RTX 3090 24GB・RAM 64GB・Windows 11）で **Strata 0.2.6** をインストールし、**ISTA-DASLab 元モデル Qwen3.8-Flash-Next / IQ2_XS** を初回モデルとして採用する。モデル保存先は **`C:\OtherApp\Qwen3.8-Flash-Next`**（既在の `C:\OtherApp\Qwen3.8-27B` 等の慣習に準拠）。Kilo Code は OpenAI Compatible プロバイダーで **`http://127.0.0.1:8080/v1`** へ接続。実装開始指示待ち（本決定自体は記録のみ）。

**Reason**:
- C: 空きは実測 **390 GB**（2026-10-27 2回確認）。IQ2_XS（68 GB）+ MTPドラフトレイヤー（約6 GB）で約75 GB → 残約315 GB、十分。
- 64GB RAM では ISTA-DASLab 全サイズ適合（MODELS.md）。IQ2_XS の RAM 使用は約36 GB エクパート + 6 GB → 余裕あり。IQ3_XXS/S は「他のアプリを閉じる」前提で次へ。
- 画像入力の**実デフォルトはオン**（README 誤記: 初稿は「オフ」だった）。初回はオフにし、安定確認後に GPU リーダー（24GB VRAM で 1〜1.4 GB VRAM）を有効化。
- 公式計測（RTX 5070 12GB・64GB RAM、engine 0.1.26、DETAILS.md）: IQ2_XS 79.6 t/s（短チャット）、Q2_0 87.3 t/s。コミュニティ実測: RTX 3090+IQ3_S 82.5 t/s（issue #2095、Windows 11、RAM 127.8GB、Strata 0.1.43、issue は追跡整理で closed）。**100〜140 t/s の保証はしない**（README には未確認）。
- C:\OtherApp の既存慣習（`Qwen3.8-27B\Qwen3.8-27B-Q4_K_M.gguf` 等: 直下にモデル名フォルダ、gguf を直接中に入れる）に準拠。

**推奨値（最終）**:

| 項目 | 値 |
|---|---|
| バージョン | Strata **0.2.6**（2026-10-25 公開、最新。Qwen engine 0.1.50） |
| インストール | `Strata-0.2.6-windows-x64-setup.exe`、デフォルト（ユーザー単体・管理権限不要）。`SHA256SUMS.txt` と SHA-256 照合 |
| ドライバー | NVIDIA **580 以上**（CUDA 13 パッケージ） |
| アプリ本体 | デフォルトのユーザー アプリフォルダ（Strata が管理） |
| 実行エンジン | デフォルト `%LOCALAPPDATA%\Strata\components`（変更不能） |
| **モデル保存先** | **`C:\OtherApp\Qwen3.8-Flash-Next`**（アプリの保存フォルダ選択で指定） |
| 確保容量 | 100 GB以上（IQ2_XS 約75 GB。将来の IQ3_S なら約90 GB） |
| 量子化（初回） | **ISTA-DASLab / IQ2_XS** |
| コンテキスト（初回） | **32K** → 確認後に **128K** 試験 |
| 画像入力 | **オフ**（デフォルトがオンなので明示） |
| MTP | オン（デフォルト。約6 GB） |
| 速度期待値 | IQ2_XS 短チャット **約60〜85 t/s**。長文/エージェントターンはこれ以下。100〜140 t/s は保証外 |
| Kilo Code | Provider: **OpenAI Compatible** / Base URL: **`http://127.0.0.1:8080/v1`** / API Key: **`local`**（Strata ドocs: 任意文字列可） / Model: `GET /v1/models` が返す値（例: `strata`。Kilo が自動取得） |
| 検証 | `http://127.0.0.1:8080` で日本語回答 + Python 生成サンプル確認。Speed: Strata モニター + 必要なら `strata bench run` |

**Follow-up / 未確認**:
- Issue **#1988**（RTX 3090・UD-IQ4_XS 64.4 t/s）は確認できず。引用する場合は番号を再確認。
- 「README が RTX 3090 で 100〜140 t/s を見込む」は確認できない。正式文書では **公式計測は RTX 5070 基準、RTX 3090 期待値はコミュニティ実測 82.5 t/s（旧版エンジン）** とする。
- Windows インストーラーの**コード署名の有無は未確認**（SmartScreen 警告の断定表現は削除。Hash 照合で判断する）。
- issue #2095 は追跡整理で closed（データ自体は有効）。
- 初回接続後に `/v1/models` の返り値（Model ID）を記録する。
- 初回実行後の実測速度・RAM 使用量（モニタ画面 / `nvidia-smi`）を記録し、期待値と照合する。

**Alternatives**:
1. モデル保存先を `Documents\Strata\Models`（アプリ既定）— 動作は同じだが OtherApp 慣習に合致しない。
2. `D:\AI\Models\Strata` — D: 空き129GBで最大構成（IQ3_S 約90GB）はギリギリ、他用途と干渉する可能性。
3. IQ3_S を初回 — 品質向上だが RAM 余裕の減る（54.8 GB 目安 + 他アプリを閉じる前提）。初回安定確認後、32K→128K 検証の順に検討。

**Related**:
- 公式: [Strata README](https://github.com/Niko1221/Strata) / INSTALL.md / MODELS.md / DETAILS.md
- 公式: [HuggingFace Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)（ベンチマーク: SWE-bench Pro 62.5 vs Claude-Opus-4.6 (Max) 53.4 等）
- Kilo: [OpenAI Compatible providers](https://kilo.ai/docs/ai-providers/openai-compatible)
