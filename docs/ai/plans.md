# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

(なし)

# Completed Plans

- [2026-10-09] Clef-flash ジャンルスコアリング（backlog #4）: Cloudflare Workers AI の判断特化モデル `@cf/cloudflare/clef-flash` で、文字列の複数ジャンル（sf/fantasy/cyberpunk/action、設定変更可能・最大64問）への関連度を 0-100 整数スコアで取得する。独立 CLI `scripts/genre_score.py`（env `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN`、5xx のみ限定的に再試行、4xx・無料枠超過は再試行せず、SHA256キャッシュ `data/genre_scores/cache.json`、`--no-cache` フラグ）+ 全モック単体テスト61件 + `workflow_dispatch` のみ `.github/workflows/genre-score.yml`。`generate_article.py` 組み込みはスコープ外。2段構成（LLM→Clef-flash）は backlog P3 #1 に追記。実 API スモーク: "攻殻機動隊" → sf:84, fantasy:3, cyberpunk:86, action:47（0.68s）。pytest 261通過。詳細: `docs/ai/tasks/2026-10-09-clef-flash-genre-score.md`

- [2026-10-09] リファインプロンプトに画像プロンプト形式チェックを追加: 2-passリファイナーの役割に「画像生成プロンプトの書式が正しいことの確認」を追加。2026-10-09実Gemini検証で書式逸脱（自然言語句等）がリファイナー（画像プロンプトを変更しないよう明示指示）を無修正通過しPython側フォールバック解析で黙って劣化することを確認。refine_story.txt / refine_tech.txt に「画像プロンプト形式チェック」新節を追加し、修正権限は形式のみに厳密限定（シーンの選定・配置・枚数・キーワードの意味・表情の意図・本文は変更不可）。コード変更不要、pytest 200通過。詳細: `docs/ai/tasks/2026-10-09-refiner-image-prompt-check.md`
- [2026-10-09] ストーリー記事の章内複数画像を許可: kemono_storyの画像指示は「各章ごとに少なくとも1つ」でモデル出力も各章1枚固定だったため、展開が激しい・印象的なシーンでは章内で複数枚の挿入を許可する指示を1行追加（合計上限はヘッダー1+本文内最大7枚のまま不変、被り禁止ルールは維持）。コード変更不要。pytest 200通過。詳細: `docs/ai/tasks/2026-10-09-story-multi-images.md`
- [2026-10-09] Windowsコンソールエンコーディング対策の統一: パイプ時のstdio cp932フォールバックによる`UnicodeEncodeError`（絵文字）・文字化けの原因を特定し、既存4パターンのワークアラウンド（無効なenv設定/_safe_print×2/TextIOWrapper差し替え/reconfigure）を`TextIOWrapper.reconfigure()`方式に統一。`fetch_topics.py`・`generate_article.py`・`fix_affiliate_links.py`・`fix_descriptions.py`の4エントリにwin32ガード付きブロックを追加、`workflow-test-procedure.md`に`$env:PYTHONUTF8="1"`（現セッション）の手順を記載。pytest 200通過。詳細: `docs/ai/tasks/2026-10-09-windows-console-encoding.md`
- [2026-10-09] 画像プロンプト表情/ポーズ指定: kemono_storyの画像プロンプトに表情データがなく生成画像の2匹が同じ・無関係な表情になる問題を解消。キャラ別表情（Danbooru実在タグ1-2個、2匹で同じ場合は1回指定）とポーズ（キャラ別ポーズは括弧内、相互作用ポーズはシーンキーワード）を追加。括弧形式は `[c1: tags, c2: tags]`（個別）/ `[c1, c2, tags]`（共有）/ `[c1, c2]`（legacy互換）の3種を `compose_image_prompt` がパースし、各キャラ外見の直後にインターリーブ（既存の合成順序は維持=キャラ/シチュエーション再現度最優先、`app.py`は不変）。テスト5件追加、pytest 200通過。E2E未検証。詳細: `docs/ai/tasks/2026-10-09-image-prompt-expressions.md`
- [2026-10-09] 楽天アフィリエイトカスケード検索: 楽天API商品カードが記事テーマと無関係な商品を返す問題（汎用キーワードで「パンプス」が「シューファンタジー」に、「iPhoneフィルム」が「SF」に、「浴衣」が「百合」にヒット）を解消。キーワード選定をカスケード検索（Gemini商品名→先頭句→ケモノ+ジャンル→ケモノ+関係性→ケモノ→獣人→動物）に変更し、関連性フィルタ（kemono汎用kwは商品名にケモノ/獣人/動物/アニマル等のコアトークン、その他はkw実語トークン包含）を追加。フィルタ通過商品3件で即停止、affiliateUrlで重複排除。先頭句はスペース+「用的/向け/用/的」で分割（単語内で使われるため平仮名1文字は区切りに使用しない）。楽天API公式レート制限（1req/s per application_id）をapi-rate-limits.mdに追加。pytest 195通過。E2E未検証。詳細: `docs/ai/tasks/2026-10-08-affiliate-keyword-revision.md`
- [2026-10-08] トレンドデータパス不一致バグ修正: `2b4a815`（静的解析の絶対パス化）で `generate_article.py` の `PROJECT_DIR` が `scripts/` を指すようになり、`TOPICS_DIR = scripts/data/topics`（存在しない）と `fetch_topics.py` の出力先 `data/topics` が不一致。2026-10-02以降全記事でトレンド注入がサイレント無効（trend_usageログ `file_not_found`）していた。`PROJECT_DIR` をリポジトリ直下に戻し、`fetch_topics.py` 起動パスを `scripts/` 補正。回帰テスト3件追加。pytest 164通過 (1.99s)
- [2026-10-07] 生成パイプライン6項目修正 (#1, #3, #5, #6, #7, #8): 英語用語漏れ修正 (CHAR_TYPE_WEIGHTS日本語化)、2passリファイン強化 (refine_story.txt全体書き換え)、e621収集開始時期ランダム化 (2010-01-01〜現在-14dランダム14日ウィンドウ)、アフィリエイト英語キーワード除去 (tags日本語化+prompt_typeフィルタ+_KEYWORD_ENHANCEMENT cleanup)、製品推薦の具体化 (A1/A2ルール強化+_improve_keyword suffix削除)、trend_usageログ欠落修正 (早期リターンにログ追加+.gitkeep)。pytest 161通過、e621 API確認 (200 OK)
- [2026-10-06] 画像生成上限増加: 記事あたりの画像上限を3枚→8枚（ヘッダー1 + 本文内最大7）に増加。ストーリー系は各章ごとに画像を配置する指示に変更。HF ZeroGPUの実稼働時間消費（初回9秒、ウォーム2秒）をapi-rate-limits.mdに反映。pytest 155通過、ビルド成功 (114ページ)
- [2026-10-06] 画像プロンプト順序最適化: BASE_QUALITY_PROMPTを8→6タグ短縮、Illustrious系推奨順序に再配置（被写体数→キャラクター→シチュエーション→artist→品質→スタイル）。pytest 155通過、ビルド成功 (114ページ)。commit: `947009c`, `fbbb0ab`
- [2026-10-06] e621 artistタグ集計機能: CHARACTER_FEATURE_CATEGORIESにartist追加、unknown_artist除外、generate_article.pyに人気artist注入、art_style指示にartist名候補追加。pytest 155通過、ビルド成功 (110ページ)。commit: `2e960f3`


完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。

