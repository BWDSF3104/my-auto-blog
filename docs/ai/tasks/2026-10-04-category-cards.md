# カテゴリーカード実装

- Date: 2026-10-04
- Status: 進行中
- Backlog: P2 #1

## 概要

フロントページにカテゴリーカードセクションを追加。既存の `tagColors.ts` を再利用して、タグ別記事数のビジュアルカードを表示。

## 実装内容

- `src/components/CategoryCards.astro` 新規作成
- `src/pages/index.astro` にカテゴリーカードセクションを追加
- タグ集計ロジックは既存の `tags/index.astro` と同じパターン

## Status

完了

## Next Action

- (none)

## Verification

- `npm run build`: 成功 (108ページ、4.66s)
- 出力HTML確認: カテゴリーカードセクションが正しくレンダリング (12カード表示)
