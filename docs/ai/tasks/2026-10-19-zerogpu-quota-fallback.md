# ZeroGPU quota 閾値以下でPollinationsへフォールバック

**Status**: 完了
**Date**: 2026-10-19
**Next Action**: 設計案をユーザーに提示、承認後に実装

## 意図 / 背景

ユーザー依頼: HF Space（blume/kemono-image-api, ZeroGPU）の残量（GPU 秒）を確認し、閾値以下であれば画像生成を別のサービス（Pollinations.ai）にフォールバックする。前回のタスクで quota API（`GET https://huggingface.co/api/spaces/zero-gpu/quota`, 認証必須、`{"base":300,"current":300,"resetsAt":null,"overquotaUsed":0,"runs":{...}}`）の取得と GitHub Actions での確認が実証済み。

## 調査結果 / 変更内容（設計案）

### 現状（変更前）
- `scripts/article/image.py::generate_and_save_image()`
  - `IMAGE_PROVIDER=pollinations` → 直接 Pollinations
  - それ以外は HF Space（gradio_client）2回リトライ（間隔15秒）→ 全失敗で Pollinations にフォールバック
- 記事あたりの画像: ヘッダー1枚 + 本文内最大 `MAX_INLINE_IMAGES=7` 枚 = 最大8枚
- 1回呼び出し = `@spaces.GPU(duration=20)`（`hf-space/app.py:308`）→ 最大20 GPU 秒/回
- Free クォータ: 300 GPU 秒/日（初使用後24hでリセット）+ 1日実行枠 `runs.limit=8`（`runs` の意味は不確実。判定には使わない）

### 提案（v2: ユーザー指針「1回だけ＋確認失敗時はリトライ」）
1. 変更箇所:
  1. `scripts/article/config.py`
     - `ZERO_GPU_QUOTA_URL = "https://huggingface.co/api/spaces/zero-gpu/quota"`
     - `ZERO_GPU_QUOTA_THRESHOLD_SECONDS = int(os.environ.get("ZERO_GPU_QUOTA_THRESHOLD_SECONDS", "40"))`（1回=20秒 × 2。env 上書き可）
     - `ZERO_GPU_QUOTA_CHECK_ATTEMPTS = int(os.environ.get("ZERO_GPU_QUOTA_CHECK_ATTEMPTS", "3"))`
     - `ZERO_GPU_QUOTA_CHECK_TIMEOUT_SECONDS = int(os.environ.get("ZERO_GPU_QUOTA_CHECK_TIMEOUT_SECONDS", "5"))`
     - `ZERO_GPU_QUOTA_CHECK_DELAY_SECONDS = int(os.environ.get("ZERO_GPU_QUOTA_CHECK_DELAY_SECONDS", "5"))`（リトライ間隔）
     - `__all__` へ追加
  2. `scripts/article/image.py`
     - モジュール級状態: `_ZERO_GPU_CHECKED = False`、`_ZERO_GPU_USE_HF = True`
     - 新規 `_fetch_zero_gpu_quota_remaining_once() -> float`:
       - `requests.get(ZERO_GPU_QUOTA_URL, headers={"Authorization": f"Bearer {HF_TOKEN}"}, timeout=ZERO_GPU_QUOTA_CHECK_TIMEOUT_SECONDS)`
       - 非200 / 例外 / 応答 `current` が数値でない / HF_TOKEN 欠落 → 例外
       - 200 → `float(data["current"])`
     - 新規 `_zero_gpu_quota_remaining() -> float | None`:
       - 単発取得を **最大 `ZERO_GPU_QUOTA_CHECK_ATTEMPTS` 回（既定3）** 実行。失敗時はログ + `time.sleep(ZERO_GPU_QUOTA_CHECK_DELAY_SECONDS)`（既定5秒）で再試行
       - 成功時は残秒、最終失敗時は `None`
     - 新規 `_determine_zero_gpu_provider() -> bool`（**プロセスで1回のみ、結果はフラグでキャッシュ**）:
       - 未確認なら quota 取得 → 残量 < 閾値 → False（Pollinations）、残量 >= 閾値 → True（HF）、`None` → True（fail-open）を判定し `_ZERO_GPU_USE_HF` に格納
       - 以降の呼び出しはフラグ返しのみ（ロジック・APIなし）
       - ログ（各1回のみ）: 成功 `📊 ZeroGPU quota: 残量 XXX sec（閾値 YY sec 以上）→ HF`／閾値以下 `⚠️ … → 画像生成は Pollinations.ai（HF 未接続）`／確認失敗 `⚠️ ZeroGPU quota 確認失敗（N回）→ HF を試行（fail-open）`
     - `generate_and_save_image()`: `IMAGE_PROVIDER == "pollinations"` ブランチの次で `not _determine_zero_gpu_provider()` のとき `_generate_image_pollinations()` へ直接（HF リトライなし）
     - docstring 更新
- 確認頻度: **プロセス1回**（最初の画像生成時に遅延評価）
  - 追加コスト: 成功時は ~1回 × 5秒以下。失敗時は 3回 × 5秒 + 2回 × 5秒 sleep = 25秒上限（その後は fail-open で HF 路に進入）
  - 途中残量枯渇（初回確認で閾値以上だったが生成途中で枯渇）は、**現行の画像1回ごとの HF→Pollinations フォールバック** が吸収（変更不能）
- 判定・ログ
  - 閾値以上: 現行（HF 2回リトライ → Pollinations）
  - 閾値以下: `⚠️ ZeroGPU quota 残量 XXX sec が閾値 YY sec 以下 → Pollinations.ai へ切り替え` を出力し、HF 未接続で Pollinations
  - quota 確認失敗: 試行数回で `⚠️ ZeroGPU quota 確認失敗（試行 N/N）: <reason>` を出力し、全試行失敗後は `→ HF 試行を続行` を出力し、現行通り（fail-open）
- テスト（`scripts/tests/test_generate_article.py` / `equivalence_check.py`）
  - 既存4テスト（`TestGenerateAndSaveImage`）: `_zero_gpu_quota_remaining` を 300.0 へ patch（外部 API 呼出し禁止のため。`requests.get` の patch は quota 確認も含めて mock）
  - 新規: 閾値以下 → Pollinations（`requests.get` mock、HF `Client` 未呼び出し）
  - 新規: quota 確認失敗（403/タイムアウト/JSON 不備）→ 試行3回 → HF 試行
  - 新規: `generate_and_save_image()` を 2回呼び出して quota API は 1回のみ呼ばれることを検証（判定のフラグキャッシュ。1回=ヘッダー画像、2回=本文内画像の最小構成）
  - テスト毎にフラグリセットは pytest の `autouse` フィックスチャ（`_reset_quota_state`）で実施。単純な `setUp` ではモジュール状態がテスト間で持ち越されるため非効力だった
  - 検証: `pytest scripts/tests/ -v`
- 影響
  - `generate_article.py`、frontmatter、Pollinations 実装、`_generate_image_pollinations` は無変更
  - 判定の失敗モードはすべて「現行挙動」に収まる（fail-open / 全失敗 → 画像なし）
  - 追加コスト: プロセスあたり quota 確認 **1回のみ**（成功時 5秒以下。失敗時 最大3回 + sleep 2回 = 25秒上限、以降は fail-open で HF 路。外部 API 1件〜3件、日次・低頻度）

## Verification

- **テスト**: `pytest scripts/tests/ -v` → **444 passed**（8.20s）
  - 新規3件: 閾値以下→Pollinations（HF 未接続）／2回の画像生成で quota API は1回のみ（フラグキャッシュ）／quota 確認失敗（403）→リトライ3回→fail-openで HF 試行
  - 既存4件（HF成功・失敗フォールバック・両方失敗・Pollinations専用）: 変更なしで継続通過
- **実装確認**: quota 判定はプロセス1回のみ（`_ZERO_GPU_CHECKED` フラグ、`_reset_quota_state` autouse fixture でテスト毎にリセット）
- 実行: `py -3.10 -m pytest scripts/tests/ -v`（pytest は Python 3.10 環境）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
