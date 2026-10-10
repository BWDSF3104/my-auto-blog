# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

(なし)

# Completed Plans

- [2026-10-10] トレンドソース品質修正（ANNナビゴミ排除 + Crunchyroll一時無効化 + per-source TTL 誤検知修正）: trend topics 実効化後のライブ検証で、ANN HTML パースがナビ・フッターを記事として収集（Crunchyroll News 15 件が全件非記事 URL・記事本文 0 件）、`_check_per_source_ttl` が他カテゴリ専属 source の陳腐化を誤検知して kemono 実行のたびに自動 fetch トリガーが発火することを発見。`ENTERTAINMENT_ARTICLE_PATTERNS`（source 別 URL whitelist: ANN = `^/(?:news|review|guide|interview|profile|gallery)/\d{4}-\d{2}-\d{2}/`）新設 + `_parse_entertainment_page()` を `urljoin` 絶対 URL 解決・重複除去・上限15件で書き換え、Crunchyroll を `ENTERTAINMENT_HTML_SOURCES` から一時無効化（静的 HTML に記事 0 件・JS 描画・RSS 404）。`_check_per_source_ttl()`: 他カテゴリ専属 source（トピックあり・要求カテゴリ0件）は `expired=False`（トリガーしない）、トピック 0 件 source（完全失敗）は従来どおり `True` 維持（自愈保持）。`latest.json` から Kemono/Crunchyroll ゴミ 25 件を除去（total 124 → 99）。`by_category`/`all` merge 構造ドリフト（pokemon 旧 7 件）は known-issues.md 記録のみで不変更。pytest 348通過（新規9）、ライブ fetch で ANN 14 件・全件正規記事 URL 確認、TTL dry check で kemono 不トリガー確認。詳細: `docs/ai/tasks/2026-10-10-trend-source-quality-fixes.md`

- [2026-10-10] トレンドデータRSS強化 + trend topics 実効化 (backlog P2 #1, #5): `fetch_rss()` が title+URL のみの取得で description を捨てていたため、RSS2.0（content:encoded→description）/Atom（content→summary）から HTML除去・300文字切り詰めで抽出し `latest.json` に保存。GameSpot/IGN は実測で正規 RSS フィードだったため HTML パースから RSS パースへ切り替え（description 付き化）。全エンタメソース失敗時の未定義 `STORY_INSPIRATION_THEMES` NameError を内蔵テーマ8件の定数定義で修正。`score_topics()` は title+description[:200] でスコアリング（精度向上、次回 deploy 時にキャッシュキー変化による一次性の全再スコア）、`_append_trending_topics()` はトレンドブロックに description[:100] スニペット注入。pytest 339通過（+24）、`test_real_apis.py --save` で GameSpot/IGN の description 出力を確認。詳細: `docs/ai/tasks/2026-10-10-trend-rss-enhancement.md`

- [2026-10-10] アフィリエイト商品推薦の書籍偏りの中性化: 直近記事の商品カード約34件中約6割が書籍・漫画・アートブックで、原因はプロンプトテンプレート内の書籍先頭例・書籍単独例・category 列挙の書籍先頭。ユーザー方針で「書籍」は例から削除せず（書籍自体は正規カテゴリ）、「多様化せよ」系の禁止指示も追加せず、例の順序入れ替え（非書籍先頭）と複数例化で中性化。プロンプト3ファイル + `generate_article.py:694` 注入行（語順のみ）。kemono の「実在作品を1つ選定」→「実在商品を1つ選定」で選定対象を中性化。pytest 315通過。詳細: `docs/ai/tasks/2026-10-10-affiliate-product-diversity.md`

- [2026-10-10] 世界設定の2段階拡大（7→12種）: 追加決定の modern（現代・Zootopia系）/ historical（歴史・時代）/ space_opera（Star Fox）に加え、ユーザー指摘（ファンタジー・異世界方面の薄さ、ポケモンの不思議のダンジョン的世界の親和性）で isekai（異世界）/ dungeon_crawl（ダンジョンクライム）を新設。追加基準を「ニッチでないか」から「ケモノのアンカワーク存在＋明確に異なる物語」へ変更（メカ/ポストアポ/スポーツは独立世界定義不足のため後日）。スコアリングgenreに historical 追加（7種）し直前の6種変更と同バッチ化（一次性の全再スコアリングは次回 deploy 1回のみ）。重み: fantasy 21 / isekai 10 / modern 10 / slice_of_life 10 / sf 8 / space_opera 7 / adventure 7 / cyberpunk 7 / dungeon_crawl 6 / mystery 5 / historical 5 / fantasy+sf 4。pytest 315通過、実APIスモーク（"戦国武将"→historical:80、"スターフォックス"→action:69/sf:40）。詳細: `docs/ai/tasks/2026-10-10-world-setting-expansion.md`

- [2026-10-10] ストーリー系ジャンル拡大: 世界設定4種（fantasy/sf/slice_of_life/fantasy+sf）のみの現状に対し、事前スコアリングの `cyberpunk` が未使用のままコストを消費し、`slice_of_life` → `[action]` の意味逆転マッピングが存在。世界設定を7種（+cyberpunk/adventure/mystery）、スコアリングgenreを6種（+slice_of_life/mystery）へ**一括変更**（キャッシュキー変更による全件再スコアリングという一次性コストを1回に集約）。comedy/romance等の未使用genreは追加しない（cyberpunk型の「スコアリング済但未使用」を再現しない）。重み再配分（合計100: fantasy 30 / slice_of_life 22 / sf 15 / cyberpunk 12 / adventure 8 / fantasy+sf 8 / mystery 5）。pytest 308通過、実APIスモークで新genreの動作確認（"攻殻機動隊"→sf:81/cyberpunk:81、"日常 四葉の妹"→slice_of_life:85）。詳細: `docs/ai/tasks/2026-10-10-genre-expansion.md`

完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。
