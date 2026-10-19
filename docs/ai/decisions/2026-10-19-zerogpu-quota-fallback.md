# ZeroGPU quota 残量で HF / Pollinations をルーティング（プロセス1回判定）

**Date**: 2026-10-19

**Decision**: 画像生成入口（`scripts/article/image.py::generate_and_save_image`）に ZeroGPU quota 確認を追加。quota API（`GET https://huggingface.co/api/spaces/zero-gpu/quota`）をリトライ3回（間隔5秒、タイムアウト5秒）で取得し、モジュール級フラグ（`_ZERO_GPU_CHECKED` / `_ZERO_GPU_USE_HF`）で **プロセス1回のみ判定**する。残量 < 閾値40秒（env `ZERO_GPU_QUOTA_THRESHOLD_SECONDS` 上書き可）なら全画像は HF 未接続で Pollinations.ai、閾値以上なら現行の HF 路。quota 確認失敗（リトライ含む）は fail-open（現行挙動維持）。

**Reason**:
- `hf-space/app.py:308` の `@spaces.GPU(duration=20)` は1回最大20 GPU 秒を消費。Free クォータは300 GPU 秒/日（8実行枠）。残量が枯弊に近づく状態で HF を呼ぶと、リトライ2回（30秒以上）で失敗し、その後 Pollinations にフォールバック — 失敗コストが大きい。閾値以下なら事前で切り替え。
- 画像毎に確認すると 1記事最大8回 API 呼出（+遅延）になるため、ユーザー方針（2026-10-19）で「最初の1回だけ判定、以降はキャッシュ」。
- 途中残量枯渇（初回確認で閾値以上だが生成途中で枯弊）は、**現行の画像1回ごとの HF→Pollinations フォールバック**が吸収（変更不能）。

**トレードオフ（許容）**:
- quota API はアカウント（blume）単位で、同じアカウントの他サービス利用も残量を消費する。
- quota 確認失敗時の fail-open は現行挙動（HF リトライ+Pollinations フォールバック）に収まるため、失敗モードは変更なし。

**関連**:
- 閾値判定・ログ・リトライ設定は `article/config.py`（`ZERO_GPU_QUOTA_*` 定数）
- テストは `scripts/tests/test_generate_article.py::TestGenerateAndSaveImage`（8件）
