# コメント機能設計（Giscus + 外部リポジトリ）

**Status**: 進行中（外部セットアップ・実装完了。残: E2E 検証＋本番デプロイ）
**Date**: 2026-10-26
**Backlog**: P2 #4
**Next Action**: コミット・プッシュ・本番デプロイ（E2E 検証）

## 意図 / 背景

ユーザー依頼: コメント機能の**設計**（実装は要指示）。
制約: **コメント用リポジトリは本プロジェクトフォルダ外（本リポ `BWDSF3104/my-auto-blog` とは別）に作成する。作成箇所（リポジトリ名・所在）は要確認。**

2026-10-11 の Giscus 設計（`decisions/2026-10-11-giscus-comments.md`）は、コメントバックエンド = 本ブログリポジトリ自体（Discussions を本リポに有効化）を想定していた。本タスクはその設計を**コメント専用リポジトリ**へ改変する。Giscus 自体（クライアントサイド widget）は維持する。

## 調査結果 / 変更内容（設計）

### 1. 选型: Giscus（2026-10-11 決定を維持）

- 採用: **Giscus**（クライアントサイドの script ウィジェット、`https://giscus.app/client.js`）。
- バックエンド: **GitHub Discussions**。
- 選択根拠（既定）: 静的サイト + バックエンド/DB/SSR なしと整合。無料・広告なし・スパム抑制（GitHub OAuth 必須）で AI 自動生成記事に有効。セルフホスト型は常時稼働サーバーが必要で設計と矛盾。

### 2. 変更点: コメント用リポジトリ = 外部専用リポジトリ

- コメントバックエンドは **本ブログリポ `BWDSF3104/my-auto-blog` ではなく**、**新しい公開 GitHub リポジトリ**（コメント専用）にする。
- 理由:
  - 分離: ブロックソースとコメント保存を独立管理。
  - 将来の複数サイト対応: 別サイトも同一コメントリポを参照可能（共有 pool の前提）。
  - コメントリポは軽量（コード・CI なし。Discussions + giscus app のみ）。
- **リポジトリ名・所在は要確認**（次节的）。候補は「#4 候補」を参照。

### 3. アーキテクチャ（データフロー）

```
[ブログ 静的サイト (GitHub Pages, /my-auto-blog)]
  │  GiscusComments.astro が script タグを出力
  │  (data-repo / data-repo-id → コメント用リポ)
  ▼
[ブラウザ: Giscus client.js]
  │  location.pathname を読み、GitHub GraphQL API で
  │  該当 Discussion を特定
  ▼
[コメント用リポジトリ (GitHub, 公開)]
  - リポジトリ: TBD（要確認）
  - カテゴリ: "Comments"
  - giscus app 導入済み（初回コメントで Discussion を自動作成）
  - 記事ごとの Discussion（タイトルが pathname を含む）
```

### 4. コメント用リポジトリの作成（手動・ユーザー）

1. 新規 **公開** GitHub リポジトリ `BWDSF3104/giscus-comments` を作成（**ユーザー選択: 2026-10-26**）。
2. Settings → General → Features で **Discussions を有効化**。
3. Discussions にカテゴリ「**Comments**」を作成。
4. https://giscus.app/ のウィザードを実行（Repository=新規リポ / Category=Comments / mapping=`pathname`）。
   - giscus app がリポにインストールされ、`<script>` タグが生成される。
5. 生成 script から **`repo_id`（`R_...`）と `category_id`（`DIC_...`）** を抽出。

### 5. 設定値（環境変数 4 値）

| 変数 | 値 | 備考 |
|---|---|---|
| `PUBLIC_GISCUS_REPO` | `<owner>/<コメント用リポ>` | **`BWDSF3104/giscus-comments`**（確認済み） |
| `PUBLIC_GISCUS_REPO_ID` | `R_...` | `R_kgDOVXdXKA`（giscus.app ウィザード＋gh api で取得・確認） |
| `PUBLIC_GISCUS_CATEGORY` | `Comments` | `Comments`（カテゴリ名） |
| `PUBLIC_GISCUS_CATEGORY_ID` | `DIC_...` | `DIC_kwDOVXdXKM4DJoNP`（giscus.app ウィザード＋gh api で取得・確認） |

- **登録先**: ローカル `.env` ＋ **ブログリポ**（`BWDSF3104/my-auto-blog`）の GitHub Actions **Repository Variables**。
  - 理由: build 作業はブログリポの CI（`deploy.yml`）で行うため。
  - 4 値は非機密の公開識別子（生成 HTML に埋め込まれる）→ `vars.*`（`deploy.yml` が `SITE_BASE_PATH` 等で既に使用）。
  - **[2026-10-26 完了]** GitHub Actions **Repository Variables に 4 値を gh で登録済み**（`gh api -X POST /repos/BWDSF3104/my-auto-blog/actions/variables`）。ローカル `.env` は実装段階で登録。

### 6. フロントエンド実装

**新規: `src/components/GiscusComments.astro`**
- frontmatter で 4 環境変数を read。
- **欠落時の early return（空）** → 非表示・build 壊さない（未設定環境で現行維持）。
- 揃った場合の描画:
  - `<section id="comments">`（既存セクションと同等の `mt-10 pt-6 border-t` スタイル）。
  - 見出し「コメント」+ 注記（GitHub 認証が必要。コメントは GitHub Discussions へ投稿）。
  - Giscus script タグ（`https://giscus.app/client.js`、`crossorigin="anonymous" async`）:
    - `data-repo` / `data-repo-id` / `data-category` / `data-category-id`: 環境変数値
    - `data-mapping="pathname"` / `data-strict="0"`
    - `data-reactions-enabled="1"` / `data-emit-metadata="0"` / `data-input-position="bottom"`
    - `data-lang="ja"` / `data-loading="lazy"`（LCP 影響回避）
- **テーマ同期**: `<script is:inline>` に MutationObserver を配置。`document.documentElement` の `class` 変化を監視し、giscus script の `data-theme` を `light` / `dark` に更新（giscus client は `data-theme` 変化を監視して再描画。ロード前後いずれでも有効）。`Header.astro` は変更しない。

**修正: `src/layouts/PostLayout.astro`**
- `import GiscusComments from '../components/GiscusComments.astro';`
- Social Sharing セクションの**直後**に `{ frontmatter.comments !== false && <GiscusComments /> }`
- Props interface に `comments?: boolean;` を追加。

**修正: `src/content.config.ts`**
- schema に `comments: z.boolean().optional(),` を追加（`.passthrough()` 済みだが型定義として明記）。
- 記事単位無効化: frontmatter に `comments: false` を付けると非表示。

### 7. 記事ごとのコメント管理

- **1 記事 = 1 Discussion**（`data-mapping="pathname"`）。
  - 鍵: `location.pathname` = `/my-auto-blog/posts/<slug>`（**base パスを含む**）。
  - Discussion タイトルに当該 pathname を含む。
  - giscus bot が**初回コメント時に Discussion を自動作成**。
- **保存先**: GitHub Discussion スレッド（本文＋返信）。**DB なし**。
- **描画**: Giscus client が GitHub GraphQL API で取得 → クライアントサイドでレンダリング（lazy load）。
- **記事単位無効化**: `comments: false`。
- **注意**: slug をリネームすると**新しい Discussion** が生成され、**旧コメントは継承されない**（設計上のトレードオフ）。

### 8. 複数サイト対応（将来・任意）

- コメント用リポは 1 つ。将来の別サイトも同一リポを参照可能。
- `data-mapping="pathname"` は**ドメイン非依存**（パスのみで判定）。
  - 両サイトの pathname 値が**一致** → 同一 Discussion → コメント**共用**。
  - base が異なる（`/my-auto-blog` vs 別 base）→ pathname 不一致 → コメント**分離**。
- 別 base のサイト間でもコメントを**共用**したい場合は `data-mapping="title"`（記事タイトルで鍵）が実用的（各サイトの記事タイトルが共通なら共用可能）。
- 本タスクの当面は本サイト単独で `pathname` 運用。

### 9. タスク分解（実施時）

| # | 内容 | 実施 | ステータス |
|---|---|---|---|
| 1 | コメント用リポ **`BWDSF3104/giscus-comments`** 作成 + Discussions 有効化 + カテゴリ「Comments」作成 + **giscus GitHub App 導入** + Giscus ウィザード（**ローカルファイル不要**） | Playwright（GitHub UI） | **完了**（repo `R_kgDOVXdXKA` / cat `DIC_kwDOVXdXKM4DJoNP`） |
| 2 | 4 環境変数登録（ローカル `.env` + ブロックリポ Actions Variables） | **gh**（Actions Variables）/ 手動（`.env`） | **Actions Variables 完了**；`.env` 待た |
| 3 | `GiscusComments.astro` 新規 + `PostLayout.astro` + `content.config.ts` 修正 | AI | **完了**（2026-10-26） |
| 4 | `deploy.yml` / `deploy-only.yml` への env 配線（`vars.PUBLIC_GISCUS_*`） | AI | **完了**（2026-10-26） |
| 5 | E2E 検証（本番: 記事ページでコメントウィジェット表示 → GitHub ログイン → 投稿 → 表示） | AI | 未着手 |

### 10. 制約・トレードオフ

- Giscus は**公開リポジトリ**を要求（コメント用リポも公開に要する）。
- コメントは**公開**に露出される（公開リポの Discussions）。
- コメント投稿は**GitHub 認証必須**（匿名コメント不可）。
- コメント用リポの**削除・リネーム**でコメントは**失われる（復元不可）** → 運用注意。
- slug リネーム → コメント非継承。
- コメント用リポにコード・CI・**必須ファイル** は不要（Discussions + giscus app のみ）。**ローカルクローン・ローカルファイルも不要**（コメント本体は GitHub 上に保存）。
- 環境変数は**ブロックリポ**の CI に登録する（コメントリポ側ではない）。

## コメント用リポジトリの作成先（確認済み: 2026-10-26）

- **リポジトリ名**: `BWDSF3104/giscus-comments`（ユーザー選択）。Giscus 慣行の汎用名・将来の複数サイト共用に強い。
- **ローカルファイル**: **不要**。
  - コメントリポは **GitHub Discussions の容器のみ**（コード・CI・必須ファイルなし）。
  - 設定（Discussions 有効化・カテゴリ「Comments」・giscus app 導入）は **GitHub UI / リポジトリ設定** で実行（ファイル非依存）。
  - コメント本体（Discussion スレッド）は **GitHub 上**に保存（リポジトリのファイルではない）。
  - したがって **ローカルクローンは不要**。リポジトリ README 等の管理目的の編集が将来的に必要になるまで、ローカルディレクトリは作成しない。

| 候補（参考） | リポジトリ | 利点 | 注意点 |
|---|---|---|---|
| A | `BWDSF3104/my-auto-blog-comments` | 本ブログ専用・目的明示 | 複数サイト共用に名称が特化 |
| B (選択) | `BWDSF3104/giscus-comments` | 汎用名・複数サイト共用に強い | 本ブログ専用が名称から不顕明 |
| C | 別 owner/org | 複数プロジェクト/サイトで共有 | 管理コスト増加 |

## Verification（実施時）

- [x] `npm run build`（2026-10-26、ローカル、`PUBLIC_GISCUS_*` 設定時）: **成功**（163 pages / 約5s、エラーなし）。
- [x] 出力 HTML 解析（`dist/posts/zankyou-no-duplica/index.html`）: giscus script タグの `data-*` が正しいことを確認。
  - `data-repo="BWDSF3104/giscus-comments"` / `data-repo-id="R_kgDOVXdXKA"` / `data-category="Comments"` / `data-category-id="DIC_kwDOVXdXKM4DJoNP"` / `data-mapping="pathname"`。
- [ ] 一時記事で `comments: false` → セction 非表示を確認（確認後削除し再 build）。
- [ ] 本番: 記事ページでコメントウィジェット表示 → GitHub ログイン → 投稿 → 表示を確認。

## 実施記録（外部セットアップ: 2026-10-26）

- **giscus-comments リポ作成**（公開）+ **Discussions 有効化** + カテゴリ「**Comments**」作成 → Playwright（GitHub UI）。
- **giscus GitHub App 導入** → Playwright（org 全リポ、write: discussions 権限）。
- **giscus.app ウィザード実行**（Repository=`BWDSF3104/giscus-comments` / Category=Comments / mapping=`pathname`）で設定値取得:
  - `data-repo-id` = `R_kgDOVXdXKA`
  - `data-category-id` = `DIC_kwDOVXdXKM4DJoNP`
- **4 環境変数を GitHub Actions Repository Variables に gh で登録完了**:
  - `gh api -X POST /repos/BWDSF3104/my-auto-blog/actions/variables -f name=... -f value=...`
  - `PUBLIC_GISCUS_REPO` / `PUBLIC_GISCUS_REPO_ID` / `PUBLIC_GISCUS_CATEGORY` / `PUBLIC_GISCUS_CATEGORY_ID`。
  - 確認: `gh api /repos/BWDSF3104/my-auto-blog/actions/variables`（8 変数: 既存4 ＋ 新規4）。

### gh 権限の記録（ユーザー質問への回答）
- **gh で可能**（かつ今回のトークンで実際に実行済み）。初回 404 は **endpoint 誤用**が原因:
  - 誤: `gh api -X POST /repos/.../variables/actions`（404）
  - 正: `gh api -X POST /repos/.../actions/variables`（201 Created）
- **必要権限**（この endpoint）:
  - fine-grained トークン: **「Variables」→ Read and write**（`actions_variables=read+write`）。classic: **`repo`** スコープ。
  - 現在の gh トークンは両方（`actions_variables=read`＋`write`）を保持 → **追加権限不要**。
- **gh で不可**: **giscus GitHub App 導入**（GitHub App の OAuth 承認＝ユーザー合意が必須）→ ブラウザ（Playwright）必須。これが唯一の Playwright 固有ステップ。

### フロントエンド実装（2026-10-26、ユーザー「開始」指示）

- **新規** `src/components/GiscusComments.astro`:
  - 4 環境変数（`import.meta.env.PUBLIC_GISCUS_REPO` 等）を read、欠落時は早期 return（空・build 安全）。
  - `<section id="comments">`＋見出し「コメント」＋GitHub 認証注記＋giscus `<script id="giscus-script">`（`data-mapping="pathname"` 等）＋`<script is:inline>` の MutationObserver（`<html>` の `dark` クラス監視 → `data-theme` を `light`/`dark` に同期）。
- **修正** `src/layouts/PostLayout.astro`:
  - import 追加。Props に `comments?: boolean;` 追加。Social Sharing の直後に `{ frontmatter.comments !== false && <GiscusComments /> }`。
- **修正** `src/content.config.ts`:
  - schema に `comments: z.boolean().optional(),` 追加。
- **修正** `.github/workflows/deploy.yml` / `deploy-only.yml`:
  - "Build Astro site" の `env:` に 4 個の `PUBLIC_GISCUS_*`（`${{ vars.PUBLIC_GISCUS_* }}`）追加。
- **新規** `.env`（gitignore 対象・ローカル build 用）に 4 値登録。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の #4 を「設計更新」反映 or 完了時に削除
