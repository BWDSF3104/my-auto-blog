# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- `docs/ai/tasks/2026-10-08-rakuten-affiliate-api.md` - 楽天市場API商品リンク連携。**設計・API検証・デザイン確認完了、実装未着手** (2026-10-08)
  - 次: `generate_article.py` 実装（`_rakuten_search` + 3関数改造 + テスト + `deploy.yml` 更新）→ pytest + build 検証

### 過去の記録

- `docs/ai/tasks/2026-10-07-generation-pipeline-fixes.md` - 生成パイプライン修正 #1, #3, #5, #6, #7, #8 完了 (2026-10-07)
- `docs/ai/tasks/2026-10-07-trend-usage-log.md` - #8 trend_usageログ欠落修正 完了 (2026-10-07)
- `docs/ai/tasks/2026-10-07-affiliate-keyword-investigation.md` - #7 アフィリエイトキーワード調査・修正 完了 (2026-10-07)
- `docs/ai/tasks/2026-10-06-draft-metadata-tracking.md` - 2-pass生成のメタデータ追跡
- `docs/ai/tasks/2026-10-05-known-issues-image-prompt.md` - KI-001, KI-002 修正完了
- `docs/ai/tasks/2026-10-05-hf-api-investigation.md` - HF ZeroGPU 調査
- `docs/ai/tasks/2026-10-06-increase-image-count.md` - 画像生成上限3→8枚
- P2バックログ完了: ロゴ画像置換, ブランドカラー統一, モバイルハンバーガーメニュー, ヒーローセクション, カテゴリーカード
- P1バックログ完了: TOCレスポンシブ対応 + Plausible有効化, HF API 使用可能状況確認
- KI-003 長プロンプト対応v2（自前chunking実装成功）
- 画像プロンプト精査: Danbooru互換形式統一, seed制御, artistタグ集計
