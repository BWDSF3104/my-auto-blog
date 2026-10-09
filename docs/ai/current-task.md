# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- `docs/ai/tasks/2026-10-09-genre-integration.md` - ジャンル事前スコアリングを記事生成フローに統合。**完了** (2026-10-09)
  - **実装内容**: `genre_score.py` に `score_topics()` 追加（latest.json 全件 + 版権を事前スコアリング → `data/genre_scores/topics.json`）。`generate_article.py` に `WORLD_SETTING_GENRE_MAP` / `_load_genre_scores()` / `_filter_by_genre()` 追加、`_append_trending_topics`・`_load_character_features` に `target_genres` パラメータ追加、生成フロー順序変更（world_setting 決定 → トレンド選択）。失敗時は従来のランダム選択にグレースフルフォールバック
  - **Verification** (2026-10-09): `pytest scripts/tests/` → **285 passed** (3.87s)
  - **E2E Verification** (2026-10-09): run `37937164582`（deploy.yml）+ `37939935733`（deploy-only）
    - V1 score_topics: PASS（119 topics + 19 copyrights, 138 API calls, 31s）
    - V2 topics.json: PASS / V3 トレンドフィルタ: PASS / V4 版権フィルタ: PASS / V5 記事生成: PASS / V7 実行時間: PASS（5m52s）
    - V6 build-and-deploy: **FAIL→FIX**（タグ「動物と獣人のハーフ / 動物」の `/` が Astro [tag].astro を破損。`ff9ac55` で `/` → `・` 置換）→ deploy-only 再実行 **SUCCESS**
  - **追加修正**: `66d28e7` genre_scores/cache.json・topics.json をコミット対象化（CI キャッシュ再利用 + 追跡性）
  - **Next Action**: 2回目実行でキャッシュヒット動作確認（API calls 大幅削減预期）

- `docs/ai/tasks/2026-10-09-clef-flash-genre-score.md` - Clef-flash ジャンルスコアリング（backlog #4）。**完了** (2026-10-09)
  - **実装内容**: `scripts/genre_score.py`（独立CLI、Clef-flash API呼び出し、SHA256キャッシュ、`--no-cache` フラグ）+ `scripts/tests/test_genre_score.py`（61件、全モック）+ `.github/workflows/genre-score.yml`（workflow_dispatch のみ）+ `api-rate-limits.md` にCloudflare追加 + `backlog.md` P3に2段構成追加
  - **Verification** (2026-10-09): `pytest scripts/tests/` → **261 passed** (3.52s)。実 API スモーク: "攻殻機動隊" → sf:84, fantasy:3, cyberpunk:86, action:47（0.68s、678 input tokens）
  - **Next Action**: ワークフロー手動実行による実 API 疎通確認（ユーザー操作）

- `docs/ai/tasks/2026-10-09-refiner-image-prompt-check.md` - リファインプロンプトに画像プロンプト形式チェックを追加。**完了** (2026-10-09)
  - **実装内容**: `refine_story.txt` に【11. 画像プロンプト形式チェック】新節＋82行目ルール書き換え＋【12. 構成と形式】番号振り直し＋自己検証1項目追加。`refine_tech.txt` に【10. 画像プロンプト形式チェック】新節＋【11. 情報追加に関する制限】番号振り直し＋【9】例外注記。コード変更不要
  - **Verification** (2026-10-09): `pytest scripts/tests/` → **200 passed** (3.28s)
  - **Next Action**: なし

- `docs/ai/tasks/2026-10-09-story-multi-images.md` - ストーリー記事の章内複数画像を許可する指示を追加。**完了** (2026-10-09)
  - **実装内容**: `kemono_story.txt` の本文内挿絵ルールに「章内で展開が激しいシーンや印象的なシーンがある場合は、その章で複数枚の挿入を許可します（合計7箇所以内）」を1行追加。コード変更不要
  - **Verification** (2026-10-09): `pytest scripts/tests/ -v` → **200 passed** (3.23s)
  - **Next Action**: なし

- `docs/ai/tasks/2026-10-09-windows-console-encoding.md` - Windowsコンソールエンコーディング対策の統一。**完了** (2026-10-09)
  - **実装内容**: パイプ時のstdio cp932フォールバックによる`UnicodeEncodeError`・文字化けを解消。既存4パターンのワークアラウンドを`TextIOWrapper.reconfigure()`方式に統一（`fetch_topics.py`の無効なenv設定を置換、`generate_article.py`・`fix_descriptions.py`に新設、`fix_affiliate_links.py`をTextIOWrapper方式から移行）。`workflow-test-procedure.md`に`$env:PYTHONUTF8="1"`（現セッション）の手順記載
  - **Verification** (2026-10-09): `pytest scripts/tests/ -v` → **200 passed** (3.41s)。パイプ環境スモークテストでutf-8化確認
  - **Next Action**: なし

- `docs/ai/tasks/2026-10-09-image-prompt-expressions.md` - 画像プロンプトに場面ごとの表情/ポーズ指定を追加。**実装完了・pytest検証済み** (2026-10-09)
  - **実装内容**: `kemono_story.txt` に2項目追加（キャラ別表情ルール: Danbooru実在タグ1人1-2個・同じ場合は1回指定 / シーンキーワードはポーズ・相互作用・背景・構図・光の簡潔なタグで構成）+ 例4箇所更新。`generate_article.py` に `_parse_image_prompt_targets`（コロン=キャラ別、コロンなし末尾エントリ=共有、legacy互換）新設、`compose_image_prompt` を各キャラ外見の直後にタグをインターリーブする合成へ変更（全同一時はdedupe）。`app.py` 不変、既存の合成順序維持
  - **テスト**: 5件新規（個別インターリーブ/単独/同一dedupe/共有/legacy互換）
  - **Verification** (2026-10-09):
    - `pytest scripts/tests/` → **200 passed** (3.79s)
    - 実Gemini API検証: 全6画像プロンプトが個別指定形式（コロン）で出力、インターリーブ順序・シーンとの表情一致を確認（gemini-3.6-flash、101.4s）
  - **未検証**: E2E（GitHub Actions）での生成画像の見た目

- `docs/ai/tasks/2026-10-08-affiliate-keyword-revision.md` - 楽天アフィリエイトキーワード改善（カスケード検索）。**実装完了・pytest検証済み** (2026-10-09)
  - **実装内容**: `generate_article.py` に `_KEMONO_CORE_TOKENS` / `_KEMONO_ANCHOR_KEYWORDS` / `_rakuten_is_relevant`（kemono汎用kwはコアトークン包含、その他はkw実語トークン包含）/ `_rakuten_first_phrase`（スペース＋区切り語「用的/向け/用/的」で分割し先頭セグメント採用。平仮名1文字は単語内で使われるため区切りに使わない。区切れない1語は商品名重複のためスキップ。固定文字数切断なし・日本語フィルタなし）/ `_rakuten_api_keywords`（Gemini商品名→先頭句→ケモノ+ジャンル→ケモノ+関係性→ケモノ→獣人→動物 のカスケード、英語のみkw除外、重複排除）/ `_rakuten_collect`（関連性フィルタ通過した最大3商品を収集、affiliateUrl重複排除、到達で即停止）を追加
  - `inject_affiliate_links` に `gemini_products` / `kemono_params` パラメータ追加、kwループ→カスケード収集へ置換。`process_inline_products` に `prompt_type` 抽出+関連性フィルタ追加。パイプラインは `process_product_cards` 実行前に `extract_product_recommendations` でGemini商品名を取得（frontmatter除去前に取得するため）
  - **テスト**: `TestRakutenIsRelevant`（6件）/ `TestRakutenFirstPhrase`（6件）/ `TestRakutenApiKeywords`（4件）/ `TestRakutenCollect`（4件）新規。`TestProcessInlineProducts` にフィルタスキープテスト追加+モック商品名を「ノートPC 15型」へ修正
  - **Verification** (2026-10-09):
    - `pytest scripts/tests/` → **194 passed** (3.47s)
  - **未検証**: E2E（GitHub Actions）でのカスケード検索の実挙動。既存の30日キャッシュが優先されるため、新規kwのAPI呼び出しはキャッシュ満了後

- `docs/ai/tasks/2026-10-08-rakuten-affiliate-api.md` - 楽天市場API商品リンク連携。**実装完了・検証済み** (2026-10-08)
  - 修正案 (2026-10-08): 絵文字カードは**維持**（置き換え✗ 廃止✗）= 楽天API商品カードの「追加」のみ。A系本文内はプレーンテキスト化済み
  - **実装内容**: `generate_article.py` に `_rakuten_search`（30日キャッシュ/429リトライ/呼び出し間隔1.5秒/画像付き先頭採用）+ `_generate_rakuten_card`（実画像付き `.product-card`）+ `_find_table_end_line` + `_rakuten_load_cache`/`_rakuten_save_cache` を追加。`process_inline_products`（比較表直後にカード追加）/ `inject_affiliate_links`（末尾セクション一番上にカード追加）を改造。既存リンク・CTA・PR注記はすべて維持。`global.css` に `.pc-img`（80px）追加
  - **deploy.yml**: `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` env（secrets）+ `data/rakuten_cache.json` の git add を追加
  - **テスト**: `TestRakutenSearch`（6件: 成功/0件/クレデンシャル未設定/キャッシュ/429リトライ/エラー）+ `TestGenerateRakutenCard`（2件）新規。`TestProcessInlineProducts` をカード挿入前提に更新。全173件通過（+9）
  - **Verification** (2026-10-08):
    - `pytest scripts/tests/` → **173 passed** (3.31s)
    - `npm run build` → **122 page(s) built** (3.66s) 成功
  - **要確認（ユーザー）**: GitHub 設定 → Secrets に `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` を追加（`RAKUTEN_AFFILIATE_ID` は既存）

- Workflow YAML 修正 (2026-10-08, `8366c32`)
  - `deploy.yml`: cp932→UTF-8変換 + 日本語コメント5行→英語 + 「Run generation script」ブロックの+1 spaceインデント破損を修正（7→6 spaces）+ Rakuten API env 2行・cache git add 2行追加
  - `deploy-only.yml`: 日本語コメント3行→英語（UTF-8は既に正常）
  - push後に deploy.yml / deploy-only.yml ともに自動トリガーされず（deploy.ymlはpushトリガーなし、deploy-only.ymlはpaths不一致）

- **E2Eテスト完了** (2026-10-08, run `37853295471`)
  - 手動トリガー `gh workflow run` → completed/success
  - generate 4m12s（基準2m39s、Rakuten API+topics再取得で増加）/ build-and-deploy 26s（基準22s）
  - 楽天API: 3kw全て0件→フォールバック（検索リンク方式）。429エラーなし。間隔1.03s/1.55s
  - 記事: 絵文字カード1件 + 検索リンク6本 + PR注記（全て維持）
  - `data/rakuten_cache.json`（3エントリ）/ `data/affiliate_links/2026-10-09-072523.json` 生成済み
  - **未検証**: 楽天API商品カードの成功パス（実画像・アフィリエイトURL・価格）。商品性の高いkwが必要
  - 結果: `test-results/2026-10-08-github-workflow-test.md`（ローカルのみ、.gitignore済み）

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
