# python-dotenv Adoption

**Date**: 2026-09-29

**Decision**: Use `python-dotenv` for environment variable management in scripts.

**Reason**: Scripts need API keys and configuration from `.env` file. `python-dotenv` provides reliable `.env` loading with fallback to system environment variables.

**Rejected Alternatives**:
- `os.environ` のみ: `.env`ファイルの自動読み込みが不可能
- 設定ファイル (YAML/JSON): 機密情報をリポジトリにコミットするリスク
