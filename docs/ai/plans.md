# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

- [2026-10-11] Pythonスクリプトのリファクタリング（パッケージ分割+大関数分解）: `ast` 解析で `generate_article.py`（3561行・`generate_post()` CC81/325行）が大幅超過と判明。`scripts/article/` パッケージ（config/gemini/image/affiliate/trends/frontmatter/slug_links/meta）へ責務群を分離し `generate_article.py` を入口+パイプラインに縮約、`generate_post()` を8ステージ関数に分解。`fetch_topics.py::main()`（CC52）は関数抽出のみ（入口ファイル名は `deploy.yml` 参照のため不変）。関数移設とテストの `patch("generate_article.X")` 経路更新をセットで実施し、フェーズごとに pytest 緑で進行。設計判断: `decisions.md` 2026-10-11。詳細: `tasks/2026-10-11-python-refactor-package-split.md`

- [2026-10-11] コメント機能（Giscus）実装: 静的サイト（GitHub Pages）+ バックエンド/DB/SSR なしの前提から、コメントに Giscus（GitHub Discussions バックエンド・クライアントサイド iframe）を採用。`data-mapping="pathname"`（base `/my-auto-blog` で開発・本番の pathname が一致し同一 Discussion 共有）、テーマ同期は MutationObserver で `data-theme` 更新（`Header.astro` 無変更）、記事単位無効化は frontmatter `comments: false`、env 欠落時は early return でセクション非表示。`deploy.yml` / `deploy-only.yml` は `vars.PUBLIC_GISCUS_*`（4 値）で配線。タスクファイル 5 件: `tasks/2026-10-11-giscus-comments-github-setup.md`（手動: Discussions 有効化 + giscus app 導入）、`tasks/2026-10-11-giscus-comments-env-config.md`（手動: 環境変数登録）、`tasks/2026-10-11-giscus-comments-component.md`（AI: `GiscusComments.astro` + Layout 組み込み + `content.config.ts`）、`tasks/2026-10-11-giscus-comments-workflow-env.md`（AI: ワークフロー env 配線）、`tasks/2026-10-11-giscus-comments-verification.md`（AI: E2E 検証 + 本番デプロイ）。選定理由: `decisions.md` 2026-10-11。バックログ: P2 #4

# Completed Plans

- [2026-10-11] README を Astro スターター既定からプロジェクト説明へ書き換え: README が Astro Starter Kit 既定内容のままだったため、使用技術・生成フローを詳しく説明するものへ全面書き換え（6ステップの生成フロー図 + generate_article.py の11ステップ詳細、技術スタック / データソース表、環境変数表（変数名のみ）、プロジェクト構造、ローカル開発手順、CI/CD、テスト規則）。ユーザー指示により排除: 個人名、API キー値（環境変数は変数名のみ）、HuggingFace の具体的なリポジトリ名（「自社ホスト HF Space（ZeroGPU、SDXL パイプライン）」と一般表現）、ユーザー名入り URL（ベースパスのみ表記）。.env キー値断片と既知別子の全文正規表現スキャンで該当なしを確認、BOM なし UTF-8。コード変更なし（README のみ）のため pytest / build 不要。詳細: `docs/ai/tasks/2026-10-11-readme-rewrite.md`

- [2026-10-11] 記事末尾の生成情報に e621 からの使用データを載せる: e621 キャラクター特徴（参考キャラクター2投稿・人気版権・人気artist・データ時点）を「生成情報」セクションに表示。`_load_character_features()` を `_select_character_features()`（選出 dict 返却・None ならスキップ）/ `_format_character_features_instruction()`（指示文組立）に分割し、`generate_post()` で 1 回の選出をプロンプトと生成情報セクションの両方に渡す（同一データ保証）。`_build_generation_info_section()` に `e621_info` パラメータ＋「参考キャラクターデータ（e621）」ブロック追加（kemono_story 限定・e621 データが実際に使われるのは kemono プロンプトのみ）。CSS 追加なし（`.gen-info-dl` 流用）、既存記事影響なし。pytest 365 通過（新規10）、一時記事 build 検証で本文末尾配置・既定閉・TOC 非載入・実データ表示を確認。詳細: `docs/ai/tasks/2026-10-11-e621-generation-info.md`

- [2026-10-11] 全ファイル UTF-8 化検討（エンコード監査 + BOM 除去 + worktree 整理）: 2026-09-30 以前の旧記事 30 件が旧 PowerShell 経路由来の UTF-8 BOM+CRLF だったため新記事（BOM なし UTF-8）と不整合。新規生成経路は全スクリプト `encoding="utf-8"` 明示指定で新規 BOM 発生なしと確認した上で、BOM 付き 31 ファイル（旧記事 30 + `affiliate-link-context.txt`）をバイト列除去（CRLF 維持）。`affiliate-link-context.txt` はコード参照なし（grep 確認）のため影響なし。`safe-remove.ps1` の BOM は Windows PowerShell 5.1 が BOM なし .ps1 を ANSI 解析するため必須で維持。旧 worktree `hallowed-fedora`（ahead 0 / behind 330、CP932 文字化け deploy.yml 残存）をセッション停止→`git worktree remove`+`branch -d` で削除。`.gitattributes` による改行コード正規化（CRLF/LF 混在）は影響範囲が広いため backlog P3 #8 へ別タスク化。`npm run build` 135 pages 成功。詳細: `docs/ai/tasks/2026-10-11-utf8-encoding-audit.md`

- [2026-10-10] 記事末尾の「生成情報」セクション追加（トレンド情報＋キャラクターデータ）: 記事生成に使ったトレンド情報とキャラデータ（体型/世界設定/変身/関係性/追加設定＋キャラタグ）を折りたたみセクションとして記事の一番下に追加。ユーザー指示「生成情報の作成はPythonスクリプト側で行う」により `generate_article.py` が `<details class="gen-info">` HTML を生成し本文末尾に追記（frontmatter 拡張＋Layout 描画方式は不採用）。`_append_trending_topics()` は戻り値 3→4 タプル化（第4要素: クリーンなトレンドタイトル `"{title}（{source}）"` 形式）。`_KEMONO_TRANSFORM_LABEL` 新設（`transform_text` の「、」接頭文字列は表示不適のため）。新ヘルパー `_build_generation_info_section()`（表示要素なしなら空文字列＝非表示）。既存記事はバックフィル不要（セクションは本文に直接入るため）。h2〜h4 不使用のため TOC 非表示。`.gen-info` CSS は `PostLayout.astro` の `<style is:global>` に追加。pytest 355通過（新規6）、一時記事での build 検証で本文末尾配置・既定閉・TOC 非載入を確認。詳細: `docs/ai/tasks/2026-10-10-generation-info-section.md`

- [2026-10-10] e621 データのトレンド配管からの分離（キャラクター特徴集計のみ継続）: e621 はキャラクター特徴集計（`data/character_features.json`）専用データであり、トレンドトピックとして記事生成に注入すべきでないこと、かつ KI-20261010-01（`by_category`/`all` merge 構造ドリフト）の e621 項目残存が問題化していたため分離。`fetch_topics.py` に `NON_TREND_SOURCES = {"e621"}` 新設し、`collect_e621()` は収集・集計のみ継続（戻り値 `list[dict]`→`int`）、`main()` は `all_topics.extend` を廃止し出力構築前に `sources`/`merged_by_category`/`all_topics_merged` をフィルタ（直前データからの merge 継承経路もカバーするため出力直前ガードが必須）。`data/topics/*.json` 12 ファイルから e621 一次性除去（旧10件 total 99→94 / 最新2件 98→73、-7728行）。`generate_article.py` の e621 参照は防御的残存、`genre_score.py` の `PROTECTED_SOURCES` は維持、`data/genre_scores/topics.json` は派生キャッシュのため放置。pytest 349通過（回帰テスト `test_e621_from_previous_never_inherited` 新規）。詳細: `docs/ai/tasks/2026-10-10-e621-trend-separation.md`

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。
