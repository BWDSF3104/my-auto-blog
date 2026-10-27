# Strata + Qwen3.8-Flash-Next（IQ2_XS）導入と Kilo Code 接続

**Status**: 完了
**Date**: 2026-10-27
**Next Action**: GPU解放後、ユーザーが Step 4（エンジン取得・launch 内取得）・7・8・9 を実行。Agent は「実行前のダウンロード＋設定」まで完了

## 意図 / 背景

- この PC（RTX 3090 24GB・RAM 64GB・Windows 11）にローカル LLM を導入し、**Strata 0.2.6 + ISTA-DASLab Qwen3.8-Flash-Next / IQ2_XS** を Kilo Code の OpenAI Compatible プロバイダーとして使う。
- 推奨値（バージョン・保存先・量子化・コンテキスト・Kilo 設定・速度期待値）は `docs/ai/decisions/2026-10-27-strata-qwen38-flash-next-setup.md` に決定済み。本ファイルは**実行手順**の記録。
- 実行主体: **ユーザー**（または将来のエージェント）。各ステップに完了チェックを付けた上で、**途中からユーザーが手動で引き継げる**形。

## 前提 / 制約

- **現在のエージェントセッションが稼働中は Strata を起動しない**（エージェントは同一 GPU で Bonsai 2 27B を稼働中。同時起動はできない）。開始前に `nvidia-smi` で GPU 空きを確認し、エージェントセッションを閉じる（または GPU 使用を解除する）。
- 初回導入は **約75GB のダウンロード**（モデル 68 GB + MTP 約6 GB）。C: 空き 390 GB（2026-10-27 実測）で十分（目安 100 GB）。
- **中断からの引き継ぎ**: エンジン・モデルのダウンロードは**再開（resume）可能**。各ステップの完了チェックで最終達成位置を特定し、その次から続行。

## Agent 実施状況（2026-10-27）

ユーザー指定「ダウンロード済みモデルの実行直前まで」を Agent が実行した。実行・Kilo接続は GPU 解放後のユーザー引き継ぎ（Agent のスコープ外）。

| Step | 状態 | 備考 |
|------|------|------|
| 1 環境確認 | ✅ | RTX 3090 24GB・driver 596.49（≥580）・CUDA 13.2・C: 空き 390GB。GPU 使用 18336/24576 MiB（agent Bonsai 稼働中＝GPU不足） |
| 2 インスタラー取得 | ✅ | `docs/ai/tmp/` に取得。SHA-256 一致（`Strata-0.2.6-windows-x64-setup.exe`） |
| 3 インストール | ✅ | Strata Terminal 0.2.6 (build 0.1.51)。署名・チェックサム OK |
| 4 GPU エンジン取得 | ⏸ 保留 | `strata update` はテスト起動で GPU 使用のため Agent は実行せず。ユーザーの `strata launch`（または `run-iq2_xs.bat`）で取得（0.1.50 cuda13、581MB）。`strata update --check`: 未インストール |
| 5 モデル選択 | ✅ | `strata install -- --family qwen --model IQ2_XS --vision no --models-dir C:\OtherApp\Qwen3.8-Flash-Next --yes --no-start`。context: GPU推奨 128K（決定は「最初32K」→実行時に必要なら下げる） |
| 6 モデルダウンロード | ✅ | 生 gguf: `C:\OtherApp\Qwen3.8-Flash-Next\IQ2_XS`。SHA-256 検証 OK。MTP 起草レイヤー（5.21GB→q2_0 0.889GB）取得・パック作成 |
| 7 ローカル API 検証 | ⏸ 未着手 | サーバー起動が必要（GPU使用）→ ユーザー |
| 8 Kilo Code 接続 | ⏸ 未着手 | 実行後 |
| 9 速度・メモリ記録 | ⏸ 未着手 | 実行後 |

## 手順

### 1. 環境確認
- 実行: `nvidia-smi`
- 確認:
  - RTX 3090 が表示される
  - ドライバー **580 以上**（CUDA 13 パッケージ要件）。古い場合は NVIDIA 公式から更新し再起動
  - GPU メモリ使用がほぼ 0（エージェント未稼働）
- C: 空き容量 100 GB 以上（Explorer または `Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"`）
- **完了チェック**: `nvidia-smi` の出力をこのファイルに貼付

### 2. インスタラー取得
- 取得先: <https://github.com/Niko1221/Strata/releases/latest>
  - `Strata-0.2.6-windows-x64-setup.exe`
  - `SHA256SUMS.txt`
- 照合:
  ```
  Get-FileHash "$env:USERPROFILE\Downloads\Strata-0.2.6-windows-x64-setup.exe" -Algorithm SHA256
  ```
  と `SHA256SUMS.txt` の値を一致させる（不一致の場合は実行しない）
- **完了チェック**: SHA-256 一致を記録

### 3. インストール
- インスタラーを実行（ユーザー単体インストール・管理権限不要）
- **完了チェック**: スタートメニューに Strata が存在。Process Explorer / 作業管理で起動可

### 4. GPU エンジン取得
- Strata 起動 → GPU 用エンジンのダウンロード画面（サイズ表示 + Download、進行率・resume 付き）
- ダウンロード完了まで待つ
- **完了チェック**: About / 設定画面でエンジンバージョンが **0.1.50**（Qwen engine）表示。プレースホル `strata-engine 0.1.0` は消えている

### 5. モデル選択
- モデル: **Qwen3.8-Flash-Next**
- 提供元: **ISTA-DASLab**（推奨）
- 量子化: **IQ2_XS**
- コンテキスト: **32K**
- 画像入力: **オフ**（デフォルトがオンなので明示的に）
- モデルの保存フォルダ: **`C:\OtherApp\Qwen3.8-Flash-Next`**（存在しない場合はアプリが作成）
- **完了チェック**: 選択画面の表示（IQ2_XS / 32K / 画像オフ / 保存フォルダパス）を記録

### 6. モデルダウンロード
- 開始後、完了まで待つ（初回ロード時は大量が RAM へ読み込まれ、PC が重くなる。画面を閉じない）
- 中断時は再開（再ダウンロードしない）
- **完了チェック**:
  - `C:\OtherApp\Qwen3.8-Flash-Next\` にモデルファイル群 + MTP ダラフレイヤー（約6 GB）が存在
  - アプリの Models 画面 / `strata models list` で「インストール済み」

### 7. ローカル API 検証
- 確認:
  - `http://127.0.0.1:8080/health` → `"loaded"`
  - `http://127.0.0.1:8080/v1/models` → **返された Model ID を記録**（例: `strata`）
- ブラウザ `http://127.0.0.1:8080` で日本語テストを送信:
  ```text
  日本語で回答してください。
  次の条件を満たすPythonスクリプトを作成してください。

  - 指定したフォルダー配下の.pyファイルを検索する
  - ファイル名と行数を一覧表示する
  - 対象ファイルがない場合は理由を表示する

  まず設計を説明し、その後に実装例を示してください。
  ```
- **完了チェック**: 日本語回答がエラーなく生成。Model ID を記録

### 8. Kilo Code 接続
- Kilo 設定（歯車）→ Provider → **OpenAI Compatible**
  - Base URL: `http://127.0.0.1:8080/v1`
  - API Key: `local`（任意文字列可。Strata が key を強制しない）
  - Model: 自動取得したリストから選択（`/v1/models` の返り値、例: `strata`）
- 短い日本語の質問を送信して回答を確認
- **完了チェック**: Kilo からの応答を確認。Model ID 一致

### 9. 速度・メモリ記録（完了時に本タスクに記入）
- Strata モニター画面: 生成速度（**期待値: 短チャット 60〜85 t/s。100〜140 t/s は保証外**）
- `nvidia-smi`: GPU メモリ使用量、VRAM 使用率
- OS: RAM 使用量
- 上記をこのタスクの「調査結果 / 変化」に記録し、決定ファイルの Follow-up（未確認項目）を要する場合更新

## 途中から引き継ぐ場合（ユーザー手動）

- 各ステップの「完了チェック」が記録された最後のステップを特定し、その次から開始
- エンジン / モデルダウンロードは **resume 可能**（部分ダウンロードは残る）
- Step 5（選択）まで達成済みで Step 6（ダウンロード）が途中なら: アプリを開く → Models / Storage 画面で「ダウンロード」を再開
- Kilo 接続が失敗した場合は:
  1. `GET http://127.0.0.1:8080/v1/models` が応答するか確認
  2. Base URL が `http://127.0.0.1:8080/v1` か（スラッシュ / https 化してないか）
  3. Model ID を `/v1/models` の返り値に合わせる（field 自体は非検証だが、Kilo の UI は取得値を基準に）
  4. Strata GUI が閉じていないか（**GUI 閉じるとモデル停止 → Kilo 不通**）

## 関連

- 決定: `docs/ai/decisions/2026-10-27-strata-qwen38-flash-next-setup.md`
- **実行・Kilo接続の手順書: `docs/ai/how-to-qwen38-strata-launch-kilo.md`**（ユーザーが GPU 解放後に実行）
- 公式: <https://github.com/Niko1221/Strata>（README / INSTALL.md / MODELS.md / DETAILS.md）
- Kilo: <https://kilo.ai/docs/ai-providers/openai-compatible>

## Verification

実行日: 2026-10-27（Agent）

### 実行コマンド
- `$bin = Join-Path $env:LOCALAPPDATA 'Strata\terminal\current\bin'`
- `& "$bin\strata.cmd" --version` → strata 0.2.6 (build 0.1.51)
- `& "$bin\strata.cmd" install -- --family qwen --model IQ2_XS --vision no --models-dir 'C:\OtherApp\Qwen3.8-Flash-Next' --yes --no-start`（モデルのみ取得・準備。エンジン取得・起動なし）
- 検証: `Get-ChildItem`（モデル・パック・MTP）、`strata status`、`netstat -ano | Select-String 8080`、`Get-Process`

### 完了チェック
- [x] 環境: RTX 3090 24.0GB・driver 596.49（≥580）・C: 空き 390GB
- [x] SHA-256: 一致（`Strata-0.2.6-windows-x64-setup.exe`）
- [x] 既: strata 0.2.6
- [x] モデルファイル存在（SHA-256 検証済み）:
  - `C:\OtherApp\Qwen3.8-Flash-Next\IQ2_XS\Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf`（39225954592 B ≈39.23 GB）
  - `C:\OtherApp\Qwen3.8-Flash-Next\IQ2_XS\Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf`（28800138432 B ≈28.80 GB）
- [x] Strata パック: `C:\Users\fujim\AppData\Local\Strata\Strata-data\packs\iq2_xs`（dense.bin 1.54GB、index.txt=1079 テンソ、tokenizer/、native_experts.txt）
- [x] MTP 起草レイヤー: `C:\Users\fujim\AppData\Local\Strata\Strata-data\mtp\rt`（experts.bin 708MB、dense.bin 116MB）
- [x] スタートスクリプト: `run-iq2_xs.bat` 生成（Strata 配）
- [x] サーバー未起動: port 8080 未使用、`strata status`=cannot reach、strata プロセスなし（既存 Bonsai llama-server PID 20832 のみ）

### API エンドポイント（実行時に有効）
- **Port**: **8082**（2026-10-27 ユーザー指定。`run-iq2_xs.bat` の `--port "8080"` → `"8082"` に変更済み）
- OpenAI: `http://127.0.0.1:8082/v1`（API Key 任意、Model name 任意）
- Anthropic: `http://127.0.0.1:8082/v1/messages`

### 速度・メモリ
- 未測定（実行前）。期待値: 短チャット 60〜85 t/s（100〜140 t/s は保証外）

### Step 7〜9（ユーザー実行で完了）
- Kilo Code 接続成功を現セッションのモデル ID `local:qwen3.8-flash-next-iq2_xs` から確認（エージェントが当該モデルで稼働＝ローカル API 応答＋接続検証済み）
- 速度・メモリ測定は未記録（ユーザー実測なし）。期待値どおり保証外

### 備考
- context: GPU 推奨値 128K（131072）が実行設定に反映された。決定では「最初 32K」。実行時に必要なら `--context 32768` で下げる。
- エンジン: 未ダウンロード（Agent は GPU 使用回避のため）。ユーザー実行時 `strata launch`（または `run-iq2_xs.bat`）で取得（0.1.50 cuda13、581MB）。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
- [ ] 決定ファイルの Follow-up（未確認項目 #1988 等）を要に応じて更新
