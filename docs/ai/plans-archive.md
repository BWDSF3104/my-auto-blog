# Plans Archive

Completed plans moved from `plans.md`. Kept 5 most recent in `plans.md`.

---

## カテゴリ別ソースフィルタリング (2026-10-01)

各トレンドソースが収集すべきカテゴリを明示的に設定。不要なカテゴリの取得を削減。

## 画像生成のフォールバック機制 (2026-10-01)

HuggingFace 画像生成のフォールバックとして Pollinations.ai を統合。`IMAGE_PROVIDER` 環境変数で `hf`（デフォルト、HF→Pollinationsフォールバック）と `pollinations`（直接Pollinations）を切り替え可能。AVIF変換を `_save_as_avif()` ヘルパーに分離。テストスクリプトが外部APIを呼ばないことを確認し、11件のユニットテストを追加（AVIF変換3、Pollinations3、ルーティング5）。テスト96件全件通過、ビルド成功を確認 (ed2ebe0)

## kemono_story ワークフローの改善 (2026-10-01)

印象的なシーン（親密さ・密着・アクション・感情的瞬間）の必須配置を条件8として追加。画像シーン選出ルールを3枚の役割分担（トップ画像=最もインパクトのある瞬間、挿絵1=前半〜中盤、挿絵2=中盤〜後半）に強化し、同じシーンの被りを防止。refine_story.txt に弱化防止チェックを追加

## アフィリエイトリンクのHTML `<a>` タグ化 (2026-09-30)

`inject_affiliate_links()` のリンク生成をMarkdown `[text](url)` からHTML `<a href="url">text</a>` に変更。長いUTMパラメータ付きURLを隠蔽。既存記事は修正対象外（known-issues.md 保留）

## ワークフローの Secrets 未接続修正 (2026-09-30)

`AMAZON_TRACKING_ID` と `RAKUTEN_AFFILIATE_ID` を `deploy.yml` の `env:` に接続。CI 実行時に正しいアフィリエイトタグが記事に埋め込まれるよう修正 (4b2ef1c)

## AI Memory Bank 運用方針改訂 (2026-09-30)

Memory Bank の更新タイミングを commit 前に変更し、`current-task.md` を追加。Long-running Agent Tasks と Recovery After Interruption のセクションを AGENTS.md に追加。`plans.md` の Active/Completed を分離、`backlog.md` の優先度を P0/P1/P2 に変更、`known-issues.md` に `Next action` フィールド追加、`decisions.md` に `Rejected Alternatives` フィールド追加。

## デプロイ完了管理とキャラ被り検出の強化 (2026-09-30)

デプロイ成功後にのみ生成完了タイムスタンプを記録し、同日の成功記録があれば再生成をスキップ。キャラクター被り検出をタイトルのみから frontmatter 全体（character_1, character_2, tags, art_style）に拡張して NG 指示ブロックに注入。テスト85件全件通過、ビルド成功を確認

## CRITICAL バグ修正 (2026-09-30)

静的監査で発見した 5 件の CRITICAL バグを修正。fetch_topics.py の e621 float スコア対応と TTL merge ロジックの反転。generate_article.py のカテゴリ不一致期限切れマーク、bare except のリトライ化、TTL チェック戻り値のキャプチャ。テスト85件全件通過、ビルド成功を確認

## ユニットテスト作成 (2026-09-30)

`fetch_topics.py` と `generate_article.py` のテストスクリプトを新規作成。85テスト全件通過（fetch_topics 24件、generate_article 61件）。キャッシュ構成（タイムスタンプファイル、シンボリックリンク、merge、クリーンアップ、TTL）、per-source TTLチェック、auto-fetchを網羅。ソースコードの静的監査も併行実施し、9件の潜在的バグを known-issues.md に記録 (66df732)

## キャッシュ構成の改善 (2026-09-30)

取得開始日時分別のファイル構成に変更。各ソースに独立した `fetched_at` を付与し、TTL超過したソースのみ再取得。`generate_article.py` が TTL 超過時に `fetch_topics.py --prompt-type X` を自動実行し、不要なカテゴリの取得を削減。`data/topics/{timestamp}.json` + `data/topics/latest.json` シンボリックリンク構成に切り替え。旧 `data/latest_topics.json` は廃止

## アフィリエイトキーワードの文脈化 (2026-09-30)

trend_keywords（GitHubリポジトリ名）の直接使用を中止。記事本文のtagsと先頭段落からテーマキーワードを抽出し、trend_keywordsはGitHubリポジトリ名を除外して補充。キーワード優先順位を「本文抽出 → trend_keywords → tagsフォールバック」に変更 (556c868)

## ドキュメント整合性修正 (2026-09-30)

known-issues.mdを日本語統一、decisions.mdとarchitecture.mdのgit除外記述を削除、AGENTS.mdにdocs/ai/のgit追跡とdevelopment-notes.md削除を明記、development-notes.mdをgitから削除 (1994529)

## SEO改善 (2026-09-30)

slugルーティング, TOC, タグページ, 関連記事, BreadcrumbList/SearchAction JSON-LD。検索エンジン最適化と内部リンク構造の強化が目的 (78ed667)

## メタ記述検証修正 (2026-09-30)

80文字未満のdescriptionを意味のない文字で埋める問題を本文抽出で修正。正規表現の脆弱性も修正 (ac4db31, 37ee985)

## OG image自動生成 (2026-09-30)

ヘッダー画像をOG画像として流用。faviconフォールバック (ac4db31)

## アフィリエイト改善 (2026-09-29)

トレンドキーワード連携, 商品カード, UTM追跡, クリック分析, 比較表。CTR向上とパフォーマンス測定が目的 (dae81e8, 0a329f0, 158a89c)

## 記事生成品質向上 (2026-09-29)

プロンプト強化, 2-pass生成, SFW強制, 記事内アートスタイル統一。生成物の質と安全性を確保 (543545a, 035063d)

## トレンド収集拡張 (2026-09-29)

NSFWフィルタ, カテゴリ厳格化, Bluesky追加, フロントマター参照追跡, スコアしきい値。データの質と追跡可能性を向上 (a0602d7)

## 環境変数管理 (2026-09-29)

python-dotenv導入, docs/ai/のgit除外。設定の一元化と機密情報の保護 (3e94448, 56be18e)

## アフィリエイトリストリンクのカード化 (2026-09-30)

記事内のAmazon・楽天リストリンクをCSSのみでカードスタイルに変更。Amazonは琥珀色、楽天はピンク色のテーマ。既存記事に遡及適用 (27cba6a)

## 2-pass精製プロンプトの改善 (2026-09-30)

全体書き換えから「監査→問題箇所のみ修正」へ転換。REFINE_PROMPT_STORY と REFINE_PROMPT_TECH を外部テンプレートファイルに分離し、内部レビュー工程を明示。2-passの役割を「高品質化」から「欠点除去」に再定義 (36d920d)

## プロジェクト構造 (2026-09-28)

不変ルール(AGENTS.md)と変動知識(docs/ai/)の分離。エージェントの知識管理を改善 (647c4b5)

---
*以下は 2026-10-02 に plans.md からアーカイブ*

## データソースのレート制限調査 (2026-10-02)

各APIのレート制限を調査・実測し `AGENTS.md` に記録。`test_real_apis.py` を独立スクリプトとして作成。テスト7/9通過 (Reddit 403, Bluesky 501 はAPI側規制)。`226f464`

## AGENTS.md のレート制限テーブル分離 (2026-10-02)

AGENTS.md のレート制限テーブルを docs/ai/api-rate-limits.md に分離 + fetch_topics.py 更新後の test_real_apis.py 検証ルールを追加。`628b46d`

## kemono/furry トレンド作品追跡の改善 (2026-10-02)

e621 に rating:safe 制限を追加して NSFW フィルタ回避、furry/wolf/fox/rabbit の score 順クエリを追加して人気作品を追跡、Bluesky 検索キーワードを拡張

## 'pokemon' カテゴリの kemono_story から除外 + ランダムトレンド選択 (2026-10-02)

kemono_story から 'pokemon' カテゴリを削除し、トレンド選択を「カテゴリごとに上位5件」から「全カテゴリをプールしてランダム2件」に変更。e621 の character/copyright タグを収集対象に追加してアフィリエイト製品推薦に活用

## ダークモード修正 (2026-10-01)

`is:inline` 属性なしでクライアントサイドスクリプトが動作しない問題を `Header.astro`, `PostLayout.astro`, `tags/index.astro` に追加して修正。`PostLayout.astro` に `Header` コンポーネントのインポート、`dark:` 変種クラス、ダークモードCSSを追加して記事ページのダークモード対応を完了。ビルド成功 (90ページ)
