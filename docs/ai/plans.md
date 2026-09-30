# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

(なし)

# Completed Plans

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。

- [2026-09-30] アフィリエイトリンクのHTML `<a>` タグ化: `inject_affiliate_links()` のリンク生成をMarkdown `[text](url)` からHTML `<a href="url">text</a>` に変更。長いUTMパラメータ付きURLを隠蔽。既存記事は修正対象外（known-issues.md 保留）
- [2026-09-30] ワークフローの Secrets 未接続修正: `AMAZON_TRACKING_ID` と `RAKUTEN_AFFILIATE_ID` を `deploy.yml` の `env:` に接続。CI 実行時に正しいアフィリエイトタグが記事に埋め込まれるよう修正 (4b2ef1c)
- [2026-09-30] AI Memory Bank 運用方針改訂: Memory Bank の更新タイミングを commit 前に変更し、`current-task.md` を追加。Long-running Agent Tasks と Recovery After Interruption のセクションを AGENTS.md に追加。`plans.md` の Active/Completed を分離、`backlog.md` の優先度を P0/P1/P2 に変更、`known-issues.md` に `Next action` フィールド追加、`decisions.md` に `Rejected Alternatives` フィールド追加。

- [2026-09-30] デプロイ完了管理とキャラ被り検出の強化: デプロイ成功後にのみ生成完了タイムスタンプを記録し、同日の成功記録があれば再生成をスキップ。キャラクター被り検出をタイトルのみから frontmatter 全体（character_1, character_2, tags, art_style）に拡張して NG 指示ブロックに注入。テスト85件全件通過、ビルド成功を確認
- [2026-09-30] CRITICAL バグ修正: 静的監査で発見した 5 件の CRITICAL バグを修正。fetch_topics.py の e621 float スコア対応と TTL merge ロジックの反転。generate_article.py のカテゴリ不一致期限切れマーク、bare except のリトライ化、TTL チェック戻り値のキャプチャ。テスト85件全件通過、ビルド成功を確認
- [2026-09-30] ユニットテスト作成: `fetch_topics.py` と `generate_article.py` のテストスクリプトを新規作成。85テスト全件通過（fetch_topics 24件、generate_article 61件）。キャッシュ構成（タイムスタンプファイル、シンボリックリンク、merge、クリーンアップ、TTL）、per-source TTLチェック、auto-fetchを網羅。ソースコードの静的監査も併行実施し、9件の潜在的バグを known-issues.md に記録 (66df732)

- [2026-09-30] キャッシュ構成の改善: 取得開始日時分別のファイル構成に変更。各ソースに独立した `fetched_at` を付与し、TTL超過したソースのみ再取得。`generate_article.py` が TTL 超過時に `fetch_topics.py --prompt-type X` を自動実行し、不要なカテゴリの取得を削減。`data/topics/{timestamp}.json` + `data/topics/latest.json` シンボリックリンク構成に切り替え。旧 `data/latest_topics.json` は廃止
- [2026-09-30] アフィリエイトキーワードの文脈化: trend_keywords（GitHubリポジトリ名）の直接使用を中止。記事本文のtagsと先頭段落からテーマキーワードを抽出し、trend_keywordsはGitHubリポジトリ名を除外して補充。キーワード優先順位を「本文抽出 → trend_keywords → tagsフォールバック」に変更 (556c868)
- [2026-09-30] ドキュメント整合性修正: known-issues.mdを日本語統一、decisions.mdとarchitecture.mdのgit除外記述を削除、AGENTS.mdにdocs/ai/のgit追跡とdevelopment-notes.md削除を明記、development-notes.mdをgitから削除 (1994529)
- [2026-09-30] SEO改善: slugルーティング, TOC, タグページ, 関連記事, BreadcrumbList/SearchAction JSON-LD。検索エンジン最適化と内部リンク構造の強化が目的 (78ed667)
- [2026-09-30] メタ記述検証修正: 80文字未満のdescriptionを意味のない文字で埋める問題を本文抽出で修正。正規表現の脆弱性も修正 (ac4db31, 37ee985)
- [2026-09-30] OG image自動生成: ヘッダー画像をOG画像として流用。faviconフォールバック (ac4db31)
- [2026-09-29] アフィリエイト改善: トレンドキーワード連携, 商品カード, UTM追跡, クリック分析, 比較表。CTR向上とパフォーマンス測定が目的 (dae81e8, 0a329f0, 158a89c)
- [2026-09-29] 記事生成品質向上: プロンプト強化, 2-pass生成, SFW強制, 記事内アートスタイル統一。生成物の質と安全性を確保 (543545a, 035063d)
- [2026-09-29] トレンド収集拡張: NSFWフィルタ, カテゴリ厳格化, Bluesky追加, フロントマター参照追跡, スコアしきい値。データの質と追跡可能性を向上 (a0602d7)
- [2026-09-29] 環境変数管理: python-dotenv導入, docs/ai/のgit除外。設定の一元化と機密情報の保護 (3e94448, 56be18e)
- [2026-09-30] アフィリエイトリストリンクのカード化: 記事内のAmazon・楽天リストリンクをCSSのみでカードスタイルに変更。Amazonは琥珀色、楽天はピンク色のテーマ。既存記事に遡及適用 (27cba6a)
- [2026-09-30] 2-pass精製プロンプトの改善: 全体書き換えから「監査→問題箇所のみ修正」へ転換。REFINE_PROMPT_STORY と REFINE_PROMPT_TECH を外部テンプレートファイルに分離し、内部レビュー工程を明示。2-passの役割を「高品質化」から「欠点除去」に再定義 (36d920d)
- [2026-09-28] プロジェクト構造: 不変ルール(AGENTS.md)と変動知識(docs/ai/)の分離。エージェントの知識管理を改善 (647c4b5)
