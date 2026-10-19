# ZeroGPU quota 残量確認ワークフロー

**Status**: 進行中
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

## Verification

（記入）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
