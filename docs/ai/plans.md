# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

- [2026-10-05] 既知問題修正 (KI-001, KI-002, KI-003):
  - KI-001: ハンバーガーメニューの「記事一覧」リンクを `#main-content` → `{baseUrl}` に変更
  - KI-002: ヒーローセクションの「最新記事を読む」を同上 + `page/[page].astro` に `id="main-content"` を追加
  - KI-003: `kemono_story.txt` の IMAGE_PROMPT 指示を強化（具体的なシーンの描写を要求）

# Completed Plans

- [2026-10-06] 画像プロンプト順序最適化: BASE_QUALITY_PROMPTを8→6タグ短縮、Illustrious系推奨順序に再配置（被写体数→キャラクター→シチュエーション→artist→品質→スタイル）。pytest 155通過、ビルド成功 (114ページ)。commit: `947009c`, `fbbb0ab`
- [2026-10-06] e621 artistタグ集計機能: CHARACTER_FEATURE_CATEGORIESにartist追加、unknown_artist除外、generate_article.pyに人気artist注入、art_style指示にartist名候補追加。pytest 155通過、ビルド成功 (110ページ)。commit: `2e960f3`
- [2026-10-06] 画像プロンプト指示をDanbooruキーワード形式に統一: `kemono_story.txt` にDanbooru互換全体指示新規追加、art_style指示に3-5タグ明記+例更新、character指示に種族例+服装1-2つ+5-8タグ制限、IMAGE_PROMPT挿入例・Frontmatter例を自然言語→キーワード形式、`DEFAULT_ART_STYLE`を5→3トークン短縮。pytest 155通過、ビルド成功 (110ページ)。commit: `db0641b`
- [2026-10-05] kemono_story プロンプトのPython側ランダム化: 6項目の重み付きランダム選択 (`_randomize_kemono_params`) + バリデーション (`_is_valid_kemono_combination`) を実装。`char_count=1` は `extra=clone` 時のみに制限。`char_count_desc` は 2人の場合 "バディ"/"ライバル"/"カップル" からランダム選択。テスト21件追加、全155件通過、ビルド成功 (110ページ)。commit: `2804bfd`
- [2026-10-05] ブランドカラー統一: `global.css` + `PostLayout.astro` のハードコードHEXをCSS変数(26変数)に集約。既存カラー値は不変。変更前後のビルド出力比較で45色完全一致を確認。ビルド成功 (110ページ)
- [2026-10-05] モバイルハンバーガーメニュー: `Header.astro` に640px未満用のドロップダウンメニューを追加。検索、ダークモード、記事一覧（`#main-content`アンカー）、タグ一覧、About、RSS、Privacy を含む。外部クリックで閉じる。ビルド成功 (110ページ)
- [2026-10-05] ヒーローセクション: `Header.astro` にグラデーション背景、ステータスバー（記事数/タグ数/最新更新日）、アクションボタンを追加。統計情報は `import.meta.glob` でビルド時計算。レスポンシブ対応 (3カラム→sm以上)。ビルド成功 (108ページ)
- [2026-10-04] カテゴリーカード: フロントページにタグ別記事数のセクションを追加。`CategoryCards.astro` コンポーネント新規作成。既存 `tagColors.ts` の12色パレットを再利用。記事数順にトップ12タグをスリムなアコーディオン型で表示（デフォルト閉じ、ボタンで展開）。ビルド成功 (108ページ)

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。

