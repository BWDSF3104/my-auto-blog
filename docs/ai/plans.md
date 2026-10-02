# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

# Completed Plans

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
古い計画は `plans-archive.md` に移動する。

- [2026-10-02] データソースのレート制限調査: 各APIのレート制限を調査・実測し `AGENTS.md` に記録。`test_real_apis.py` を独立スクリプトとして作成。テスト7/9通過 (Reddit 403, Bluesky 501 はAPI側規制)。`226f464`

- [2026-10-02] AGENTS.md のレート制限テーブルを docs/ai/api-rate-limits.md に分離 + fetch_topics.py 更新後の test_real_apis.py 検証ルールを追加: `628b46d`
- [2026-10-02] kemono/furry トレンド作品追跡の改善: e621 に rating:safe 制限を追加して NSFW フィルタ回避、furry/wolf/fox/rabbit の score 順クエリを追加して人気作品を追跡、Bluesky 検索キーワードを拡張
- [2026-10-02] 'pokemon' カテゴリの kemono_story から除外 + ランダムトレンド選択: kemono_story から 'pokemon' カテゴリを削除し、トレンド選択を「カテゴリごとに上位5件」から「全カテゴリをプールしてランダム2件」に変更。e621 の character/copyright タグを収集対象に追加してアフィリエイト製品推薦に活用

- [2026-10-01] ダークモード修正: `is:inline` 属性なしでクライアントサイドスクリプトが動作しない問題を `Header.astro`, `PostLayout.astro`, `tags/index.astro` に追加して修正。`PostLayout.astro` に `Header` コンポーネントのインポート、`dark:` 変種クラス、ダークモードCSSを追加して記事ページのダークモード対応を完了。ビルド成功 (90ページ)
- [2026-10-01] 記事ページダークモードの文字色コントラスト改善: `PostLayout.astro` の `<article>` に `dark:prose-invert` + 各要素の `dark:` 変種クラスを追加して本文の文字色を改善。ビルド成功 (92ページ)
- [2026-10-01] FAQPage schema + Speakable schema: 記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成（行単位ステートマシンパーサー）。記事冒頭段落をSpeakable JSON-LDとして出力。`generate_article.py` に `_extract_faq_pairs()` と `_extract_speakable_text()` を追加し、frontmatter にJSON文字列で記録。`PostLayout.astro` で条件付きJSON-LD出力。テスト134件全件通過、ビルド成功 (90ページ)
- [2026-10-01] canonical URL一貫性: slug変更時の301リダイレクト実装。`data/slug-redirects.json` で旧→新slugマッピングを記録。`generate_article.py` にslug変更検出・自動記録ロジック追加。`[...slug].astro` の `getStaticPaths` にリダイレクトルートを追加してAstroレベルの301リダイレクトを実装。sitemap整合性確認済み。テスト119件全件通過、ビルド成功 (90ページ)
- [2026-10-02] 既存記事のアフィリエイトリンク一括置換: `scripts/fix_affiliate_links.py` で 15ファイル（48行）を `[text](url)` から `<a>` タグに置換。1ファイル試験→全体適用→ビルド成功 (94ページ)
- [2026-10-02] Reddit 代替ソースの追加: e621、Kemono API、RSS フィードを代替ソースとして追加。kemono/pokemon カテゴリのトピック収集を安定化。テスト134件全件通過
