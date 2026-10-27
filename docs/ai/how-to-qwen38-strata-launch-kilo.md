# Qwen3.8-Flash-Next（Strata）実行・Kilo Code 接続の手順書

この PC 上、**Strata 0.2.6 + Qwen3.8-Flash-Next / IQ2_XS** をローカル LLM として
実行し、Kilo Code の OpenAI Compatible プロバイダーとして使うための手順。

Agent は「実行前のダウンロード＋設定」までを完了済み。
**実際の起動・Kilo 接続は GPU 解放後のユーザーが実施する。**

- 決定: `docs/ai/decisions/2026-10-27-strata-qwen38-flash-next-setup.md`
- 実行記録: `docs/ai/tasks/2026-10-27-strata-qwen38-setup.md`
- 公式: <https://github.com/Niko1221/Strata>

## 前提: GPU を解放する（最重要）

現在の Kilo エージェントセッションは、同一 GPU で Bonsai 2 27B を稼働中
（`nvidia-smi` で GPU メモリ約 18 GB 占有）。Strata も同一 GPU を使うため、
**実行前にこのエージェントセッションを閉じる**。閉じた後 `nvidia-smi` で
GPU メモリ使用がほぼ 0 になるまで待つ。

> 例: 「Kilo のセッションを閉じる → `nvidia-smi` で GPU 使用 0 確認 → 以降の手順」

## 1. モデル実行（初回）

### 1.1 起動
```bat
:: 方式A: 起動スクリプト（ダブルクリック可。port 8082）
"C:\Users\fujim\AppData\Local\Strata\install\run-iq2_xs.bat"

:: 方式B: ターミナルから（必要なら --port で port 変更。例: 8082）
$bin = Join-Path $env:LOCALAPPDATA 'Strata\terminal\current\bin'
& "$bin\strata.cmd" launch --model IQ2_XS --family qwen --port 8082
```

初回に**GPU エンジン（0.1.50 cuda13、581MB）をダウンロード**し、モデルを起動する。
起動時は大量の RAM 読み込みが発生し、数分 PC が重くなる。**画面を閉じない**。
完了するとブラウザ（またはターミナル）に API アドレスが表示される。

### 1.2 実行中の確認
- Strata monitor / ブラウザ `http://127.0.0.1:8082` で日本語テストを送る（2 以降）。
- GPU が Strata により占有される（`nvidia-smi`）。

## 2. ローカル API 検証

```text
http://127.0.0.1:8082/health
```
→ `"loaded"` を返す。

```text
http://127.0.0.1:8082/v1/models
```
→ 返された **Model ID を記録**（例: `strata`）。後で Kilo の Model 指定に使われる。

### 日本語・Python テスト（成功確認用）
```text
日本語で回答してください。
次の条件を満たすPythonスクリプトを作成してください。

- 指定したフォルダー配下の.pyファイルを検索する
- ファイル名と行数を一覧表示する
- 対象ファイルがない場合は理由を表示する

まず設計を説明し、その後に実装例を示してください。
```
エラーなく日本語で回答が生成されたら OK。

## 3. Kilo Code 接続

1. Kilo 設定（歯車）→ **Provider** → **OpenAI Compatible**
2. Base URL:
   - port 8082 の場合: `http://127.0.0.1:8082/v1`
3. API Key: `local`（任意文字列可。Strata は key を強制しない）
4. Model: 2 の `/v1/models` が返した Model ID（例: `strata`）
5. 短い日本語の質問を送り、回答を確認

> 注意: **Strata の GUI / サーバーが閉じているとモデルが停止 → Kilo 不通**。
> 起動中は Strata サーバー（port 8080/8082）を保持する。

## ポート設定（8082 固定済み）

**8082 に固定済み**（2026-10-27 ユーザー指定）。起動スクリプトは以下の通り変更済み:

- `C:\Users\fujim\AppData\Local\Strata\install\run-iq2_xs.bat` 内の
  `--port "8080"` → `--port "8082"` に変更済み。スクリプト起動で常に 8082 になる。

### 他のポートに変更する場合

```bat
& "$bin\strata.cmd" launch --model IQ2_XS --family qwen --port <PORT>
```
その場合は Kilo 側の Base URL も `<PORT>` に合わせて変更する。

> port は `strata launch --port N` で任意指定可（N は自由）。
> 変更した場合は「Kilo の Model ID」は不変（Model ID は port に関係なく `/v1/models` の返り値）。

## 実行時の速度・メモリ記録（完了時にタスクファイルへ記入）

- **生成速度**（短チャット）: 期待値 **60〜85 t/s**（100〜140 t/s は保証外）
  - Strata monitor の速度表示で確認
- **GPU**: `nvidia-smi` の VRAM 使用量・使用率
- **OS RAM**: Task Manager / `Get-CimInstance Win32_OperatingSystem` で RAM 使用量

上記を `docs/ai/tasks/2026-10-27-strata-qwen38-setup.md` の
「Verification」セクションに記録する。

## 問題解決

| 症状 | 対処 |
|---|---|
| 起動しっぱたれず GPU メモリ不足 | `--mtp off`（MTP 無効、約 1GB の VRAM・RAM 節約。速度は低下）。RAM 不足なら `--low-ram on` |
| Kilo から不通 | ① Strata サーバーが閉じていないか ② Base URL の port が合っているか（8080/8082）③ URL の末尾スラッシュ / https 化していないか ④ Model ID が `/v1/models` の返り値と一致するか |
| 初回にエンジン取得が失敗 | 回線再確認。`strata update`（GPU 使用でテスト起動するため、GPU 解放後に） |
| 画面が黒くなる / PC が凍結 | `--vram-reserve-mib 1500` で GPU 表示用に VRAM を確保（GPU がディスプレイ駆動中時） |

## 関連

- 決定: `docs/ai/decisions/2026-10-27-strata-qwen38-flash-next-setup.md`
- 実行記録・状態: `docs/ai/tasks/2026-10-27-strata-qwen38-setup.md`
- 公式: <https://github.com/Niko1221/Strata>（README / MODELS.md / DETAILS.md）
- Kilo: <https://kilo.ai/docs/ai-providers/openai-compatible>
