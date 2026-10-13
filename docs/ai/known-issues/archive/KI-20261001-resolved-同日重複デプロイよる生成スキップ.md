# 同日の重複デプロイによる生成スキップ

**Date**: 2026-10-01
**Status**: 解決済

`check_deploy_success()` 関数と `data/.last-deploy-success.json` の記録・チェック処理を削除。同日の成功記録がある場合に記事生成をスキップするロジックは不要と判断。`deploy.yml` からのタイムスタンプ記録ステップも削除。
