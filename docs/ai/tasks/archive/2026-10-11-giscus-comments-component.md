# 2026-10-11: コメント機能（Giscus）— コンポーネント実装と Layout 組み込み

**Status**: 未着手
**担当**: AI
**依存**: なし（`env-config` 未完でも env 欠落時に early return するため build は壊れない）
**関連**: `tasks/2026-10-11-giscus-comments-verification.md`（最終検証）

## 概要

`src/components/GiscusComments.astro` を新規作成し、`PostLayout.astro` に組み込む。表示位置は記事末尾（Social Sharing セクションの直後）。

## 設計

### `src/components/GiscusComments.astro`（新規）

- frontmatter で `import.meta.env.PUBLIC_GISCUS_REPO` / `PUBLIC_GISCUS_REPO_ID` / `PUBLIC_GISCUS_CATEGORY` / `PUBLIC_GISCUS_CATEGORY_ID` を読取、**いずれか欠落時は frontmatter の early return でセクションごと描画しない**（未設定環境で build が壊れない・現状維持）
- 設定値が揃っている場合の描画:
  - `<section id="comments">`（既存セクションと同じ `mt-10 pt-6 border-t` スタイル）
  - 見出し「コメント」+ GitHub 認証が必要な旨の注記（giscus app の認可、Discussion への投稿であること）
  - giscus client script タグ（`https://giscus.app/client.js`、`crossorigin="anonymous" async`）:
    - `data-repo` / `data-repo-id` / `data-category` / `data-category-id`: env 値
    - `data-mapping="pathname"` / `data-strict="0"`
    - `data-reactions-enabled="1"` / `data-emit-metadata="0"` / `data-input-position="bottom"`
    - `data-lang="ja"` / `data-loading="lazy"`（LCP への影響を回避）
    - `data-theme`: 初期値は現在のサイトテーマ
- **テーマ同期**: サイトのダークモード切替は `Header.astro` の `toggleDark()` が `documentElement` の class を操作するのみでイベントを発火しない。そのため本コンポーネント内に `<script is:inline>` を置き、`MutationObserver` で `document.documentElement` の `class` 変化を監視し、giscus script の `data-theme` を `light` / `dark` に更新する（giscus client は `data-theme` 属性の変化を監視して再描画するため、ロード前後いずれでも有効）。`Header.astro` への変更は不要

### `src/layouts/PostLayout.astro`（修正）

- `import GiscusComments from '../components/GiscusComments.astro';`
- Social Sharing セクション直後に `{frontmatter.comments !== false && <GiscusComments />}`
- Props interface に `comments?: boolean;` を追加

### `src/content.config.ts`（修正）

- schema に `comments: z.boolean().optional(),` を追加（`.passthrough()` 済みだが型定義として明記）
- 記事単位での無効化: frontmatter に `comments: false` を付けるとコメント欄を非表示

## pathname mapping の注意点

- `astro.config.mjs` の `base: '/my-auto-blog'` により、本番（`https://BWDSF3104.github.io/my-auto-blog/posts/<slug>`）とローカル開発の pathname が一致するため、開発中に作成した Discussion と本番が同一になる
- slug リネーム（`data/slug-redirects.json`）時は新 pathname で新規 Discussion になり、旧コメントは引き継がれない（既知のトレードオフ、`decisions.md` 2026-10-11 参照）

## Verification

- `npm run build` 成功（env 未設定時はコメント欄なしで build できること・env 設定時は script タグ出力）
- 出力 HTML を解析して giscus script タグの `data-*` 属性が正しく埋まっていることを確認
- `comments: false` の一時記事でセクション非表示を確認（確認後削除し再 build）
- 実際のウィジェット表示確認は `verification` タスク（env 値 + ネットワーク必要）

## Next Action

- `workflow-env` タスク（CI 配線）を並行実施、完了後は `verification` タスクへ
