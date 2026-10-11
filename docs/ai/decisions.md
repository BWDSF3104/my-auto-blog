# Design Decisions

古い決定は `decisions-archive.md` に移動する。直近15件のみ保持。

## 2026-10-11: Pythonスクリプトの構造は「入口ファイル固定 + `scripts/article/` パッケージ + フェーズ分割移行」

**Decision**: `scripts/generate_article.py`（3561行・`generate_post()` CC81/325行）は `scripts/article/` パッケージ（`config` / `gemini` / `image` / `affiliate` / `trends` / `frontmatter` / `slug_links` / `meta`）へ責務群を分離し、`generate_article.py` 自体は「入口 + `generate_post()` パイプライン」に縮約する。`generate_post()` は 8 ステージ関数（`build_ng_instruction` / `resolve_kemono` / `generate_content` / `build_header_image` / `apply_frontmatter_fields` / `postprocess_content` / `apply_seo_schemas` / `finalize_and_save`）に分解（本体は約70行・CC約12）。`scripts/fetch_topics.py`（1032行・`main()` CC52）はパッケージ化せず、`main()` 内の関数抽出（`collect_all_topics` / `build_output`（純粋関数）/ `save_output` / `cleanup_old_topic_files`）のみ行う。移行は 8 フェーズ（0=ベースライン → 1=fetch_topics → 2=article/雛形+config/meta → 3=image → 4=affiliate → 5=trends/frontmatter/slug_links → 6=大関数分解 → 7=入口縮約+docs更新）で、各フェーズ末に `pytest scripts/tests/` 緑を確認して進行する。

**Reason**: (1) プロダクション入口は `deploy.yml:50` / `deploy.yml:89` がファイル名固定で起動するため、`fetch_topics.py` / `generate_article.py` は入口として残置し、中身だけを分離する。（2）`generate_article.py::_auto_fetch_topics`（L2077）が `fetch_topics.py` をパス指定 subprocess で実行するため、`fetch_topics.py` は独立実行可能のまま維持（`main()` は同ファイル内に残す）。（3）テストが `patch("generate_article.X")` 形式で内部関数に強く結合しているため、**関数移設と patch 経路更新（→ `patch("article.<module>.X")`）を同一フェーズで実施**しないと mock が実コードに効かなくなる（サイレントなテスト無効化が最悪ケース）。(4) 8 フェーズ分割で各フェーズが独立に pytest 検証可能なため、中間状態での回帰を最小単位で検出できる。

**Rejected Alternatives**:
- `generate_article.py` 内の関数抽出のみ（パッケージ分割しない・保守的案）: 3561行の単一ファイルが残り責務の混在（Gemini/画像/アフィリエイト/トレンド/SEO/ログ管理）が解消されないため、管理のしやすさという目的に不达
- `fetch_topics.py` も `scripts/topics/` パッケージ化: 1032行で問題は `main()` への集中のみ。入口 subprocess 起動経路・テストの patch 対象（`fetch_topics.TOPICS_DIR` / `urllib` 等）の更新コストに見合わない
- 1回の大型コミットで一括移行: 中間状態を pytest で検証できず、3561行 + テスト 2974行の同時変更で回帰の切り分け不能
- `scripts/article/` を `scripts/generate_article/`（ディレクトリ同名化）に: `generate_article.py` と `generate_article/` が同名混在し Windows / import の曖昧性が高まるため不採用

**Impact**:
- 新規: `scripts/article/{__init__,config,gemini,image,affiliate,trends,frontmatter,slug_links,meta}.py`、`scripts/generate_article.py` は入口+パイプラインに縮約（行数は Phase 7 完了時点で確定）
- `scripts/fetch_topics.py`: `main()` 関数抽出（入口は不変）
- `scripts/tests/test_generate_article.py` / `test_fetch_topics.py`: import と `patch` 経路をフェーズごとに更新
- `.github/workflows/*.yml`: 不変（入口ファイル名は維持）
- 完了条件: 全フェーズ pytest 緑 + `npm run build` 緑 + README / AGENTS.md の構造記載更新
- 詳細: `tasks/2026-10-11-python-refactor-package-split.md`

## 2026-10-11: コメント機能は Giscus（GitHub Discussions バックエンド）を採用

**Decision**: 記事のコメント機能に Giscus（https://giscus.app、GitHub Discussions をバックエンドとするクライアントサイド iframe ウィジェット）を採用。新規 `src/components/GiscusComments.astro` を `src/layouts/PostLayout.astro` の記事末尾（Social Sharing セクション直後）に組み込み、frontmatter `comments: false` で記事単位無効化（`src/content.config.ts` schema に `comments: z.boolean().optional()` 追加）。`data-mapping="pathname"`（base `/my-auto-blog` で開発・本番の pathname が一致し同一 Discussion 共有）。テーマ同期は `documentElement` の class 変化を MutationObserver で監視し giscus script の `data-theme` を更新（サイトのダーク切替はイベントを発火しないため、`Header.astro` 無変更）。設定は `PUBLIC_GISCUS_REPO` / `PUBLIC_GISCUS_REPO_ID` / `PUBLIC_GISCUS_CATEGORY` / `PUBLIC_GISCUS_CATEGORY_ID` の 4 値（`data-lang="ja"` / `data-loading="lazy"` / `data-strict="0"` / reactions on / emit-metadata off / input bottom）、いずれか欠落時はコンポーネントが early return してセクション非表示。`deploy.yml` / `deploy-only.yml` の build ステップに `env:` で `${{ vars.PUBLIC_GISCUS_* }}` を追加（現状この 2 ワークフローは `PUBLIC_*` を一切渡していないため必須）。

**Reason**: (1) 本プロジェクトは静的サイト（GitHub Pages）+ バックエンド/DB/SSR なしの設計哲学であり、セルフホスト型コメントサービス（Cusdis/Remark42/Isso）は常時稼働サーバーを新規追加するため矛盾。(2) Giscus は無料・広告なし・トラッキングなし・サーバー/DB 不要で、コメントがブログ本体のリポジトリ `BWDSF3104/my-auto-blog` の Discussions に保存されるため「GitHub で生成し Pages にデプロイ」構成と整合。(3) 投稿は GitHub OAuth 必須でスパム抑制が強く、AI 自動生成記事はスパムボットに狙われやすい点で有効。(4) Discussions はスレッド返信・リアクション・カテゴリ・GitHub 側で完結するモデレーションを提供。(5) サイト独自のテーマ切替と両立可能（giscus client は `data-theme` 属性変化で再描画）。

**Rejected Alternatives**:
- Utterances（GitHub Issues バックエンド）: スレッド返信なし・モデレーション弱く、Giscus が機能の上位互換
- セルフホスト型（Cusdis/Remark42/Isso/Commento）: 匿名投稿可能な利点はあるが、サーバー（Fly.io 等）の運用負荷・障害点・バックアップが新規発生。将来匿名投稿が必須化すれば再検討
- SaaS（Disqus/Hyvor Talk/Cusdis Cloud）: 広告・トラッキング（Disqus）、有料（Hyvor）、無料枠制限（Cusdis Cloud）で収益化個人ブログと相性不良
- GitHub Actions + 静的生成による独自実装: 自動生成記事とのコミット競合・非リアルタイムで不向き

**Impact**（計画段階・未実装）:
- 新規 `src/components/GiscusComments.astro`、修正 `src/layouts/PostLayout.astro` / `src/content.config.ts` / `.github/workflows/deploy.yml` / `.github/workflows/deploy-only.yml`
- 手動 1 タスク: Discussions 有効化 + カテゴリ「Comments」（Announcements 種別）作成 + giscus.app ウィザードで giscus app 導入 + 4 値を `.env` と GitHub Variables に登録
- 既知のトレードオフ: 投稿者は GitHub アカウント必須（匿名不可）/ slug リネーム（`slug-redirects.json`）でコメントが引き継がれない / giscus.app と GitHub Discussions API に依存 / コメントデータは Discussions に紐づく（エクスポート API なし）
- タスクファイル: `tasks/2026-10-11-giscus-comments-github-setup.md` / `-env-config.md` / `-component.md` / `-workflow-env.md` / `-verification.md`（バックログ P2 #4）

## 2026-10-11: 生成情報の e621 ブロックは「実際にプロンプトに使った選出データ」を Python 側で表示

**Decision**: 記事末尾の「生成情報」セクションに e621 キャラクター特徴（参考キャラクター2投稿・人気版権・人気artist・データ時点）を表示する。`_load_character_features()`（プロンプト指示文字列返却・選出データを破棄）を `_select_character_features(target_genres) -> dict | None`（`{updated_at, total_posts, raw_posts, posts, copyrights, artists}` 返却）と `_format_character_features_instruction(info) -> str` に分割し、`generate_post()` で `_select_character_features()` を 1 回だけ呼び出して選出 dict をプロンプト（`character_features_instruction`）と `_build_generation_info_section(..., e621_info)` の両方に渡す。`_build_generation_info_section()` の「キャラクターデータ」ブロック直後に「参考キャラクターデータ（e621）」ブロックを `html.escape` 付きで追加（参考キャラ1/2 は 種族/色/身体的特徴/参照/作品 を `<br>` 連結・空は `-`、データ時点は `datetime.fromisoformat` で UTC 整形）。表示は **`prompt_type == "kemono_story"` 限定**（`show_e621 = bool(e621_info) and prompt_type == "kemono_story"`）。既存 `.gen-info-block` / `.gen-info-dl` CSS を流用し Layout 変更なし。

**Reason**: (1) e621 データがプロンプトに注入される経路は kemono_story の `{character_features_instruction}` プレースホルダーのみ（`scripts/prompts/kemono_story.txt:103`）であり、非ケモノ記事では「使用したデータ」ではないため非表示が正しい。(2) 従来は `_load_character_features()` が `random.choice` で選出した 2 投稿を文字列化して返すだけだったため、記事側で「どの投稿を使ったか」を復元不能。選出を dict に分離し 1 回だけ呼び出せば、プロンプトと表示が**同一選出データ**になる（2 回呼び出しでは選出がずれる）。(3) `_load_character_features()` は既存テスト（`TestLoadCharacterFeaturesGenre`）が文字列返却を前提とするため、ラッパーとして残置し互換を維持。(4) 前回決定（2026-10-10 生成情報セクション）と同様に本文直接追記方式で、既存記事への影響・バックフィルなし。

**Rejected Alternatives**:
- `_load_character_features()` をそのまま使い表示側でもう一度選出する: `random.choice` が 2 回独立実行され、プロンプトと表示の参考キャラクターが一致しない
- frontmatter に e621 選出データを保存して Layout が描画: 2026-10-10 決定で frontmatter 方式を不採用済み。本文直接追記で既存記事影響ゼロを維持
- 非ケモノ記事にも e621 ブロック表示（「利用可能なデータ」として）: ユーザー要望は「使用データを載せる」であり、使用していないデータの表示は誤解を招くため不採用

**Impact**:
- `scripts/generate_article.py`: `_select_character_features()` / `_format_character_features_instruction()` 新設、`_load_character_features()` を 2 関数ラッパー化、`generate_post()` で 1 回の選出を共有、`_build_generation_info_section()` に `e621_info: dict | None = None` パラメータ＋e621 ブロック追加
- `scripts/tests/test_generate_article.py`: `TestBuildGenerationInfoSection` に `E621_INFO` fixture + 4 件追加、`TestSelectCharacterFeatures` 新設 6 件（全モック/ローカルファイル）
- `src/layouts/PostLayout.astro` / `scripts/prompts/*.txt` / `fetch_topics.py`: 不変
- pytest 365 passed（ベースライン 355 + 新規 10）。一時記事 build（140 page(s)）で本文末尾配置・既定閉・セクション内 h2〜h4 なし（TOC 非載入）・実データ表示を確認、一時ファイル削除後再 build（138 page(s)）でクリーン状態確認
- 既存記事: 影響なし（`e621_info=None` 時=従来挙動）。次回 deploy 以降に生成される kemono_story 記事のみ表示

## 2026-10-10: 記事末尾の「生成情報」セクションは Python 側で本文に直接追記

**Decision**: 記事末尾の「生成情報」セクション（使用したトレンド情報＋キャラデータ）は `generate_article.py` が `<details class="gen-info">` HTML を生成し、本文末尾に直接追記する。frontmatter に新フィールドを追加して Layout 側で描画する方式は採用しない。`_append_trending_topics()` は第4要素としてクリーンなトレンドタイトル（`"{title}（{source}）"` 形式）を返すよう 3→4 タプル化。変身ラベルは `transform_text`（「、」接頭のプロンプト結合文字列）をそのまま表示せず `_KEMONO_TRANSFORM_LABEL` 定数で分離。表示要素が一切ない記事はセクション非表示（空文字列）。

**Reason**: (1) ユーザーが「生成情報の作成はPythonスクリプト側で行う」と明示したため。(2) セクションを本文に直接入れることで既存記事への影響がゼロになりバックフィルが不要になる（frontmatter 方式なら Layout に表示条件分岐を追加し、既存記事との差分管理が必要）。(3) 保存直前の単一箇所に追記処理を置けるため、FAQ / speakable / 内部リンク等の本文解析ロジックとの干渉を避けやすい（それらはすべて追記前に実行済み）。(4) `<details>` + h2〜h4 不使用で TOC・JSON-LD・関連記事スコアリング（frontmatter 基準）に影響しない。

**Rejected Alternatives**:
- frontmatter 拡張（`trend_topics` / `char_type` 等）+ PostLayout 描画: 設計検討当初の方式。Layout に表示条件・セクション描画を追加する必要があり、ユーザーの Python 側生成指示により不採用
- プロンプトに指示して Gemini が本文末尾へセクション出力: モデル依存で形式・文言が安定しない（HTML 生成指示は従来 NG 指示対象）のため不採用

**Impact**:
- `scripts/generate_article.py`: `import html`、`_KEMONO_TRANSFORM_LABEL` 新設、`_append_trending_topics()` 3→4 タプル化（全4 return 更新）、`_build_generation_info_section()` 新設、`generate_post()` に 5.8 追記処理（保存直前）
- `src/layouts/PostLayout.astro`: `.gen-info` 系 CSS を `<style is:global>` に追加（描画ロジック変更なし）
- `scripts/tests/test_generate_article.py`: 4 タプル unpack 5 箇所更新 + `TestBuildGenerationInfoSection` 6 件新規
- pytest 355 passed（ベースライン 349 + 新規 6）。一時記事での build 検証で本文末尾配置・既定閉・TOC 非載入を確認
- 既存記事: 影響なし（セクション非存在＝非表示）。次回 deploy 以降に生成される記事のみ表示

## 2026-10-10: e621 データのトレンド配管からの分離

**Decision**: e621 をトレンドトピック出力（`data/topics/latest.json`）から完全に排除する。収集自体は継続（キャラクター特徴集計用）。`fetch_topics.py` に `NON_TREND_SOURCES = {"e621"}` 定数を新設し、`collect_e621()` はトレンド項目を組立せず収集数を `int` で返すのみ、`main()` は出力構築前に `sources` / `merged_by_category` / `all_topics_merged` を `NON_TREND_SOURCES` でフィルタする。

**Reason**: e621 のデータは「キャラクター特徴の集計」（`data/character_features.json`）専用であり、ニュース的「トレンド」ではないため、トレンドトピックとして記事プロンプトに注入されると意味が不自然になる。さらに直前データからの merge 継承で e621 が `by_category` に残存し続ける（KI-20261010-01）構造的問題の温床になっていた。

**Rejected Alternatives**:
- e621 収集の完全無効化: キャラクター特徴集計（`_aggregate_and_save_character_features`）が壊れる
- 注入時のみ除外（`generate_article.py` 側）: e621 が `latest.json` に残るため `score_topics()` が無駄にスコアリングし続ける、merge ドリフトも残存
- `collect_e621()` 側の削除のみ: 直前データ（`prev`）の merge 継承経路から e621 が再混入するため不十分（回帰テスト `test_e621_from_previous_never_inherited` で実証）

**Impact**:
- `scripts/fetch_topics.py`: `NON_TREND_SOURCES` 新設、`collect_e621()` 戻り値 `list[dict]`→`int`、`main()` の `all_topics.extend` 廃止、出力前フィルタ 3 行
- `scripts/tests/test_fetch_topics.py`: e621 を前提とする 3 テストを reddit 例へ改名、回帰テスト `test_e621_from_previous_never_inherited` 新規
- `scripts/tests/test_generate_article.py`: 1 テストの例を e621→reddit
- `scripts/generate_article.py`: 不変（:2321 / :2427 の e621 参照は防御的残存として維持）
- `scripts/genre_score.py`: 不変（`PROTECTED_SOURCES = {"e621"}` は版権エントリ保護のため維持）
- `data/topics/*.json`: 12 ファイルから e621 一次性除去（-7728 行）
- `data/genre_scores/topics.json`: 放置（派生キャッシュ、次回 `score_topics()` で再生成）
- pytest 349 passed

## 2026-10-10: トレンドソース品質（ANN whitelist + Crunchyroll一時無効化 + TTL誤検知修正）

**Decision**: (1) `_parse_entertainment_page()` に source 別 URL whitelist（`ENTERTAINMENT_ARTICLE_PATTERNS`: ANN = `^/(?:news|review|guide|interview|profile|gallery)/\d{4}-\d{2}-\d{2}/`）を導入し、`urllib.parse.urljoin(base_url, href)` で相対リンクを絶対 URL 解決（`javascript:`/`mailto:`/`#` スキップ、URL 重複除去、上限 15 件）。(2) Crunchyroll を `ENTERTAINMENT_HTML_SOURCES` から一時無効化（静的 HTML に記事 0 件・JS 描画・RSS 404）。(3) `_check_per_source_ttl()` で他カテゴリ専属 source（トピックあり・要求カテゴリ 0 件）を `expired=False`（自動 fetch トリガーしない）、トピック 0 件 source（完全失敗）は従来どおり `expired=True` 維持（自愈保持）。(4) `by_category`/`all` の merge 構造ドリフト（pokemon 旧 7 件）は known-issues.md 記録のみで不変更。

**Reason**: (1) trend topics 実効化後のライブ検証で、ANN パース結果（`latest.json` の Crunchyroll News 15 件）が全件ナビ・フッター系の非記事 URL（記事本文 0 件）であり、スコアリング・スニペット注入が汚染されることを確認。記事パスは 5 種プレフィックス + 日付形式で閉集合だが、ナビ URL は開放集合のため whitelist 方式を採用。(2) Crunchyroll の静的 HTML には記事が 0 件（JS 描画）であり、収集してもゴミのみ。(3) `fetched_at` は source 横断で共有のため、kemono 実行時に e621（pokemon 専属）/GitHub（tech 専属）が「古い」だけで誤検知され、毎回の自動 fetch トリガーで API クォータを無駄消費していた。(4) merge ドリフトはカテゴリ単位継承と source 単位継承の構造差が原因で、単独修正は merge ロジックの再設計が必要。影響は低（注入は score しきい値でフィルタ）のため記録に留める。

**Rejected Alternatives**:
- ANN の blocklist（ナビ URL 除外）: ナビ・フッター URL の集合は開放的で新しいゴミが随時出現する一方、記事パスパターンは閉集合であり whitelist の方が堅牢
- Crunchyroll を維持して JS 描画対応・代替フィード探索: headless browser かフィード探索が必要で効果（ゴミ 15 件 → 0 件）に見合わない。一時無効化とし、手段が見つかったら後日再追加（backlog P3）
- TTL チェックで他カテゴリ専属 source を無条件スキップ: 「トピック 0 件 = 完全失敗」の source は自愈のため `True` 維持が必要であり、2 者を区別する条件分岐が必要だった
- merge 構造ドリフトの単独修正: 影響が低（score しきい値でフィルタ）かつ merge ロジックの再設計が必要のため、known-issues.md に記録し P3 へ保留

**Impact**:
- `scripts/fetch_topics.py`: `ENTERTAINMENT_HTML_SOURCES` から Crunchyroll 削除、`ENTERTAINMENT_ARTICLE_PATTERNS` 新設、`_parse_entertainment_page()` 書き換え（urljoin + whitelist + 重複除去 + 上限15件、`base_url` パラメータ追加）、ヘッダ docstring 更新
- `scripts/generate_article.py`: `_check_per_source_ttl()` 精緻化（他カテゴリ専属 source は `False`、完全失敗 source は `True`）
- `scripts/tests/`: test_fetch_topics に `TestParseEntertainmentPage` 7件 + fixture 更新、test_generate_article に TTL 2件新規 + 既存1件アサート更新
- `data/topics/latest.json`: Kemono 10 件 + Crunchyroll News 15 件のゴミ除去（total 124 → 99）
- pytest 348通過（+9）。ライブ fetch で ANN 14 件・全件正規記事絶対 URL 確認。TTL dry check で kemono 不トリガー（修正前は毎回トリガー）・pokemon の真の陳腐化 4 件は正検知
- 既存正常部分への影響なし: whitelist 対象は ANN のみ（GameSpot/IGN は RSS パース経路・e621/GitHub は別関数）、TTL の変更は「他カテゴリ専属 source がトリガー対象から除外」されるのみ（完全失敗の自愈・要求カテゴリ内の陳腐化検出は不変）

## 2026-10-10: RSS description の取得・活用（backlog P2 #1, #5 統合）

**Decision**: `fetch_rss()` に description 抽出を追加し、`latest.json` 保存 → `score_topics()`（title+description[:200] でスコアリング）→ `_append_trending_topics()`（description[:100] スニペットを「—」区切りでトレンドブロック注入）の全データフローを実装。切り詰めは段階別（保存 300 / スコアリング 200 / 注入 100）。抽出順は RSS 2.0: `content:encoded` → `description`、Atom: `content` → `summary`。GameSpot/IGN は実測で正規 RSS フィードのため HTML パースから `fetch_rss()` へ切り替え、ANN（RSS 404）/Crunchyroll は HTML パース維持（description=""）。全エンタメソース失敗時のフォールバック `STORY_INSPIRATION_THEMES`（未定義・NameError）を内蔵テーマ8件（title+description）の定数定義で修正。

**Reason**: (1) kemono_story モードでは e621 がストーリーインスピレーションから除外され、残り候補（エンタメニュース・GitHub）が title のみの score=0-1 で物語テーマに反映されない問題（backlog P2 #1）。(2) description を取得しても保存されなければ下流（ジャンル判断・記事生成）で活用できないため #5 と #1 を1タスクに統合。(3) GameSpot/IGN は HTML パース扱いで description を捨てていたが、実測（2026-10-10）で両方とも正規 RSS 2.0（description あり）だったため正規 RSS パースへ。(4) `STORY_INSPIRATION_THEMES` の NameError は `main()` の try/except で吞まれ、全ソース失敗時に0件になる沈黙障害だったため恒久修正。

**Rejected Alternatives**:
- GitHub 収集に description 別フィールド追加: title が既に `f"{full_name}: {description}"` で description を埋め込んでいるため、別フィールド追加は二重計上になる
- ANN を RSS パースへ変更: `https://www.animenewsnetwork.com/feeds/news` が 404（RSS 不存在）のため HTML パース維持
- description を保存せずスコアリング時のみ利用: 記事生成時のスニペット注入（下流の再利用）が不可になる
- source 名（"GameSpot RSS"/"IGN RSS"）の変更: per-source TTL（`_check_per_source_ttl`）のキーとなるため維持

**Impact**:
- `scripts/fetch_topics.py`: `_clean_rss_description()` / `_rss_item_description()` / `_atom_entry_description()` 新設、`fetch_rss()` / `collect_rss_feeds()` に description、`ENTERTAINMENT_RSS_SOURCES` / `ENTERTAINMENT_HTML_SOURCES` 分離、`collect_entertainment_trends()` 書き換え、`STORY_INSPIRATION_THEMES` 定数定義
- `scripts/genre_score.py`: `score_topics()` のスコアリング入力を title+description[:200] に変更
- `scripts/generate_article.py`: `_append_trending_topics()` にスニペット注入 + `selected_items` ログに description[:200]
- `scripts/tests/`: 新規24件（fetch_topics 17 / genre_score 3 / generate_article 4）。`test_real_apis.py` に GameSpot/IGN フィード + description 出力
- pytest 339通過（+24）。`test_real_apis.py --save` で GameSpot/IGN の description 出力確認（`api_test_20261010_074140Z.json`）
- 次回 `deploy.yml` 実行時に `score_topics` の全件再スコアリング発生（入力テキスト変化によるキャッシュキー変化、一次性コスト）

## 2026-10-10: アフィリエイト商品推薦の書籍偏りの中性化（書籍例は維持）

**Decision**: プロンプトテンプレート3種（`default.txt` / `ai_deep.txt` / `kemono_story.txt`）と `generate_article.py:694` 注入行を、「書籍」が先頭・単独例にならないよう**例の順序入れ替えと複数例化**で中性化する。例から「書籍」を削除せず、「カテゴリ構成を多様化せよ」「書籍に限定しない」等の禁止指示・否定表現も追加しない。kemono プロンプトの「実在作品を1つ選定」→「実在商品を1つ選定」（選定対象の中性化）、category 例は書籍を末尾へ順変（default/ai_deep: ソフトウェア, ツール, ガジェット, 書籍, フィギュア, ゲーム等 / kemono: フィギュア, グッズ, BD, ゲーム, 書籍等）。

**Reason**: (1) ユーザー報告 + 実測: 直近記事の商品カード約34件中約6割が書籍・漫画・アートブック（BEASTARS ×6、ケモノキャラクター図鑑公式ガイド ×3、アートブック ×4）。(2) LLM はプロンプト内の例を強く模倣するため、Frontmatter 例の1件目・唯一の例・category 列挙の先頭が「書籍」だと商品選定が書籍にアンカーされる。(3) ユーザー指示: 書籍自体は正規の商品カテゴリ（テック記事でも自然）のため、修正は「削除」ではなく「順序」で行う。(4) Gemini 商品名は楽天API検索カスケード（`_rakuten_api_keywords()`）にも波及するため、プロンプト段階の修正で商品カードと API カードの双方を改善できる。

**Rejected Alternatives**:
- 「書籍」を例・カテゴリ列挙から削除: ユーザー指示「書籍自体は別にあっていい、プロンプト側もやはり書籍は例として残す」に反する
- 「カテゴリ構成を多様化せよ」「書籍に限定しない」等の禁止指示を追加: ユーザー指示「そんな記載は要らない」。明示的な否定指示はプロンプトノイズになる可能性がある
- `_KEYWORD_ENHANCEMENT` / `_improve_keyword`（フォールバック検索リンクキーワード）の併せて修正: Gemini 商品名とは別メカニズムであり、今回の偏りの原因ではない
- 既存記事の遡及書き直し: 再生成コストが高く、新プロンプトで新規記事は自然に改善するため見送り

**Impact**:
- `scripts/prompts/default.txt`: 6箇所（例入れ替え2・比較表例+1行・Frontmatter 例入れ替え・category 列挙2）
- `scripts/prompts/ai_deep.txt`: 3箇所（例入れ替え + AI開発フレームワーク例追加・Frontmatter 例入れ替え・ルール文言の順変）
- `scripts/prompts/kemono_story.txt`: 4箇所（関連グッズ・書籍・Frontmatter 例にグッズ項目+1・実在作品→実在商品・category 列挙順変）
- `scripts/generate_article.py`: 注入行1行の語順のみ（書籍・ゲーム・グッズ → ゲーム・書籍・グッズ）
- pytest 315通過。変更ファイルが deploy-only.yml の paths に該当しないため自動デプロイなし・deploy 確認不要
- 効果の観察: 次回 deploy 実行の商品カードのカテゴリ分布

## 2026-10-10: 世界設定の2段階拡大（12種・アンカワーク基準）

**Decision**: kemono_story の世界設定を7種→12種に拡大。追加: `isekai`（異世界、10）/ `modern`（現代、10）/ `space_opera`（スペースオペラ、7）/ `dungeon_crawl`（ダンジョンクライム、6）/ `historical`（歴史、5）。既存再配分: fantasy 30→21 / slice_of_life 22→10 / sf 15→8 / cyberpunk 12→7 / adventure 8→7 / fantasy+sf 8→4（合計100維持）。ファンタジー族（fantasy+isekai+dungeon_crawl+fantasy+sf）は41/100に拡大。`WORLD_SETTING_GENRE_MAP` に5件追加（isekai/dungeon_crawl→`[fantasy, action]`、modern→`[slice_of_life, action, mystery]`、space_opera→`[sf, action]`、historical→`[historical]`）。スコアリングgenreは `historical` のみ新設（6→7種、専用instruction）し、未デプロイの6種変更と**同バッチ**に集約（一次性の全再スコアリングは次回 deploy 1回のみ）。追加基準を「ニッチでないか」から「ケモノに独立世界を定義するアンカワーク存在＋明確に異なる物語を生む」に変更。

**Reason**: (1) ユーザー指摘: 現代人獣社会（furry 界で最も一般的な舞台、Zootopia 系）と時代・史前設定（史前獣人・戦国獣人）が表現不能だった。(2) 「ファンタジー・異世界方面のジャンルが少ない」— 異世界は読者目線では独立したラベルであり、`fantasy` 単独では「転生・異世界冒険」の読者意図を表現できない。(3) ポケモンの不思議のダンジョン的世界（モンスター主役＋ダンジョン攻略）は `adventure`（探索・宝探し）と明確に異なる。(4) Star Fox 系の宇宙冒険は汎用 `sf` とは異なる読者期待を持つ。(5) ユーザー指摘により「ニッチ」を除外理由から排除（ただし細分化しすぎも不好のためアンカワーク基準で制御）。

**Rejected Alternatives**:
- メカ / ポストアポカリプス / スポーツの世界設定追加: 独立したケモノ世界のアンカワークがなく、既存世界のバリアント（space_opera 内のメカ要素 / sf+action / slice_of_life+action）で表現可能。需要が観測されたら後日追加
- `historical` を新 genre として採点せず `[fantasy, action]` へ弱マッピング: 時代系トレンド（歴史ニュース等）が `historical` 世界に優先選択されない。未デプロイ変更と同バッチ化で追加コストはゼロ（一次性再スコアリング回数は不変）のため、専用 genre 採用
- `space_opera` / `isekai` / `dungeon_crawl` に専用採点 genre を追加: 既存 genre の複合マッピングで十分（sf+action / fantasy+action）。genre 増加は1callあたりの入トークン増と維持コスト

**Impact**:
- `scripts/genre_score.py`: `GENRE_INSTRUCTIONS` +historical、`DEFAULT_GENRES` 7種化
- `scripts/generate_article.py`: `WORLD_SETTING_WEIGHTS`（12種）/ `WORLD_SETTING_GENRE_MAP`（12件）/ `_KEMONO_WORLD_TAGS`（12件）
- `.github/workflows/genre-score.yml`: genres デフォルト入力 7種化
- `scripts/tests/`: GENRE_MAP テスト+5、`test_weights_sum_to_100` / `test_all_settings_have_genre_map_entry` 新設、`test_world_setting_in_options` 12文字列化、`test_default_genres` 7種化
- pytest 315通過、実APIスモーク: "戦国武将"→historical:80、"スターフォックス"→action:69/sf:40
- 次回 `deploy.yml` 実行時に 7-genre 版の全件再スコアリング（一次性コスト）

## 2026-10-10: ストーリー系ジャンルの一括拡大（世界設定7種・スコアリングgenre6種）

**Decision**: kemono_story の世界設定を4種→7種（+`cyberpunk` 12 / +`adventure` 8 / +`mystery` 5。fantasy 35→30 / slice_of_life 25→22 / sf 20→15 / fantasy+sf 20→8 で合計100維持）、スコアリングgenreを4種→6種（+`slice_of_life` / +`mystery`、専用instruction）へ**一括変更**。`WORLD_SETTING_GENRE_MAP` に `cyberpunk`→`[cyberpunk]` / `adventure`→`[action, fantasy]` / `mystery`→`[mystery]` を追加し、`slice_of_life` の `[action]`→`[slice_of_life]` に修正。

**Reason**: (1) 既存の `cyberpunk` genre が全トレンド・版権に毎回スコアリングされるのに世界設定から未使用で、コストのみの無駄だった。(2) `slice_of_life` → `[action]` は「日常」世界のトレンド候補をアクション高スコア順にソートしてしまう意味逆転バグ。(3) キャッシュキーが `SHA256(text|sorted genres)` のため genre 追加は全エントリ失効→次回 `deploy.yml` の `score_topics()` で全件再スコアリング（138 calls ≈ 31s）という一次性コストになる。ユーザー指示で追加するなら1回に集約する方針を採用。clef-flash の採点はgenre間独立（合計100正規化なし）のため、genre追加は既存genreの判別力を希薄化しない（コストは1callあたり入トークン微増のみ、6genreで1021 tokens ≈ 8 neurons）。

**Rejected Alternatives**:
- comedy / romance / horror 等の追加genre: いずれの世界設定からも未使用のため、`cyberpunk` と同じ「スコアリング済但未使用」の無駄を再現する。将来 world setting を追加する際にくる回で genre 追加（再スコアリング1回分が発生するが、必要になった時点でのみ支払う）
- `adventure` を独立 genre として採点: 既存 `action` + `fantasy` の複合マッピングで十分カバーでき、新genreの追加コスト・維持コストを避けられる
- Phase 1（既存genreのみ使用）と Phase 2（新genre追加）を分けて2回実施: 138件の全再スコアリングが2回発生する一次性コスト。無料枠（10,000 neurons/日）内で収まるため1回に集約

**Impact**:
- `scripts/genre_score.py`: `GENRE_INSTRUCTIONS` +2、`DEFAULT_GENRES` 6種化
- `scripts/generate_article.py`: `WORLD_SETTING_WEIGHTS` / `WORLD_SETTING_GENRE_MAP` / `_KEMONO_WORLD_TAGS` 更新
- `scripts/tests/`: `TestWorldSettingGenreMap` 3件追加、`test_world_setting_in_options` 新3文字列、`test_default_genres` セット更新、`TestScoreTopics` のモックpayloadを `DEFAULT_GENRES` 派生化（4件）
- 次回 `deploy.yml` 実行時に全件再スコアリング（一次性コスト、138 calls ≈ 31s、無料枠内）
- pytest 308通過、実APIスモーク: "攻殻機動隊"→sf:81/cyberpunk:81/mystery:34/slice_of_life:16、"日常 四葉の妹"→slice_of_life:85（新instructionの動作確認）

## 2026-10-09: kemono_tags の構造化データ化（結合・分割往復の廃止）

**Decision**: `generate_article.py` の kemono パラメータを「構造化データ + プロンプト表示文字列」の2層構成に変更し、タグ生成を `_build_kemono_tags()` に集約する。`CHAR_TYPE_WEIGHTS` の値を体型タグのリスト化（`["獣人","動物"]` 等）、`_KEMONO_WORLD_TAGS`（世界設定→タグリスト）・`_KEMONO_EXTRA_TAGS`（追加設定→タグ文字列）を一次データとし、従来プロンプト向けに使用していた結合文字列（`char_type` = `" / " 結合`、`world_setting` = `と` 結合、`extra_text` = `、` 接頭）はこれらから派生生成する。`_randomize_kemono_params()` は `char_types` / `world_tags` / `extra_tag`（構造化）と従来キー（表示用）の両方を返す。`_kemono_affiliate_keywords` / `_rakuten_api_keywords` も `world_tags` を直接使用し、`split("と")` を廃止。併せて `target_genres` 参照のキー不一致バグ（表示文字列 `world_setting` → キー `world_setting_key`）を修正。

**Reason**: 最新記事（2026-10-09-223016）の tags が `["ケモノ","動物と獣人のハーフ・動物","ファンタジー","BL","、ライバル関係"]` と不自然だった。原因は2つ: (1) ジャンルは `split("と")` で分割していたが体型タグは `replace(" / ","・")` のみで分割漏れ、(2) `extra_text` はプロンプト文（「…からランダムにテーマを選択してください」）への自然な接続のための「、」接頭であり、そのままタグに混入していた。根本原因は「結合文字列を一次データとして扱い、用途ごとに分割・結合を往復させる」設計。スクリプト内で最初から構造化データを保持しておけば往復処理自体が不要になる。併発発覚: `WORLD_SETTING_GENRE_MAP` のキーは `world_setting_key` だが `world_setting`（表示文字列）で参照していたため、genre-integration 実装のジャンルベーストレンド優先選択がサイレント無効化されていた（恒常的に `None`）。

**Rejected Alternatives**:
- タグブロック側の `split(" / ")` 追加のみ: 体型・ジャンル・追加設定で分割文字が異なる（` / ` / `と` / `、`）ため、各所で個別の分割ロジックが残り継続的に壊れる。結合文字列の一次データ化が根本原因
- `extra_text` から「、」を除去しタグ側で補う: プロンプト側の文脈（「異性愛、ライバル関係からランダムに… 」）が不自然になるため、「、」接頭はプロンプト向け表示値として維持し、タグ用に別途カンマなし値を保持
- 旧形式タグを持つ既存記事の遡及修正: 記事の再生成コストが高く、旧タグページへのリンク切れリスクがあるため未実施（最新記事1件のみ修正）

**Impact**:
- `scripts/generate_article.py`: `CHAR_TYPE_WEIGHTS` リスト化、`_KEMONO_WORLD_TAGS` / `_KEMONO_EXTRA_TAGS` 新設（旧結合文字列は派生）、`_randomize_kemono_params` 戻り値2層構成化、`_build_kemono_tags()` 新設、`generate_post` タグブロック置換、`_kemono_affiliate_keywords` / `_rakuten_api_keywords` を `world_tags` 使用へ、`target_genres` キー不一致修正
- `scripts/tests/test_generate_article.py`: 13テスト追加（`TestBuildKemonoTags` 7 / `TestKemonoAffiliateKeywords` 3 / 整合性2 / char_types1）、旧テスト更新4件
- `src/content/posts/2026-10-09-223016-auto-post.md`: tags 修正（`動物と獣人のハーフ` / `動物` / `ライバル関係` に分割・清浄化）
- pytest 297通過、`npm run build` 131ページ成功（新タグページ `/tags/動物と獣人のハーフ/`・`/tags/ライバル関係/` 生成確認）
- 次回以降の記事生成で `target_genres`（ジャンルベースのトレンド・版権優先選択）が初めて実効する

## 2026-10-09: リファインプロンプトに画像プロンプト形式チェックを追加

**Decision**: `refine_story.txt`（【11. 画像プロンプト形式チェック】新設）と `refine_tech.txt`（【10. 画像プロンプト形式チェック】新設）に形式チェック節を追加し、2-passリファイナーの役割に「画像生成プロンプトの書式が正しいことの確認」を追加。修正権限は**形式のみ**に厳密限定: 括弧の欠落・無効なcharacter_N参照（有効IDへ）、自然言語句→簡潔タグ、masterpiece等品質タグの削除、日本語・全角→英語・半角、表情欠落時の1-2タグ（Danbooru実在タグ・場面感情に一致）追加。変更不可: シーンの選定・配置・枚数、シーンキーワードの意味、表情の意図、記事本文。「タグ内英語は変更しない」ルール（旧82行目）は「内容として書き換えない（形式誤りは新節に従って修正する）」へ書き換え、構成維持節の例外注記を併記。

**Reason**: 「画像プロンプトに場面ごとの表情/ポーズ指定追加」(2026-10-09) の実Gemini検証で書式逸脱（自然言語句1件+2件）を観測し、現状のリファイナー（画像プロンプトを変更しないよう明示指示）では無修正通過、Python側フォールバック解析で黙って劣化することを確認。リファイナーは抽出・画像生成より前に走るため修正が `compose_image_prompt` へ伝播し、追加API呼び出しなし。観測された逸脱は意味的（自然言語句・表情と場面の一貫性）で正規表現では完全捕捉不能のためプロンプトによるチェックが適切。

**Rejected Alternatives**:
- B: Python構造化検証（`validate_image_prompts()`）のみ: 信頼性・テスト性は高いが意味的品質（自然言語句・Danbooru実在性）を判定不能。今回は未採用（逸脱頻度定量化の警告ログとして後日追加可能）
- C: A+Bハイブリッド: 最も堅牢だが作業量最大。Aの効果評価後に判断
- リファイナーによる画像プロンプト全面書き換え: 「キャラ及びシチュエーション再現度を最優先」原則に反。LLMが正当な形式を不正に書き換えたりシーン内容を書き換えたりするリスク
- 現状維持: 2026-10-09「画像プロンプトのキャラ別表情/ポーズ指定」の Impact 行（`refine_story.txt`: 変更なし）を本決定で取り下げ・取代

**Impact**:
- `scripts/prompts/refine_story.txt`: 【11. 画像プロンプト形式チェック】新設、82行目書き換え、【12. 構成と形式】番号振り直し＋例外注記、自己検証前チェックリスト1項目追加
- `scripts/prompts/refine_tech.txt`: 【10. 画像プロンプト形式チェック】新設、【9. 見出し・構成】の「各種タグ」例外注記、【11. 情報追加に関する制限】番号振り直し
- 適用対象: refine_story = kemono_story (novel/story)、refine_tech = default/ai_deep
- pytest 200通過 (3.28s)。リファイナーの実Gemini挙動検証未実施

## 2026-10-09: Windowsコンソールエンコーディング対策の統一（stdio reconfigure）

**Decision**: エントリスクリプト冒頭（import直後・最初のprint前）に `if sys.platform == "win32":` ガード付きで `sys.stdout.reconfigure(encoding="utf-8")` / `sys.stderr.reconfigure(encoding="utf-8")` を配置し、既存のワークアラウンドをこの方式に統一。`fetch_topics.py`（無効な `os.environ["PYTHONIOENCODING"]` 設定を置換）・`generate_article.py`（新設）・`fix_affiliate_links.py`（`io.TextIOWrapper` 差し替え方式から移行、`import io` 削除）・`fix_descriptions.py`（新設）の4エントリに適用。`_safe_print()`（fetch_topics / test_real_apis）はUTF-8下ではフォールバックが発火しない防御コードとして維持。

**Reason**: Kilo CLI が stdout をキャプチャ（パイプ扱い）すると Python はコンソール直結時の `WindowsConsoleIO`（UTF-8対応）を使わず**ロケール cp932 にフォールバック**し、絵文字等非収録文字で `UnicodeEncodeError`・cp932バイト列のUTF-8解读で文字化けする（2026-10-09 実測で確認）。`PYTHONIOENCODING` はインタプリタ起動時のみ参照されるため実行時設定は現在プロセスに無効（`fetch_topics.py` 旧コードの欠陥）。`reconfigure()` は既存オブジェクトをインプレースで書き換えるため、旧方式（TextIOWrapper差し替え）の旧stream参照分裂・二重ラッパー問題を回避でき、環境変数に依存せず別マシンでも確実に効く。`test_real_apis.py:33-36` に既に同じ方式があり、コードベースの先例として採用。

**Rejected Alternatives**:
- `os.environ["PYTHONIOENCODING"]`（実行時設定）: 現在プロセスに無効（起動時のみ参照）。子プロセス専用修正
- `io.TextIOWrapper` 差し替え: 有効だが旧streamを保持するコードがcp932書き続行する分裂状態の恐れ、同一バッファ上の二重ラッパー
- `_safe_print()` のみ: 逐次的な例外処理で出力先が2系統に分裂。根本対策にならない（防御として維持）
- 環境変数 `PYTHONUTF8=1` のみ: 運用ベースとして `workflow-test-procedure.md` に記載済みだが、env未設定環境（別マシン・CI・新セッション）では無効になるためコード側の自己完結と併用
- 共有ヘルパモジュール化: スクリプトは「単体実行前提」の独立設計のため、3行ブロックの重複を許容（`hf-space/app.py` は HF Space=Linux 実行のため対象外）

**Impact**:
- `scripts/fetch_topics.py`, `scripts/generate_article.py`, `scripts/fix_affiliate_links.py`, `scripts/fix_descriptions.py`: reconfigureブロック追加/置換
- `docs/ai/workflow-test-procedure.md`: 「ローカル実行注意」セクション追加（`$env:PYTHONUTF8="1"` 現セッション設定・`python -X utf8` 1回限り代替）
- pytest 200通過、パイプ環境スモークテストで utf-8 化確認

## 2026-10-09: 画像プロンプトのキャラ別表情/ポーズ指定

**Decision**: kemono_story の画像プロンプトに場面ごとの表情/ポーズ指定を追加。形式は `[character_1: blushing, smile, character_2: frown, narrowed eyes] scene`（コロン=キャラ別）/ `[character_1, character_2, smile] scene`（コロンなし末尾エントリ=共有）/ `[character_1, character_2] scene`（legacy後方互換）の3種。`compose_image_prompt` が括弧をパースし、表情/ポーズタグを各キャラクター外見の直後にインターリーブ。全キャラの表情が同一の場合はキャラブロックの後に1回だけ出力（dedupe）。キャラ別ポーズは括弧内、相互作用ポーズ（hugging, facing each other 等）はシーンキーワードで指定。

**Reason**: 既存の画像プロンプトに表情データがなく、生成画像の2匹が同じ・無関係な表情になりストーリー再現度が低下。Illustrious系（Nova-Furry-XL）のベストプラクティス調査で、表情タグは各キャラの描述の直後（隣接性ヒューリスティック）がキャラへの結合に最も有効と判明。

**Rejected Alternatives**:
- 合成順序の変更（quality先頭化等）: ユーザーが「キャラ及びシチュエーションの再現度を最優先」と明示。既存順序（被写体数→キャラ→シチュエーション→artist→quality→style）を維持
- `BREAK` / `(tag:1.2)` 重み付け: パイプラインは素のdiffusers（Compelなし）でパースされない
- テンプレートに表情例の長いリスト: 22行目の「Danbooru互換タグ形式」ルールと冗長（ユーザー修正で削除）。「実在タグ」要求＋具体例2つで十分と判断
- `app.py` 変更: HF Spaceアプリは最終プロンプト文字列をそのまま受け取るため、`compose_image_prompt` 側で合成

**Impact**:
- `scripts/prompts/kemono_story.txt`: ルール2項目（キャラ別表情・シーンキーワードの構成）追加＋例4箇所更新
- `scripts/generate_article.py`: `_parse_image_prompt_targets()` 新設、`compose_image_prompt` をインターリーブ合成に変更
- `scripts/tests/test_generate_article.py`: テスト5件追加（個別/単独/dedupe/共有/legacy）
- `refine_story.txt`: 当時変更なし（82行目の「タグ内英語は変更しない」が新形式も維持するため）→ 同日の「リファインプロンプトに画像プロンプト形式チェックを追加」で形式修正許可へ取代

## 2026-10-04: 重複YAMLキーの自動修復ロジック

## 2026-10-06: 画像生成上限を3枚→8枚に増加

**Decision**: `MAX_INLINE_IMAGES` のデフォルトを 2 → 7 に増加（ヘッダー含めて合計最大8枚）。ストーリー系（kemono_story）は各章ごとに画像を配置する指示に変更。技術系（default, ai_deep）も挿絵上限を 2 → 7 に増加。

**Reason**: HF ZeroGPU の `duration=20` はタイムアウト予約であり、実稼働時間分のみ消費されることを確認。初回9秒、ウォーム2秒/枚で1日約101枚生成可能。以前の3枚/記事ではクォータの大幅な余剰があった。

**Rejected Alternatives**:
- 画像数を維持: クォータの余剰を無駄にする
- Pollinations.ai への完全移行: HF の画質が安定しているためプライマリは維持

**Impact**:
- `scripts/generate_article.py`: `MAX_INLINE_IMAGES` デフォルト 2 → 7
- `scripts/prompts/kemono_story.txt`: 画像選出ルールを「合計最大8枚、各章に1つ以上」に変更
- `scripts/prompts/default.txt`: 挿絵上限 2 → 7
- `scripts/prompts/ai_deep.txt`: 挿絵上限 2 → 7
- `docs/ai/api-rate-limits.md`: HF ZeroGPU の実稼働時間消費を反映

**Decision**: `generate_article.py` の `validate_and_fix_frontmatter()` 内で、PyYAML `safe_load` 検証より前に重複キーチェックを无条件で実行。キャラクターキーの命名規則を `character_N` に強制し、AI が出力したキャラクタータイプ名（例: `少年:`）を自動リネーム。

**Reason**: AI がプロンプト指示の `character_1`/`character_2` を無視し、キャラクタータイプ名をキーとして出力するため、2人以上で重複し Astro/Vite が `duplicated mapping key` でビルド中断。PyYAML の `safe_load` は重複キーでエラーを発生させないので、事前チェックが必須。

**Rejected Alternatives**:
- AI プロンプトの修正のみ: AI が指示を無視する根本問題は解決しない
- `safe_load` のみの検証: 重複キーを検出できない
- ビルド失敗後の手動修正のみ: CI/CD パイプラインが毎度ブロックされる

**Impact**:
- `scripts/generate_article.py`: `_fix_duplicate_yaml_keys()` と `_is_character_like_key()` ヘルパー関数を追加、`validate_and_fix_frontmatter()` に无条件の重複チェックを組み込み
- `scripts/tests/test_generate_article.py`: 重複キー修復のテストケースを追加



