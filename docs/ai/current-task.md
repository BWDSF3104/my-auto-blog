# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

アフィリエイトリンクのHTML `<a>` タグ化（長いURLの隠蔽）

## Priority

P1

## Status

完了

## Objective

`inject_affiliate_links()` で生成されるアフィリエイトリンクを `[text](long_url)` のMarkdown形式から `<a href="url">text</a>` のHTMLタグに変更。長いUTMパラメータ付きURLを可読ソースから隠蔽する。

既存記事ファイルは修正対象外（known-issues.md にイシューとして保留）。

## Modified Files

- `scripts/generate_article.py` — `inject_affiliate_links()` のリンク生成をMarkdownからHTML `<a>` タグに変更
- `docs/ai/current-task.md` — 状態更新
- `docs/ai/plans.md` — 完了した計画として記録
- `docs/ai/decisions.md` — 設計判断を記録
- `docs/ai/known-issues.md` — 既存記事のリンク形式を保留イシューとして追加

## Completed

- [x] `inject_affiliate_links()` のリンク生成ロジックをHTML `<a>` タグに変更
- [x] `pytest scripts/tests/ -v` 成功確認（85/85, 1.60s）
- [x] `npm run build` 成功確認（82 pages, 2.02s）
- [x] Memory Bank 更新
- [x] git commit & push

## Pending

(なし)

## Verification

- `pytest scripts/tests/ -v`: 85/85 passed, 1.60s
- `npm run build`: 成功（82 pages, 2.02s）

## Next Action

(なし)

## Commit

(Pushed)

## Notes

- 既存記事の `[text](long_url)` 形式は known-issues.md に保留イシューとして記録
