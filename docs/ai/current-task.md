# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- `docs/ai/tasks/2026-10-08-rakuten-affiliate-api.md` - 楽天市場API商品リンク連携。**実装完了・検証済み** (2026-10-08)
  - 修正案 (2026-10-08): 絵文字カードは**維持**（置き換え✗ 廃止✗）= 楽天API商品カードの「追加」のみ。A系本文内はプレーンテキスト化済み
  - **実装内容**: `generate_article.py` に `_rakuten_search`（30日キャッシュ/429リトライ/呼び出し間隔1.5秒/画像付き先頭採用）+ `_generate_rakuten_card`（実画像付き `.product-card`）+ `_find_table_end_line` + `_rakuten_load_cache`/`_rakuten_save_cache` を追加。`process_inline_products`（比較表直後にカード追加）/ `inject_affiliate_links`（末尾セクション一番上にカード追加）を改造。既存リンク・CTA・PR注記はすべて維持。`global.css` に `.pc-img`（80px）追加
  - **deploy.yml**: `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` env（secrets）+ `data/rakuten_cache.json` の git add を追加
  - **テスト**: `TestRakutenSearch`（6件: 成功/0件/クレデンシャル未設定/キャッシュ/429リトライ/エラー）+ `TestGenerateRakutenCard`（2件）新規。`TestProcessInlineProducts` をカード挿入前提に更新。全173件通過（+9）
  - **Verification** (2026-10-08):
    - `pytest scripts/tests/` → **173 passed** (3.31s)
    - `npm run build` → **122 page(s) built** (3.66s) 成功
  - **要確認（ユーザー）**: GitHub 設定 → Secrets に `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` を追加（`RAKUTEN_AFFILIATE_ID` は既存）

### 過去の記録

- `docs/ai/tasks/2026-10-08-topics-path-bug.md` - トレンドデータ読み込みパス不一致バグ修正 完了 (2026-10-08, pytest 164通過)
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
