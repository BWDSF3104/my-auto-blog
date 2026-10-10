# Plans Archive

Completed plans moved from `plans.md`. Kept 5 most recent in `plans.md`.

---

## ログ・メタファイルのクリーン処理（リネーム+期間削除） (2026-10-10)

デプロイごとに `drafts/`・`trend_usage/`・`affiliate_links/`・`prompt_logs/`（いずれも無制限蓄積・readback なし監査ログ）がリポジトリに蓄積していたため整理。ファイル名から「ログであること」が分かりにくい `data/affiliate_links` の命名を是正し、ログディレクトリ名を `_logs` 規則で統一（`affiliate_links`→`affiliate_logs`、`trend_usage`→`trend_usage_logs`。`git mv` + `.gitkeep` 追加 + 機能コード1行 + `deploy.yml` 参照更新）。`generate_article.py` に `_cleanup_old_logs(days=30)` 追加（ファイル名タイムスタンプ `%Y-%m-%d-%H%M%S` 基準で30日前ファイルを4ディレクトリから削除、`.gitkeep`・形式不一致ファイルは削除対象外、`generate_post()` 末尾で呼出）。削除は `deploy.yml` の既存2段コミット構造で捕捉（`drafts/`・`trend_usage_logs/`・`prompt_logs/`→第1コミット、`affiliate_logs/`→`git add -A` で第2コミット）。`topics/` は既存の最新10件保持（個数ベース, `fetch_topics.py:892`）を維持。全モックテスト8件追加、pytest 305通過。詳細: `docs/ai/tasks/2026-10-10-log-cleanup.md`

## タグ生成ロジックの構造化リファクタ (2026-10-09)

最新記事の tags が「動物と獣人のハーフ・動物」（体型タグ未分割）・「、ライバル関係」（extra_text の「、」接頭混入）と不自然だったため、スクリプト内で最初から構造化データ（`char_types` / `world_tags` / `extra_tag`）を保持し、`_build_kemono_tags()` で結合・分割を往復せずにタグを生成する設計へ変更。プロンプト表示用結合文字列（`char_type` / `world_setting` / `extra_text`）は派生値として維持（`kemono_story.txt` の文脈自然さのため）。併せて `target_genres` のキー不一致バグ（`world_setting` 表示文字列 → `world_setting_key`）を修正し、ジャンルベースのトレンド優先選択を実効化。pytest 297通過、ビルド 131ページ成功。詳細: `docs/ai/tasks/2026-10-09-tag-split-refactor.md`

## ジャンル事前スコアリングを記事生成フローに統合 (2026-10-09)

独立CLI（`genre_score.py`）が完成したClef-flashジャンルスコアリングを、記事生成のトレンド選択・版権選択に統合。`score_topics()` で latest.json 全件 + 版権を事前スコアリングし `data/genre_scores/topics.json` に保存。`generate_article.py` に world_setting→ジャンル変換（`WORLD_SETTING_GENRE_MAP`）を追加し、`_append_trending_topics` と `_load_character_features` に `target_genres` パラメータを追加（ジャンル適合度優先選択）。生成フローの順序を world_setting 決定 → トレンド選択に変更。失敗時は従来のランダム選択にグレースフルフォールバック。テスト19件追加（全285通過）。詳細: `docs/ai/tasks/2026-10-09-genre-integration.md`

## Clef-flash ジャンルスコアリング（backlog #4） (2026-10-09)

Cloudflare Workers AI の判断特化モデル `@cf/cloudflare/clef-flash` で、文字列の複数ジャンル（sf/fantasy/cyberpunk/action、設定変更可能・最大64問）への関連度を 0-100 整数スコアで取得する。独立 CLI `scripts/genre_score.py`（env `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN`、5xx のみ限定的に再試行、4xx・無料枠超過は再試行せず、SHA256キャッシュ `data/genre_scores/cache.json`、`--no-cache` フラグ）+ 全モック単体テスト61件 + `workflow_dispatch` のみ `.github/workflows/genre-score.yml`。`generate_article.py` 組み込みはスコープ外。2段構成（LLM→Clef-flash）は backlog P3 #1 に追記。実 API スモーク: "攻殻機動隊" → sf:84, fantasy:3, cyberpunk:86, action:47（0.68s）。pytest 261通過。詳細: `docs/ai/tasks/2026-10-09-clef-flash-genre-score.md`

## リファインプロンプトに画像プロンプト形式チェックを追加 (2026-10-09)

2-passリファイナーの役割に「画像生成プロンプトの書式が正しいことの確認」を追加。2026-10-09実Gemini検証で書式逸脱（自然言語句等）がリファイナー（画像プロンプトを変更しないよう明示指示）を無修正通過しPython側フォールバック解析で黙って劣化することを確認。refine_story.txt / refine_tech.txt に「画像プロンプト形式チェック」新節を追加し、修正権限は形式のみに厳密限定（シーンの選定・配置・枚数・キーワードの意味・表情の意図・本文は変更不可）。コード変更不要、pytest 200通過。詳細: `docs/ai/tasks/2026-10-09-refiner-image-prompt-check.md`

## ストーリー記事の章内複数画像を許可 (2026-10-09)

kemono_storyの画像指示は「各章ごとに少なくとも1つ」でモデル出力も各章1枚固定だったため、展開が激しい・印象的なシーンでは章内で複数枚の挿入を許可する指示を1行追加（合計上限はヘッダー1+本文内最大7枚のまま不変、被り禁止ルールは維持）。コード変更不要。pytest 200通過。詳細: `docs/ai/tasks/2026-10-09-story-multi-images.md`

## Windowsコンソールエンコーディング対策の統一 (2026-10-09)

パイプ時のstdio cp932フォールバックによる`UnicodeEncodeError`（絵文字）・文字化けの原因を特定し、既存4パターンのワークアラウンド（無効なenv設定/_safe_print×2/TextIOWrapper差し替え/reconfigure）を`TextIOWrapper.reconfigure()`方式に統一。`fetch_topics.py`・`generate_article.py`・`fix_affiliate_links.py`・`fix_descriptions.py`の4エントリにwin32ガード付きブロックを追加、`workflow-test-procedure.md`に`$env:PYTHONUTF8="1"`（現セッション）の手順を記載。pytest 200通過。詳細: `docs/ai/tasks/2026-10-09-windows-console-encoding.md`

## 画像プロンプト表情/ポーズ指定 (2026-10-09)

kemono_storyの画像プロンプトに表情データがなく生成画像の2匹が同じ・無関係な表情になる問題を解消。キャラ別表情（Danbooru実在タグ1-2個、2匹で同じ場合は1回指定）とポーズ（キャラ別ポーズは括弧内、相互作用ポーズはシーンキーワード）を追加。括弧形式は `[c1: tags, c2: tags]`（個別）/ `[c1, c2, tags]`（共有）/ `[c1, c2]`（legacy互換）の3種を `compose_image_prompt` がパースし、各キャラ外見の直後にインターリーブ（既存の合成順序は維持=キャラ/シチュエーション再現度最優先、`app.py`は不変）。テスト5件追加、pytest 200通過。E2E未検証。詳細: `docs/ai/tasks/2026-10-09-image-prompt-expressions.md`

## 楽天アフィリエイトカスケード検索 (2026-10-09)

楽天API商品カードが記事テーマと無関係な商品を返す問題（汎用キーワードで「パンプス」が「シューファンタジー」に、「iPhoneフィルム」が「SF」に、「浴衣」が「百合」にヒット）を解消。キーワード選定をカスケード検索（Gemini商品名→先頭句→ケモノ+ジャンル→ケモノ+関係性→ケモノ→獣人→動物）に変更し、関連性フィルタ（kemono汎用kwは商品名にケモノ/獣人/動物/アニマル等のコアトークン、その他はkw実語トークン包含）を追加。フィルタ通過商品3件で即停止、affiliateUrlで重複排除。先頭句はスペース+「用的/向け/用/的」で分割（単語内で使われるため平仮名1文字は区切りに使用しない）。楽天API公式レート制限（1req/s per application_id）をapi-rate-limits.mdに追加。pytest 195通過。E2E未検証。詳細: `docs/ai/tasks/2026-10-08-affiliate-keyword-revision.md`

## トレンドデータパス不一致バグ修正 (2026-10-08)

`2b4a815`（静的解析の絶対パス化）で `generate_article.py` の `PROJECT_DIR` が `scripts/` を指すようになり、`TOPICS_DIR = scripts/data/topics`（存在しない）と `fetch_topics.py` の出力先 `data/topics` が不一致。2026-10-02以降全記事でトレンド注入がサイレント無効（trend_usageログ `file_not_found`）していた。`PROJECT_DIR` をリポジトリ直下に戻し、`fetch_topics.py` 起動パスを `scripts/` 補正。回帰テスト3件追加。pytest 164通過 (1.99s)

## 生成パイプライン6項目修正 (#1, #3, #5, #6, #7, #8) (2026-10-07)

英語用語漏れ修正 (CHAR_TYPE_WEIGHTS日本語化)、2passリファイン強化 (refine_story.txt全体書き換え)、e621収集開始時期ランダム化 (2010-01-01〜現在-14dランダム14日ウィンドウ)、アフィリエイト英語キーワード除去 (tags日本語化+prompt_typeフィルタ+_KEYWORD_ENHANCEMENT cleanup)、製品推薦の具体化 (A1/A2ルール強化+_improve_keyword suffix削除)、trend_usageログ欠落修正 (早期リターンにログ追加+.gitkeep)。pytest 161通過、e621 API確認 (200 OK)

## 画像生成上限増加 (2026-10-06)

記事あたりの画像上限を3枚→8枚（ヘッダー1 + 本文内最大7）に増加。ストーリー系は各章ごとに画像を配置する指示に変更。HF ZeroGPUの実稼働時間消費（初回9秒、ウォーム2秒）をapi-rate-limits.mdに反映。pytest 155通過、ビルド成功 (114ページ)

## 画像プロンプト順序最適化 (2026-10-06)

BASE_QUALITY_PROMPTを8→6タグ短縮、Illustrious系推奨順序に再配置（被写体数→キャラクター→シチュエーション→artist→品質→スタイル）。pytest 155通過、ビルド成功 (114ページ)。commit: `947009c`, `fbbb0ab`

## e621 artistタグ集計機能 (2026-10-06)

CHARACTER_FEATURE_CATEGORIESにartist追加、unknown_artist除外、generate_article.pyに人気artist注入、art_style指示にartist名候補追加。pytest 155通過、ビルド成功 (110ページ)。commit: `2e960f3`

## 画像プロンプト指示をDanbooruキーワード形式に統一 (2026-10-06)

`kemono_story.txt` にDanbooru互換全体指示新規追加、art_style指示に3-5タグ明記+例更新、character指示に種族例+服装1-2つ+5-8タグ制限、IMAGE_PROMPT挿入例・Frontmatter例を自然言語→キーワード形式、`DEFAULT_ART_STYLE`を5→3トークン短縮。pytest 155通過、ビルド成功 (110ページ)。commit: `db0641b`

## kemono_story プロンプトのPython側ランダム化 (2026-10-05)

6項目の重み付きランダム選択 (`_randomize_kemono_params`) + バリデーション (`_is_valid_kemono_combination`) を実装。`char_count=1` は `extra=clone` 時のみに制限。`char_count_desc` は 2人の場合 "バディ"/"ライバル"/"カップル" からランダム選択。テスト21件追加、全155件通過、ビルド成功 (110ページ)。commit: `2804bfd`

## ブランドカラー統一 (2026-10-05)

`global.css` + `PostLayout.astro` のハードコードHEXをCSS変数(26変数)に集約。既存カラー値は不変。変更前後のビルド出力比較で45色完全一致を確認。ビルド成功 (110ページ)

## モバイルハンバーガーメニュー (2026-10-05)

`Header.astro` に640px未満用のドロップダウンメニューを追加。検索、ダークモード、記事一覧（`#main-content`アンカー）、タグ一覧、About、RSS、Privacy を含む。外部クリックで閉じる。ビルド成功 (110ページ)

## ヒーローセクション (2026-10-05)

`Header.astro` にグラデーション背景、ステータスバー（記事数/タグ数/最新更新日）、アクションボタンを追加。統計情報は `import.meta.glob` でビルド時計算。レスポンシブ対応 (3カラム→sm以上)。ビルド成功 (108ページ)

## カテゴリーカード (2026-10-04)

フロントページにタグ別記事数のセクションを追加。`CategoryCards.astro` コンポーネント新規作成。既存 `tagColors.ts` の12色パレットを再利用。記事数順にトップ12タグをスリムなアコーディオン型で表示（デフォルト閉じ、ボタンで展開）。ビルド成功 (108ページ)

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

## canonical URL一貫性 (2026-10-01)

slug変更時の301リダイレクト実装。`data/slug-redirects.json` で旧→新slugマッピングを記録。`generate_article.py` にslug変更検出・自動記録ロジック追加。`[...slug].astro` の `getStaticPaths` にリダイレクトルートを追加してAstroレベルの301リダイレクトを実装。sitemap整合性確認済み。テスト119件全件通過、ビルド成功 (90ページ)

---
*以下は 2026-10-06 に plans.md からアーカイブ*

## Plausibleアクセス解析の有効化 (2026-10-04)

`Layout.astro` のPlausibleスクリプトを`BWDSF3104.github.io`ドメインで有効化。ビルド成功 (108ページ)

## 目次 (TOC) のレスポンシブ対応 (2026-10-04)

デスクトップは既存のstickyサイドバー維持、モバイルにアコーディオン型折りたたみTOCを追加。`PostLayout.astro` にトグルボタン、chevron SVG、JSトグルハンドラー (aria-expanded) を実装。`headings`変数のスコープ修正。ビルド成功 (108ページ)

## 重複YAMLキーによるビルド失敗の修正 (2026-10-04)

AI が出力した重複YAMLキー（`少年:` 等）による Astro ビルド失敗を解決。`generate_article.py` に自動修復ロジック実装、破損記事を手動修正、テスト110件全通、ビルド成功、デプロイ完了

## Backlog P0 実装 (B1-B4) (2026-10-02)

9件の P0 バックログを 4 バッチで実装。B1: Back to Top FAB + Skip Navigation リンク + `.skip-link` CSS。B2: コードブロックコピーボタン (Clipboard API) + 画像 Lazy Loading。B3: `src/lib/tagColors.ts` で 12 色パレットのタグ色 + `og:locale` + 動的 `og:image` メタデータ + `article:modified_time`。B4: Social Sharing (X, Hatena, LINE, Pocket) + Footer SNS アイコン (X, GitHub, RSS) + BreadcrumbList JSON-LD (index, page, tags)。ビルド成功 (94ページ)

## Reddit 代替ソースの追加 (2026-10-02)

e621、Kemono API、RSS フィードを代替ソースとして追加。kemono/pokemon カテゴリのトピック収集を安定化。テスト134件全件通過

## 既存記事のアフィリエイトリンク一括置換 (2026-10-02)

`scripts/fix_affiliate_links.py` で 15ファイル（48行）を `[text](url)` から `<a>` タグに置換。1ファイル試験→全体適用→ビルド成功 (94ページ)

## FAQPage schema + Speakable schema (2026-10-01)

記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成（行単位ステートマシンパーサー）。記事冒頭段落をSpeakable JSON-LDとして出力。`generate_article.py` に `_extract_faq_pairs()` と `_extract_speakable_text()` を追加し、frontmatter にJSON文字列で記録。`PostLayout.astro` で条件付きJSON-LD出力。テスト134件全件通過、ビルド成功 (90ページ)
