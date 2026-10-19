# ZeroGPU quota 残量確認ワークフロー

**Status**: 完了
**Date**: 2026-10-19
**Next Action**: ワークフロー作成・push・GitHub 起動で実験

## 意図 / 背景

ユーザー依頼: ZeroGPU クォータの残量（GPU 秒）を確認してログを出すだけの GitHub Actions ワークフローを作成し、GitHub 上で起動して実験する。`hf-space/`（blume/kemono-image-api）の GPU 確保が失敗・遅くなる原因（quota 枯渇）の切り分け利用を念頭に。

## 調査結果 / 変更内容

- Endpoint: `GET https://huggingface.co/api/spaces/zero-gpu/quota`（OpenAPI 確認済み、認証必須）
  - `base`: 総クォータ（GPU 秒）
  - `current`: 残りのクォータ（GPU 秒）
  - `resetsAt`: リセット時刻 ISO 8601（未使用なら null）
  - `overquotaUsed`: 追加課金分 GPU 秒（null 可）
- クライアント: `HfApi.get_zero_gpu_quota()`（`huggingface_hub`）— REST 同等
- 設計: `.github/workflows/zerogpu-quota-check.yml`
  - トリガー: `workflow_dispatch` のみ（実験目的。push トリガーは不要）
  - `runs-on: ubuntu-latest`、jq はランナー前提
  - `curl -fsS` + `jq` で raw 応答と整形（残秒・分換算・resetsAt）をログ出力
  - HTTP エラー時は `curl -f` で非0 exit → ジョブ失敗
  - 実応答フィールド（2026-10-19 GitHub 実行で確認）:
    - `base`, `current`, `resetsAt`, `overquotaUsed`（docs と一致）
    - `runs`: `{used, limit, remaining, resetsAt}` — 1日実行枠（Free 8 枠）も取得可能

## Verification

- **実行**: `gh workflow run zerogpu-quota-check.yml`（実行 ID: 39216236661, https://github.com/BWDSF3104/my-auto-blog/actions/runs/39216236661）
- **結果**: success（実行時間 約 1 秒）
  ```
  ZeroGPU quota (raw):
  {"base":300,"current":300,"resetsAt":null,"overquotaUsed":0,"runs":{"used":0,"limit":8,"remaining":8,"resetsAt":null}}

  ZeroGPU quota (parsed):
  {
    "total_gpu_seconds": 300,
    "remaining_gpu_seconds": 300,
    "remaining_minutes": 5,
    "resets_at": null,
    "overquota_used_seconds": 0
  }
  ```
- **補足**:
  - 初回実行（39215117655）は HTTP 403 で失敗。ユーザーが権限を修正後に success（200）
  - 未使用のため `resetsAt` は `null`（初使用後 24h のリセット時刻が次に表示）
  - 実応答は `runs`（実行数 0/8、残量 8）も含まれる
  - 検証方法: ローカル `.env` トークンでの事前テスト（200 + 同上の値）と GitHub 実行ログの両方で確認

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
