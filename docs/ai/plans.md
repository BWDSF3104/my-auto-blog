# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

(なし)

# Completed Plans

- [2026-10-08] トレンドデータパス不一致バグ修正: `2b4a815`（静的解析の絶対パス化）で `generate_article.py` の `PROJECT_DIR` が `scripts/` を指すようになり、`TOPICS_DIR = scripts/data/topics`（存在しない）と `fetch_topics.py` の出力先 `data/topics` が不一致。2026-10-02以降全記事でトレンド注入がサイレント無効（trend_usageログ `file_not_found`）していた。`PROJECT_DIR` をリポジトリ直下に戻し、`fetch_topics.py` 起動パスを `scripts/` 補正。回帰テスト3件追加。pytest 164通過 (1.99s)
- [2026-10-07] 生成パイプライン6項目修正 (#1, #3, #5, #6, #7, #8): 英語用語漏れ修正 (CHAR_TYPE_WEIGHTS日本語化)、2passリファイン強化 (refine_story.txt全体書き換え)、e621収集開始時期ランダム化 (2010-01-01〜現在-14dランダム14日ウィンドウ)、アフィリエイト英語キーワード除去 (tags日本語化+prompt_typeフィルタ+_KEYWORD_ENHANCEMENT cleanup)、製品推薦の具体化 (A1/A2ルール強化+_improve_keyword suffix削除)、trend_usageログ欠落修正 (早期リターンにログ追加+.gitkeep)。pytest 161通過、e621 API確認 (200 OK)
- [2026-10-06] 画像生成上限増加: 記事あたりの画像上限を3枚→8枚（ヘッダー1 + 本文内最大7）に増加。ストーリー系は各章ごとに画像を配置する指示に変更。HF ZeroGPUの実稼働時間消費（初回9秒、ウォーム2秒）をapi-rate-limits.mdに反映。pytest 155通過、ビルド成功 (114ページ)
- [2026-10-06] 画像プロンプト順序最適化: BASE_QUALITY_PROMPTを8→6タグ短縮、Illustrious系推奨順序に再配置（被写体数→キャラクター→シチュエーション→artist→品質→スタイル）。pytest 155通過、ビルド成功 (114ページ)。commit: `947009c`, `fbbb0ab`
- [2026-10-06] e621 artistタグ集計機能: CHARACTER_FEATURE_CATEGORIESにartist追加、unknown_artist除外、generate_article.pyに人気artist注入、art_style指示にartist名候補追加。pytest 155通過、ビルド成功 (110ページ)。commit: `2e960f3`


完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。

