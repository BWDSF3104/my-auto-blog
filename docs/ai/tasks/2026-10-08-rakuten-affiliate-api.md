# 楽天市場API商品リンク連携 (2026-10-08)

**状態: 設計確定済み・実装未着手 (2026-10-08)**

## 概要
アフィリエイト商品リンクを「GEMINIが生成した検索ページURL（`search.rakuten.co.jp/search/mall/...`）」から、楽天市場APIで取得した**具体的な商品詳細URL（アフィリエイト版）** に置き換える。比較表と末尾おすすめリストは**商品画像付きカード**で表示する。

API動作検証・設計・デザイン確認は完了。次は `generate_article.py` 実装。

## ユーザー確認済み決定事項

### URL・商品選定
1. **商品URLはアフィリエイト版**（`hb.afl.rakuten.co.jp` ラッパー型、`pc=` パラメータに通常URL埋め込み）
2. **商品選定基準: `sort=-reviewCount`**（レビュー数降順）
3. APIは**キーワード1回につき1呼び出し**、`hits=3` で上位3件を取得し、画像付きの先頭商品を採用（1件目が画像なしなら2・3件目から選択）
4. 記事1本あたり API 1〜3回（30日キャッシュで月60〜90回程度。楽天API上限10万/日の大幅余裕）

### カード表示
5. **比較表（`process_inline_products`）: 1商品カード**
6. **末尾リスト（`inject_affiliate_links`）: キーワード1件につき1商品カードをセクション一番上に追加、既存リンク（CTAボックス・検索リンク4本・PR注記）はそのまま維持**
7. **カード件数: 合計1〜3枚**（128px画像・2列グリッド想定）
8. カード構成: 商品画像 + 商品名（`itemName`）+ キーワード（`pc-category`）+ 価格（`itemPrice`）+ Amazonボタン（検索）/楽天市場ボタン（商品アフィリエイトURL）
9. **デザイン確認済み (2026-10-08)**: モックアップ（デスクトップ1280px・スマホ390px）のスクリーンショットをモバイルアプリへ送信し承認

### キーワードフィルタ設計
10. **A系（本文内・比較表）**: `_is_affiliate_bad_keyword`(L1028) のガードのみ前置き、キーワードは**そのまま** `_rakuten_search()` に渡す（除外時は既存検索リンクへフォールバック）
    - `_is_github_repo_name`(L1075) は**適用しない**（単一英単語全滅のため iPhone/Switch/Kindle 等の正当な商品名を誤殺する）
    - `_improve_keyword`(L1042) も**適用しない**（"iPhone"→"iPhone 書籍" 等の改造が商品検索を壊す）
11. **B系（末尾）**: 従来通り全フィルタ（bad_keyword + repo_name）＋ `_improve_keyword` の改善済みキーワードをそのまま渡す

### 共通
12. **キャッシュ: 30日**（`data/rakuten_cache.json` 想定、git管理）
13. **フォールバック: API失敗時・0件時、既存の検索リンク方式を維持**
14. Amazonは従来どおり検索リンク（PA-API不使用）

## 発見済み追加範囲 (2026-10-08 最新記事キーワード調査)

### 問題2: B系オフテーマキーワード（tags由来）
kemono_story 記事の末尾セクション（B系）は frontmatter `tags`（物語タグ）からキーワードを生成する。物語タグには購買意図がなく、楽天検索で**無関係な商品**がカード表示される。

実API検証（2026-10-08, `sort=-reviewCount`, `hits=3`）:
- `ケモノ` → 上位1位が**ペンケース ¥3,000**（ケモノ柄小物）
- `ライバル` → 上位1位が**パールピアス ¥2,750**（"トライ**バル**"部分一致によるヒット）
- `BNA ビー・エヌ・エー Complete Animation Art Book` → **0ヒット**（フォールバックで事なし）

対応方針（実装時に決定、候補）:
- (a) 商品意図のないtags由来kwは楽天API検索を**除外**し、既存検索リンク方式のまま（B系のAPI対象はトレンド補完kw＋A系と重複するkwのみ）
- (b) kwに商品性ヒューリスティック（商品名パターンの部分一致・品目リスト）を課し、不合格は検索リンクへフォールバック
- (c) tagsを商品意図語に置換する改造（例: 「ケモノ」→「ケモノパーカー」）— 推測が混じるため非推奨

### リンク生成追跡ログ（構造化JSON）追加
現状の追跡は print（count / anchor→kw）と `data/trend_usage/{ts}.json`（トレンド使用のみ）で、改修後は **API呼び出し結果（ヒット数・選定商品・フォールバック理由）が追跡不能**になる。

提案: 実行ごとに `data/affiliate_links/{ts}.json` を記録（git管理、trend_usageと同じ方式）。1kwあたり:
```
{
  "keyword_raw": "ケモノ",
  "keyword_used": "ケモノパーカー",
  "source": "B_tag | B_trend | A_inline | A_table",
  "filters": {"bad_keyword": false, "repo_name": false, "improved": true},
  "api": {"status": "ok | error | zero | cache | skipped", "hits": 3, "error": null},
  "selected": {"itemName": "...", "itemPrice": 3000, "affiliateUrl": "...", "reviewCount": 1234},
  "fallback_reason": null | "api_error" | "zero_results" | "no_image" | "not_affiliatable",
  "final_url": "..."
}
```
集計サマリ（API呼び出し数/キャッシュヒット数/フォールバック数）も同ファイルに含める。

## 楽天API仕様（動作検証済み・公式ドキュメント確認済み）

### エンドポイント・認証
- エンドポイント: `https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701`（現行version 2026-07-01。旧 `20220601` は `400 wrong_parameter`）
- 認証: **Webアプリケーション型**（IP登録不要）。クエリに `applicationId` + `accessKey` + `affiliateId` + `keyword` + `hits` + `sort` + `format=json` + `formatVersion=2`
- ヘッダー: `Origin: https://bwdsf3104.github.io` + `Referer: https://bwdsf3104.github.io/my-auto-blog/`
- クレデンシャル: `.env` と GitHub Secrets に `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` / `RAKUTEN_AFFILIATE_ID` の3件を設定済み（値はファイルに記録しない）

### レスポンス
- トップレベル `Items`（大文字）。`formatVersion=2` でフラット: `itemName` / `itemPrice` / `itemUrl` / `affiliateUrl` / `mediumImageUrls`（128px・最大3枚）/ `smallImageUrls`（64px）/ `reviewCount` / `reviewAverage`
- `formatVersion=1` だと `Items[0].Item` でラップされる（2を使用）
- `affiliateId` 指定時: `itemUrl` = `affiliateUrl` = アフィリエイトURL

### レート制限
- 連続呼び出しで **429**「Rate limit is exceeded. Try again in 1 seconds.」
- 実装時は**呼び出し間隔1.5〜2秒＋429リトライ（2秒sleep）＋timeout 15〜30秒**必須

### 検証時の注意（教訓）
- PowerShell `Get-Content`/`Set-Content` パイプラインがUTF-8日本語を文字化けさせる（AGENTS.md禁止事項）。一時的な「0件」問題はAPI不具合ではなくこの文字化けが原因。ファイル編集は必ず `write`/`edit` ツール使用

## 実装計画（未着手）
1. `generate_article.py` に `_rakuten_search(keyword)` 追加（429リトライ・30日キャッシュ `data/rakuten_cache.json`）
2. `process_inline_affiliates`(L907) / `process_inline_products`(L956) / `inject_affiliate_links`(L1138) を楽天商品URL・商品カードHTMLに改造（決定事項10-13準拠）
3. `src/styles/global.css` に `.pc-img`（商品画像80px表示）スタイル追加（既存 `.product-card` 体系に統合）
4. テスト: `TestRakutenSearch` 新規追加（成功/失敗/0件/キャッシュ/429リトライ）＋既存アフィリエイトテストに `unittest.mock` でAPIモック（実API呼び出し禁止）
5. `.github/workflows/deploy.yml` の `env:` に `RAKUTEN_ACCESS_KEY` / `RAKUTEN_APPLICATION_ID` 追加＋`data/rakuten_cache.json` の `git add` 追加
6. 検証: `pytest scripts/tests/ -v` ＋ `npm run build` ＋ 出力HTML解析（カード構造・クラス名・リンクURL）

## 関連ファイル
- `scripts/generate_article.py`: 3関数（L907/L956/L1138）、パターン（L205/L211）、フィルタ（L1028/L1075/L1042）、呼び出し箇所（L2597-2606）
- `src/styles/global.css`: 既存 `.product-card` 体系（L95-212）・ブランドカラー（L5-70）
- `scripts/tests/test_generate_article.py`: 既存アフィリエイトテスト
- `.github/workflows/deploy.yml`: 記事生成ワークフロー
- 検証用一時ファイル（Temp\kilo\）: `rakuten_test*.py` / `rakuten_fetch_sample.py` / `rakuten_sample.json` / `card_test.html`

## Verification
- [x] 楽天API動作検証: 認証通過・検索ヒット（ノートPC=約100万件）・アフィリエイトURL・画像URL取得確認 (2026-10-08)
- [x] デザインモックアップ作成・スクリーンショット（desktop/mobile）送信・承認 (2026-10-08)
- [ ] pytest / npm run build: 実装後
