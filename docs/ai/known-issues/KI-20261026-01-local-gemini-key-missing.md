# ローカル .env に GEMINI_API_KEY（および他シークレット）が存在しない

**Date**: 2026-10-26
**状態**: 未解決（発見元: `2026-10-26-plugin-utf8-minimal` プラグイン最小化の検証中。本タスクは dummy key による検証で完了）

## 確認した事実

- `pytest scripts/tests/` を実行時、`generate_article.py:23` の環境変数存在チェック（`GEMINI_API_KEY` 未設定時 ValueError）により **収集段階で失敗**（テスト実行前に落ちる）。
- 原因: 現在の `S:\Documents\AutoBlog\my-auto-blog\.env` は **公開 Giscus 変数 4 件のみ**（`PUBLIC_GISCUS_CATEGORY`, `PUBLIC_GISCUS_CATEGORY_ID`, `PUBLIC_GISCUS_REPO`, `PUBLIC_GISCUS_REPO_ID`）。
- `GEMINI_API_KEY` は以下のどこにも存在しない:
  - `.env`（gitignore、シークレットのみを想定）
  - user / machine / process 環境変数
  - `.env.public`（**未作成・未トラッキング**）
- `.env.public` は 2026-10-23 方針（`2026-10-23-env-secrets-public-management.md`）で「公開値のみ、トラッキング」を想定していたが、現在不存在。
- 実態: ローカル `.env` から **シークレット系キー（GEMINI_API_KEY 等）が削除された状態**。Giscus 公開変数 4 件だけが残っている（Giscus 外部リポジトリ移行 `2026-10-26` 作業の一環で推測）。

## 影響

- **CI**: 無影響（GitHub Secrets の `GEMINI_API_KEY` を使う。`.env` は CI で存在しない/no-op）。
- **ローカルテスト**: 実鍵を必要としない（`unittest.mock` で全 Gemini 呼出をモック、`AGENTS.md` テストスクリプトルール）。ただし **`generate_article.py` の入口の環境変数存在チェック** が import 時に行われるため、テスト実行前に *値がある* 環境変数が要る。
  - 対応: 検証時は dummy key（`local-test-dummy`）で実行。実 API 呼出は起きない（モック済み）。
- **ローカル本番パイプライン**（`generate_article.py` 実行）: 実鍵がないと実行不能。ローカルでの記事生成は目前できない。

## 対応の方向性（要ユーザー判断）

1. **シークレットの保持場所を再確認**: ローカル `.env` に実鍵を復元するか（セキュリティ上不要なら保持しない方針か）。
2. **`.env.public` の作成**: 2026-10-23 方針どおり公開変数 `.env.public`（トラッキング）を復元/作成し、`.env` との分離を整える。
3. **Giscus 公開変数の所在整理**: `.env` 内の 4 件が `.env.public` に移動すべきか。

## 確認方法

- `.env` のキー: `python docs\ai\tmp\check_env2.py`（値は出さない・有無のみ）
- テスト: `GEMINI_API_KEY=local-test-dummy pytest scripts/tests/ -v` → 454 passed（2026-10-26 検証）
- CI: `.github/workflows/deploy.yml:81`（`GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`）
