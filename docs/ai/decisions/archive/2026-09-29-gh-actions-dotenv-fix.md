# GH Actions dotenv Fix

**Date**: 2026-09-29

**Decision**: Install `python-dotenv` in GitHub Actions workflow.

**Reason**: Scripts failed in CI because `python-dotenv` was not installed in the Actions environment.

**Rejected Alternatives**:
- Actionsで.envファイルをコミット: 機密情報の漏洩リスク
- 環境変数の手動設定のみ: ローカル開発とCIの設定が分かれる
