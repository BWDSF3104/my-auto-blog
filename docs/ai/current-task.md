# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

ワークフローの Secrets 未接続修正

## Priority

P1

## Status

完了

## Objective

`AMAZON_TRACKING_ID` と `RAKUTEN_AFFILIATE_ID` は Repository Secrets に登録されていたが、`deploy.yml` の `env:` で参照されていなかったため、CI 実行時にデフォルトのプレースホルダー値（`your-amazon-tag-22`, `your-rakuten-id`）が使われていた。`generate_article.py` ステップの `env:` に Secrets 参照を追加。

## Modified Files

- `.github/workflows/deploy.yml` — `Run generation script` ステップの `env:` に `AMAZON_TRACKING_ID` と `RAKUTEN_AFFILIATE_ID` を追加
- `docs/ai/plans.md` — Active Plans に修正計画を記録

## Completed

- [x] 現状確認: Secrets 登録状況とワークフローの env ブロックを比較
- [x] plans.md に修正計画を記録
- [x] deploy.yml の `Run generation script` ステップに Secrets 参照を追加
- [x] 変更内容の検証

## Pending

(なし)

## Verification

deploy.yml の env ブロックに 5 つの環境変数が正しく設定されていることを確認済み。

## Next Action

(なし)

## Commit

(未コミット)

## Notes

- `fetch_topics.py` はアフィリエイト ID を使用しないため、`Fetch trending topics` ステップへの追加は不要
- `Record deploy success timestamp` ステップもアフィリエイト ID を使用しないため変更不要
- 次の CI 実行から記事に正しいアフィリエイトタグが埋め込まれる
