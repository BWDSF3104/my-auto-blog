# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

# Completed Plans

- [2026-10-05] ブランドカラー統一: `global.css` + `PostLayout.astro` のハードコードHEXをCSS変数(26変数)に集約。既存カラー値は不変。変更前後のビルド出力比較で45色完全一致を確認。ビルド成功 (110ページ)
- [2026-10-05] モバイルハンバーガーメニュー: `Header.astro` に640px未満用のドロップダウンメニューを追加。検索、ダークモード、記事一覧（`#main-content`アンカー）、タグ一覧、About、RSS、Privacy を含む。外部クリックで閉じる。ビルド成功 (110ページ)
- [2026-10-05] ヒーローセクション: `Header.astro` にグラデーション背景、ステータスバー（記事数/タグ数/最新更新日）、アクションボタンを追加。統計情報は `import.meta.glob` でビルド時計算。レスポンシブ対応 (3カラム→sm以上)。ビルド成功 (108ページ)
- [2026-10-04] カテゴリーカード: フロントページにタグ別記事数のセクションを追加。`CategoryCards.astro` コンポーネント新規作成。既存 `tagColors.ts` の12色パレットを再利用。記事数順にトップ12タグをスリムなアコーディオン型で表示（デフォルト閉じ、ボタンで展開）。ビルド成功 (108ページ)

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。

- [2026-10-04] Plausibleアクセス解析の有効化: `Layout.astro` のPlausibleスクリプトを`BWDSF3104.github.io`ドメインで有効化。ビルド成功 (108ページ)
- [2026-10-04] 目次 (TOC) のレスポンシブ対応: デスクトップは既存のstickyサイドバー維持、モバイルにアコーディオン型折りたたみTOCを追加。`PostLayout.astro` にトグルボタン、chevron SVG、JSトグルハンドラー (aria-expanded) を実装。`headings`変数のスコープ修正。ビルド成功 (108ページ)
- [2026-10-04] 重複YAMLキーによるビルド失敗の修正: AI が出力した重複YAMLキー（`少年:` 等）による Astro ビルド失敗を解決。`generate_article.py` に自動修復ロジック実装、破損記事を手動修正、テスト110件全通、ビルド成功、デプロイ完了
- [2026-10-02] Backlog P0 実装 (B1-B4): 9件の P0 バックログを 4 バッチで実装。B1: Back to Top FAB + Skip Navigation リンク + `.skip-link` CSS。B2: コードブロックコピーボタン (Clipboard API) + 画像 Lazy Loading。B3: `src/lib/tagColors.ts` で 12 色パレットのタグ色 + `og:locale` + 動的 `og:image` メタデータ + `article:modified_time`。B4: Social Sharing (X, Hatena, LINE, Pocket) + Footer SNS アイコン (X, GitHub, RSS) + BreadcrumbList JSON-LD (index, page, tags)。ビルド成功 (94ページ)
- [2026-10-02] Reddit 代替ソースの追加: e621、Kemono API、RSS フィードを代替ソースとして追加。kemono/pokemon カテゴリのトピック収集を安定化。テスト134件全件通過
- [2026-10-02] 既存記事のアフィリエイトリンク一括置換: `scripts/fix_affiliate_links.py` で 15ファイル（48行）を `[text](url)` から `<a>` タグに置換。1ファイル試験→全体適用→ビルド成功 (94ページ)
- [2026-10-01] FAQPage schema + Speakable schema: 記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成（行単位ステートマシンパーサー）。記事冒頭段落をSpeakable JSON-LDとして出力。`generate_article.py` に `_extract_faq_pairs()` と `_extract_speakable_text()` を追加し、frontmatter にJSON文字列で記録。`PostLayout.astro` で条件付きJSON-LD出力。テスト134件全件通過、ビルド成功 (90ページ)

