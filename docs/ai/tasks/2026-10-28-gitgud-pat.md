# gitgud.io PAT 取得と .env 保存

**Status**: 完了
**Date**: 2026-10-28
**Next Action**: 以降の管理はフォーク版（`S:\Documents\AutoBlog\my-auto-blog-nsfw` / gitgud.io）側へ移行。
本リポジトリ側での残余作業なし。

## 意図 / 背景

- gitgud.io（GitLab Self-Managed 基盤、NSFW 版フォーク先）の Personal Access Token
  を取得し、ローカル `.env`（シークレット専用、gitignore）へ保存する。
- 関連: `docs/ai/tasks/2026-10-23-nsfw-fork-hardcode-audit.md`（GitGud.io 調査）、
  `docs/ai/decisions/2026-10-23-env-secrets-public-management.md`（env 分離方針）。

## 調査結果 / 変更内容

- **PAT の作成はエージェントでは不可能**。GitLab の PAT はユーザー本人のアカウント
  認証（ログイン）後に UI でのみ生成され、値は生成時の一度だけ表示される。
  認証情報を持たないため、代理生成・API 経由の取得は行えない。
- 作成手順（GitLab 標準 UI）:
  1. gitgud.io にログイン
  2. `Personal access tokens`（プロフィール > Access Tokens）を開く
  3. scope: `write_repository`（push 目的）＋必要なら `api`
  4. 有効期限を設定し `Create personal access token` → 表示された値を控える
- gitgud.io は自動フェッチを 403 でブロック（`https://gitgud.io/help`・PAT ペイン
  ともに 403）。バージョン・UI 経路は照合できず、上記は GitLab 標準手順。
- `glab` CLI は未インストール（`docs/ai/tasks/2026-10-28-oct-2026-vuln-inventory.md`）。
- 保存先方針: シークレットは `.env` のみ（`.env.public` には入れない）。
  キー名は `GITGUD_TOKEN` を想定（現行 `.env` は giscus 公開識別子 4 キーのみ）。
- 現行 git remote は `origin` = GitHub のみ。gitgud 向け remote（例 `gitgud`）は未設定。
- **ログイン経路（2026-10-28 実測）**: `https://gitgud.io/users/sign_in` は GitLab 標準
  ユーザー名/パスワードフォームではなく、**Sapphire Accounts の OAuth**
  （`accounts.sapphire.moe/oauth/authenticate?client_id=gitgud`）へリダイレクト。
  認証情報の入力先は Sapphire Accounts 側（Email or Username / Password）。
  初回アクセスは Cloudflare のボットチャレンジで 403（webfetch では継続不可、
  Playwright は約15秒で通過）。

## Verification

- PAT 作成（Playwright）: legacy token、name `kilo-gitgud`、scopes `api` +
  `write_repository`、expires **なし**。
- **UI は期限空白を受け付けない**（空白だと client が today+1 に補完し `2026-10-29` で
  作成された）。server 側は `expires_at: ""`（null）を許可:
  `POST /-/user_settings/personal_access_tokens`（ CSRF token 付き、セッション認証）で
  `expires_at: null` のトークンが作成できる。UI 生 form 経由では不可能。
- 採用トークン: id `20940`（name `kilo-gitgud`、expires null、scopes api+write_repository）
- API 動作確認: `python docs/ai/tmp/gitgud_pat_check.py` → `status: 200`、
  `username: bwdsf3104`（token 値は出力しない）
- `.env` 保存確認: `git check-ignore -v .env` → `.gitignore:17:.env`（非トラッキング）。
  `git status --short` に `.env` 現れず。
- 残存トークン（revoked 前の状態、`GET /api/v4/personal_access_tokens`）:
  `20935`(2027-10-27), `20936`(2026-10-29), `20937`(2026-10-29),
  `20938`(2030-12-31), `20939`(null), `20940`(null・採用)
- 整理（ユーザー承認「一つあれば十分」, 2026-10-28）: 20935〜20939 を revoke 完了。
  active は `20940`（期限なし・api+write_repository）のみ。revoke 後の API 確認: status 200。
- scope 変更要求（read_repository=clone/pull、write_repository=push）: classic PAT は
  作成後の scope 変更不可（Rotate も scope は不変）。値は一度のみ表示。
  → 20940 を revoke し、`20942`（name `kilo-gitgud`、scopes
  `read_repository`+`write_repository`+`api`、expires null）を API 経由で再作成。
  `write_repository` は GitLab 定義上「read-write（Git-over-HTTP）」で clone/pull/push
  に単独で使えるが、read を明示するため read_repository も付与。
- 現行 active トークンは `20942` のみ。`.env` の `GITGUD_TOKEN` を更新。
  再検証: `python docs/ai/tmp/gitgud_pat_check.py` → status 200。
- clone（2026-10-28、push・設定変更なし）: `https://gitgud.io/bwdsf3104/my-auto-blog-nsfw.git`
  → `S:\Documents\AutoBlog\my-auto-blog-nsfw`（既存 GitHub clone と同じ親の隣、独立フォルダ。
  既存 clone へのネストなし）。
  認証: credential helper `docs/ai/tmp/gitgud_cred.py`（+ `.bat` ラッパー）が `.env` を読み、
  PAT をコマンドラインにも remote URL にも埋め込まない。
  初回は GCM の gitgud.io OAuth 試行でハング → `credential.helper=` で chain を空にして
  helper のみで解決。
  clone 先の `.git/config` にトークン・helper 設定なし（`Select-String -Quiet` → False）。
  `HEAD` = `13b9537`、main、origin/main と一致、working tree clean。
- フォーク同期（2026-10-28、ユーザー指示）:
  - `.env` をフォークへコピー（コミット対象外、`.gitignore:17`）。
    `docs/ai/tmp/` は**フォルダのみ**作成（内容 110ファイル/約260MB は未コピー。
    `.gitignore:31 tmp/` でコミット対象外）。
  - インポート（`13b9537`）以降の作成・更新ファイルを local からコピー: 54ファイル。
    共有履歴があるため `git diff --name-status 13b9537 HEAD` + 未コミット分（`current-task.tsv`、
    本タスクファイル）で対象を確定。hash（sha256）一致 0 不一致。
  - rename 9件（tasks → tasks/archive）と `data/topics` の 1件は、フォーク内の旧パスを
    `kilo-safe-remove.cmd`（ゴミ箱）で削除してアーカイブ版をコピー。
  - フォークでコミット: `e5df1ac`（53 files changed）。`.env` / `tmp/` はコミットに含まれない
    ことを `git show --name-only` で確認。push は未実施。

## 保存したキー（.env / gitignore）

- `GITGUD_TOKEN`（PAT）
- `SAPPHIRE_EMAIL` / `SAPPHIRE_PASSWORD`（ユーザー承認済み: ログイン情報も env 保存）

未実施（次の作業）: gitgud 向け remote 追加、`.gitlab-ci.yml` 移行。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
