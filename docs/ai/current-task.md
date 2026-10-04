# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- P1-2 サイト内検索の再実装 (前回セッション失敗、再実行準備中)

## Completed Task

- P1-3 Analytics (Umami/Plausible) - 完了
- P1-4 Privacy Policy - 完了
- pokemon_super_mystery_dungeon_mew_relationship_verified_vs_theory.md: 記事のフォーマット・画像配置・ビルド検証 **完了**

### 完了内容
- P1-3: アクセス解析統合
- P1-4: Privacy Policy ページ
- 記事画像ダウンロード・変換・配置

## Failed Task

- P1-2 サイト内検索 (初回): Astro 7 content collections API に適合できず失敗。詳細:
  - `astro:content` の `getCollection()` を `astro.config.mjs` で直接インポート → ロードタイミングエラー
  - integration に移動後も Vite の `closeBundle` が既にクローズされている
  - `astro:content_loader` は存在しないモジュール
  - `astro/loaders` を試したが、content config の `type: 'content'` が legacy プロパティでエラー
  - Astro 7 型定義を繰り返し読み込み、API 探索ループに陥りセッション切断
  - 残骸: `src/lib/search-index.ts`, `src/lib/search-index-plugin.ts`, `src/lib/search-index-integration.ts`, `src/content.config.ts`

## Verification

- `pytest scripts/tests/ -v`: 134 passed in 1.93s
- `npm run build`: 104 page(s) built in 3.01s, Completed (前回成功時)

## Changes

- 前回のP1-2失敗で以下が作成・変更された可能性がある（要確認・クリーンアップ）:
  - `astro.config.mjs`
  - `src/content.config.ts`
  - `src/content/config.ts`
  - `src/lib/search-index.ts`
  - `src/lib/search-index-plugin.ts`
  - `src/lib/search-index-integration.ts`
  - `src/pages/search.astro`
  - `src/components/Header.astro`

## Relevant Files

- `docs/ai/current-task.md`: 進捗追跡ファイル
- `docs/ai/backlog.md`: バックログ
