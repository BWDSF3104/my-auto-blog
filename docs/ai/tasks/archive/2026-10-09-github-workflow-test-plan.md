# GitHub ワークフロー E2E テスト計画: ジャンル事前スコアリング統合

- 日付: 2026-10-09
- 対象ワークフロー: `Auto Generate Content and Deploy to GitHub Pages`（deploy.yml）
- 対象コミット:
  - `d8d3e7d` feat: Clef-flash ジャンル事前スコアリングを記事生成フローに統合
  - `670051a` test: ジャンル事前スコアリング統合テスト追加
  - `3dc4783` docs: ジャンル事前スコアリング統合のタスク記録
  - `???` fix: deploy.yml に score_topics ステップ追加

## 背景

直近の自動生成（2026-10-09 11:53 JST, run 37876671031）は本統合**以前**のコマ。
`data/genre_scores/topics.json` が存在しないため、現在の生成フローでは
`_append_trending_topics`・`_load_character_features` が従来のランダム選択にフォールバックしている。
deploy.yml に `score_topics` ステップを追加し、E2E で実動作を確認する。

## 基準値（run 37876671031, 2026-10-09 11:53 JST）

| Job | 所要時間 |
|-----|---------|
| generate | ~4m12s（Rakuten API + topics再取得込み） |
| build-and-deploy | ~26s |
| 全体 | ~4m38s |

trend_usage ログ（2026-10-09-115359.json）:
- `total_raw: 71` → `after_score_filter: 71` → `after_rating_filter: 46` → `final_candidates: 2`
- 選択: "Rainbow Six Tactics"（GameSpot RSS）/ "Alien: Isolation 2"（IGN RSS）
- 記事: 暗黒ファンタジー（竜化戦士 × 黒鴉錬金術師、百合）

## 確認項目

### V1: score_topics ステップの正常実行
- **確認方法**: generate job のログで "Pre-score trends (Clef-flash)" ステップの出力を確認
- **成功基準**: `Scored: N topics, M copyrights` / `API calls: X, Cache hits: Y` が出力され、ステップが success
- **関連ファイル**: `.github/workflows/deploy.yml`

### V2: data/genre_scores/topics.json の生成
- **確認方法**: generate job のログで score_topics の出力を確認。`data/genre_scores/` は .gitignore されているためコミットされないが、job 内の generate_article.py が同一 working directory で読む
- **成功基準**: API calls > 0（初回）または Cache hits > 0（2回目以降）
- **関連ファイル**: `scripts/genre_score.py`（`score_topics()`）

### V3: トレンド選択にジャンルフィルタが適用される
- **確認方法**: 生成後の `data/trend_usage/*.json`（最新）を確認。`candidate_pool` に `after_genre_filter` フィールドがあればそれ、なければ `selected` の各アイテムが world_setting のジャンルと関連するものか定性確認
- **成功基準**: world_setting が `fantasy` の場合、選択されたトレンドがファンタジー関連（またはスコア未登録で末尾保持）であること。SF/サイバーパンク系のトレンドが優先されないこと
- **関連ファイル**: `data/trend_usage/*.json`, `scripts/generate_article.py`（`_append_trending_topics`）

### V4: 版権選択にジャンルフィルタが適用される
- **確認方法**: 生成記事の frontmatter + 本文から版権名を確認。`data/character_features.json` の aggregates.copyrights と比較し、world_setting のジャンル適合度が高い版権が優先されているか
- **成功基準**: world_setting が `fantasy` の場合、ファンタジー系版権（例: harry_potter, lord_of_the_rings 等）が優先されるか、少なくともランダム選択と同等以上に関連度が高いこと
- **関連ファイル**: 生成記事 MD, `data/character_features.json`

### V5: 記事生成の正常完了（回帰確認）
- **確認方法**: generate job が success、記事 MD + 画像がコミット済み
- **成功基準**: 記事ファイルが `src/content/posts/` に存在、画像が `public/images/` に存在、frontmatter が有効
- **関連ファイル**: `src/content/posts/2026-10-09-*-auto-post.md`

### V6: build-and-deploy の正常完了（回帰確認）
- **確認方法**: build-and-deploy job が success、GitHub Pages にデプロイ済み
- **成功基準**: `npm run build` 成功、Pages デプロイ完了
- **関連ファイル**: N/A

### V7: 実行時間の妥当性
- **確認方法**: generate job の所要時間を基準値と比較
- **成功基準**: 基準値（~4m12s）+ score_topics 実行時間（119件 × ~1s ≈ 2min）= ~6-7min 以内。大幅超過（10min超）は異常
- **関連ファイル**: `gh run view` の job duration

## 注意事項

- **Clef-flash API**: 無料枠 10,000 neurons/日。119件 × ~700 tokens ≈ 682 neurons（6.8%）。初回は API 呼び出し 119+28=147回、2回目以降はキャッシュヒットで API 0回
- **CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN**: GitHub Secrets に設定済み（genre-score.yml で動作確認済み）
- **score_topics 失敗時**: ステップが fail しても generate job が止まらないよう `continue-on-error` を検討（現状は fail すると job 中断）
- **初回実行**: キャッシュ未作成のため全件 API 呼び出し。所要時間 +2〜3min 増加
