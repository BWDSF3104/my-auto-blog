# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

`kemono_story` ワークフローの改善：印象的なシーンの必須化と画像シーン選出の最適化

## Priority

P1

## Status

完了

## Objective

`kemono_story` ワークフローの改善：ストーリー中にキス・ハグ・密着・激しいバトルなどの印象的なシーンを必須化し、画像生成対象のシーン選出（トップ画像 `image_prompt` と記事中 `IMAGE_PROMPT`）を視覚的にインパクトのあるものへ最適化する。

## Modified Files

- `scripts/prompts/kemono_story.txt` — 印象的なシーンの必須条件（条件8）を追加、画像シーン選出ルールを3枚の役割分担に強化
- `scripts/prompts/refine_story.txt` — クライマックス・余韻セクションに印象的なシーンの弱化防止チェックを追加

## Completed

- [x] `kemono_story.txt` に「印象的なシーン」の必須条件（条件8）を追加
- [x] `kemono_story.txt` の画像シーン選出ルールを3枚の役割分担に強化
- [x] `refine_story.txt` に印象的なシーンの弱化防止チェックを追加
- [x] `pytest scripts/tests/ -v` 成功確認（85/85, 1.58s）
- [x] `npm run build` 成功確認（83 pages, 5.35s）

## Pending

(なし)

## Verification

- `pytest scripts/tests/ -v`: 85/85 passed, 1.58s
- `npm run build`: 成功（83 pages, 5.35s）

## Next Action

(なし)

## Commit

(未コミット)

## Notes

- SFW制約は厳守
- トップ画像 (`image_prompt`) と記事中画像 (`IMAGE_PROMPT` x2) で異なる瞬間を選出するよう指示
- 3枚で物語の異なる感情・場面をカバーするよう選出基準を分離
