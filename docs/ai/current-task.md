# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

キャラクター・テーマ被り防止の改善（デプロイ成功タイムスタンプ記録 + フロントマッター被り検出）

## Priority

P1

## Status

完了

## Objective

AI生成ブログ記事でキャラクターやテーマが被る問題を2つの改修で改善する:
1. デプロイ成功後にのみ生成完了タイムスタンプを記録（同日の成功記録があれば再生成をスキップ）
2. キャラクター被り検出をタイトルのみから frontmatter 全体（character_1, character_2, tags, art_style）に拡張

## Requirements

- デプロイ成功後に `data/.last-deploy-success.json` を記録
- 生成開始時に同日の成功記録があれば `sys.exit(0)` でスキップ
- 直近記事の frontmatter からキャラクター・タグ・アートスタイルを抽出
- 抽出したメタデータを NG 指示ブロックに注入して LLM に被り防止を指示

## Modified Files

- `.github/workflows/deploy.yml` - デプロイ成功後にタイムスタンプ記録ステップ追加
- `scripts/generate_article.py` - `check_deploy_success()` 関数追加、`get_recent_meta_by_type()` 関数追加、NG 指示ブロック強化
- `docs/ai/current-task.md`
- `docs/ai/plans.md`
- `docs/ai/decisions.md`

## Completed

- [x] 現状調査：generate_article.py の被り検出ロジックとワークフローを確認
- [x] 改修プランを docs/ai/plans.md に記録
- [x] 実装1: デプロイ成功後にのみ生成完了タイムスタンプを記録
  - [x] deploy.yml にデプロイ成功記録ステップ追加
  - [x] check_deploy_success() 関数実装
  - [x] generate_post() 冒頭にチェック追加
- [x] 実装2: キャラクター被り検出を frontmatter 全体に拡張
  - [x] get_recent_meta_by_type() 関数実装
  - [x] NG 指示ブロックにキャラクター・タグ・アートスタイルの被り防止指示を追加
- [x] テスト検証: 85 tests passed
- [x] ビルド検証: Astro build succeeded (81 pages)
- [x] docs/ai/ 更新

## Pending

(なし)

## Verification

Build: Astro build succeeded (81 pages, 2.14s)
Test: 85 tests passed in 1.19s

## Next Action

(なし)

## Commit

5f04f0a

## Notes

- f-string 内でバックスラッシュが使えないため、join 操作を別変数に抽出して対応
- デプロイ失敗時の rollback は不要と判断（git履歴のクリーンさより簡潔さを優先）
