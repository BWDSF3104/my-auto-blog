# Cloudflare Pages 対応 (NSFW版、コミットなしデプロイ)

**Status**: 完了
**Date**: 2026-10-23
**Next Action**: 推奨案 (CI生成→build→wrangler deploy) をユーザーに報告・合意

## 意図 / 背景

前タスク「NSFWフォーク移行準備: ハードコード部分的抽出調査」
(`2026-10-23-nsfw-fork-hardcode-audit.md`, 完了・方針変更によりクローズ) の継続。

ユーザー方針変更 (2026-10-23):
1. **プロジェクトのフォークはしない**（フォーク方式は廃止）
2. **GitHub Pages → 既存維持**（SFW版。記事・画像はコミット、既存パイプライン不変）
3. **Cloudflare Pages → 新規追加**（NSFW版。**NSFW コンテンツはコミットしない**）

本タスク: この「同一リポジトリ・2 デプロイ」方式の調査・検討・報告。
実装はユーザー合意後。

## 調査結果 / 変更内容

### 現行アーキテクチャ（実コード確認済み）

| 項目 | 現状 |
|---|------|
| SFW パイプライン | `deploy.yml`（cron JST 23:00 / workflow_dispatch）: fetch → 記事生成 → **コミット+プッシュ** → `npm run build` → GH Pages デプロイ |
| SFW ビルド専用 | `deploy-only.yml`: checkout → build → GH Pages（生成・コミットなし） |
| 記事出力 | `scripts/generate_article.py:504` `output_dir = "src/content/posts"`（ハードコード）。**スクリプト自体は git 操作しない**（コミットはワークフローの別ステップ: deploy.yml L94-124） |
| 画像出力 | `public/images/` |
| Astro `site`/`base` | `astro.config.mjs`: `SITE_ORIGIN` / `SITE_BASE_PATH` env 駆動 → **デプロイごとに値を変えてよい** |
| コンテンツ集 | `src/content.config.ts`: `glob({ pattern: '**/*.md', base: 'src/content/posts' })` → **ワークスペースの `src/content/posts` 内はすべてビルドに含む** |
| ビルド | `npm run build` = `generate-search-index.js` + `astro build` |
| CF 認証 | `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` が `.env` に既存（Workers AI スコアリング用）。Pages 用スコープは要確認 |

### 制約

- リポジトリはパブリック（GH Pages 源）→ **NSFW 関連（コンテンツも設定値も）は Git に入れない**
- NSFW コンテンツは「生成 → 部署」の間だけ**一過性のワークスペース**に置く
- NSFW 用プロンプト・ratings 値 → CI では **GitHub Secrets**、ローカルでは `.env`（gitignore、ローカルのみ）。`.env.public` には入れない

### 候補案

| 案 | 内容 | 判定 |
|---|---|---|
| **A** | **CI ジョブ** (`workflow_dispatch`): fetch → 記事生成(NSFW env, secrets) → build → `wrangler pages deploy dist` | **推奨** |
| B | ローカル生成（ローカル `.env` に NSFW 値）→ ローカル `wrangler pages deploy dist` | 代替/デバッグ用。ローカル wrangler 要 |
| C | CF Pages の GitHub リポ連携デプロイ | **不可**（NSFW はコミットしないため） |
| D | NSFW コンテンツをコミットして CI でデプロイ | **制約違反** |

### 推奨案 A: パイプライン設計

新規 `.github/workflows/cf-nsfw.yml`:

```
on: workflow_dispatch（cron 追加は後で）
permissions: contents: read（コミットしないため write 不要）
jobs:
  deploy:
    1. checkout (fetch-depth: 0)
    2. node 22 / npm ci
    3. python scripts/fetch_topics.py
       env: E621_ALLOWED_RATINGS=s,q,e, E621_NSFW_RATINGS="",
            GEMINI_API_KEY, HF_TOKEN, RAKUTEN_*, AMAZON_TRACKING_ID, PROMPT_TYPE=kemono_story
    4. python scripts/generate_article.py
       env: BASE_QUALITY_PROMPT=${{ secrets.NSFW_BASE_QUALITY_PROMPT }},
            NEGATIVE_PROMPT=${{ secrets.NSFW_NEGATIVE_PROMPT }},
            (IMAGE_PROVIDER, IMAGE_FALLBACK_URL_TEMPLATE, ZERO_GPU_* は現行値)
    5. npm run build
       env: SITE_ORIGIN=<CF サイトの origin>, SITE_BASE_PATH=/
    6. npx wrangler pages deploy dist
       --project-name nsfw-blog --api-token ${{ secrets.CLOUDFLARE_API_TOKEN }} --region <region>
```

- **コミットステップなし** → NSFW 記事・画像は一過性の CI ワークスペース内に留まり、**Git に永不**
- `dist/` には SFW（コミット済み）+ NSFW（ワークスペース）を含む
- 既存 `deploy.yml` / `deploy-only.yml` は変更不要（パスフィルタにより相互干渉なし）

### CF サイトの内容

- **デフォルト: SFW + NSFW**（ワークスペースの `posts` 全体がビルドに含む → 追加コードなし）
- **NSFW のみ**: 別コンテンツディレクトリ + 別 collection への変更が必要（追加作業）

### 初回セットアップ（ユーザー実行）

1. Cloudflare Pages プロジェクト作成（例 `nsfw-blog`）
2. `CLOUDFLARE_API_TOKEN` のスコープに `pages:read` / `pages:edit` 追加（現行は Workers AI 用途）
3. 新しい Secrets 追加:
   - `NSFW_BASE_QUALITY_PROMPT`（"safe for work" 等除去済みプロンプト）
   - `NSFW_NEGATIVE_PROMPT`（"nsfw, human" 除去済み）
   - `NSFW_E621_ALLOWED_RATINGS` = `s,q,e`
   - `NSFW_E621_NSFW_RATINGS` = （空 or `q`）
4. CF サイトの origin を決める（カスタムドメイン or `*.pages.dev`）
5. （任意）GSC: CF サイトは別プロパティ。現行 `gsc_index.py` は GH ドメイン用のみ

### コード変更範囲

| ファイル | 変更 |
|---|------|
| `.github/workflows/cf-nsfw.yml` | **新規作成**（約 80 行） |
| `astro.config.mjs` | 不変（site/base は env 駆動済み） |
| `scripts/`（Python） | 不変（出力は相対パス、スクリプト内コミットなし） |
| `src/content.config.ts` | 不変（`src/content/posts` の glob でワークスペース記事も網羅） |
| `.env.public` | 不変（NSFW 値はコミットしない） |
| `.env`（ローカル） | 案 B 採用時のみ NSFW 値追加（gitignore 維持） |

### 未決事項

1. CF サイト: **SFW+NSFW**（推奨・コード不変）or **NSFWのみ**（追加変更要）
2. トIGGER: 手動（`workflow_dispatch`）のみ or cron（例 JST 8:30）
3. NSFW 値: Secrets（推奨）or プレインリポジトリ変数（値が公開になる）
4. API アccount: SFW と共用（レート制限・コストは増幅）か

## Verification

実装時:
- `pytest scripts/tests/ -v`（Python 変更があれば全テスト）
- 現行値での `npm run build`（SFW 現行動作不変）
- サandbox CF プロジェクトでの `npm run build` + `wrangler pages deploy` 実演
  → 公開サイトで SFW+NSFW 確認
- `git log` / `git status` で NSFW 記事・画像がコミットされていないこと
- GSC / sitemap / search index（`generate-search-index.js`）が NSFW 記事を含むこと

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
