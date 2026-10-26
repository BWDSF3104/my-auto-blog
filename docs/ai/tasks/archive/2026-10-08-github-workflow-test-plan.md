# GitHub ワークフロー E2E テスト計画

## テスト概要

| 項目 | 値 |
|------|-----|
| 作成日 | 2026-10-08 |
| テスト対象 | 楽天API商品カード実装 + workflow YAML修正 |
| 使用ワークフロー | `deploy.yml`（generate + deploy） |
| トリガー方法 | `gh workflow run` 手動トリガー |

## テスト対象コミット

| コミット | 内容 |
|---------|------|
| `c973af4` | feat: 楽天市場APIで実画像付き商品カードを追加（比較表・末尾セクション） |
| `8366c32` | fix: workflow YAMLをUTF-8に変換し日本語コメントを英語化、deploy.ymlインデント修正 |

## 基準値

| 項目 | 値 |
|------|-----|
| 直近成功run | `37718631109`（2026-10-08 schedule, 3m6s） |
| generate job | 2m39s（02:35:42 → 02:38:21 UTC） |
| build-and-deploy job | 22s（02:38:23 → 02:38:45 UTC） |
| 参考: 前日成功run | `37560652150`（2026-10-07 schedule, 12m20s） |

## 前提条件

- [x] `RAKUTEN_APPLICATION_ID` Secret 設定済み（2026-10-08T00:44:45Z）
- [x] `RAKUTEN_ACCESS_KEY` Secret 設定済み（2026-10-08T00:44:46Z）
- [x] `RAKUTEN_AFFILIATE_ID` Secret 設定済み（2026-09-27T13:37:00Z）
- [x] `AMAZON_TRACKING_ID` / `GEMINI_API_KEY` / `HF_TOKEN` 設定済み
- [x] pytest 173件通過（ローカル）
- [x] npm run build 122ページ成功（ローカル）
- [x] deploy.yml YAML parse OK（UTF-8）
- [x] deploy-only.yml YAML parse OK（UTF-8）

## 確認項目

### A. ワークフロー実行（deploy.yml）

| # | 確認項目 | 確認方法 | 成功基準 |
|---|---------|---------|---------|
| A1 | YAMLエラーなしで起動 | `gh run view <ID>` | status=completed, conclusion=success（0s失敗なし） |
| A2 | generate job 完了 | `gh run view <ID> --json jobs` | generate = success |
| A3 | build-and-deploy job 完了 | 同上 | build-and-deploy = success |
| A4 | 実行時間の妥当性 | 基準値と比較 | generate: 3〜10分（API追加で増可） / 全体: 5〜15分 |

### B. 楽天API連携（generate job ログ）

| # | 確認項目 | 確認方法 | 成功基準 |
|---|---------|---------|---------|
| B1 | クレデンシャル設定済み | generate job ログ | `⚠️ 楽天APIクレデンシャル未設定` が**出ない** |
| B2 | API検索実行・ヒット | ログの `🛒 [rakuten]` 行 | `→ {itemName} (¥{price})` が1件以上 |
| B3 | 比較表カード挿入 | ログの `🖼️ 楽天API商品カードを {n} 枚追加（比較表の直後）` | n ≥ 1（キーワードが1件以上ヒットした場合） |
| B4 | 末尾セクションカード挿入 | ログの `🖼️ 楽天API商品カードを末尾セクションに {n} 枚追加` | n ≥ 1（キーワードが1件以上ヒットした場合） |
| B5 | 429リトライ（該当時） | ログの `⏳ 楽天API 429` | リトライ後に成功 or 最終エラーでフォールバック |
| B6 | 呼び出し間隔 | ログのタイムスタンプ | 連続429なし（1.5秒間隔が機能） |
| B7 | フォールバック動作 | `→ 画像付き商品なし` or `❌ 楽天API失敗` | 該当kwのみ検索リンク方式へ（記事生成は継続） |

### C. 記事コンテンツ（生成されたMDファイル）

| # | 確認項目 | 確認方法 | 成功基準 |
|---|---------|---------|---------|
| C1 | 比較表直後に商品カード | MDの比較表 `</table>` 直後に `<div class="product-cards">` | 1〜3枚の `.product-card` |
| C2 | 末尾セクション一番上にカード | `### 📚 テーマ関連` 内、CTA・検索リンクより先に `<div class="product-cards">` | カードがリンクより上 |
| C3 | 商品画像URL | `.pc-img` の `<img src="...">` | Rakuten CDN（`thumbnail.rakuten.co.jp` 等） |
| C4 | アフィリエイトURL | カード内楽天ボタン href | `hb.afl.rakuten.co.jp` ラッパー形式 |
| C5 | 価格表示 | `.pc-price` | `¥{num}` 形式（カンマ区切り） |
| C6 | 既存絵文字カード維持 | MD内の絵文字カード（📦🛍️等） | 従来通り存在 |
| C7 | 既存検索リンク維持 | 末尾セクションの Amazon/楽天検索リンク | 従来通り存在 |
| C8 | PR注記維持 | `※ 当サイトはアフィリエイト広告` | 従来通り存在 |

### D. 構造化データ（git push 後）

| # | 確認項目 | 確認方法 | 成功基準 |
|---|---------|---------|---------|
| D1 | `data/rakuten_cache.json` 生成 | `git show origin/main:data/rakuten_cache.json` | 有効JSON、`fetched_at`+`product`+`hits` |
| D2 | `data/affiliate_links/{ts}.json` 生成 | `git show origin/main:data/affiliate_links/` | 新規ファイル存在 |
| D3 | デプロイ自動トリガー | `gh run list --workflow=deploy-only.yml --limit 1` | pushトリガーで success |

### E. デプロイサイト（GitHub Pages）

| # | 確認項目 | 確認方法 | 成功基準 |
|---|---------|---------|---------|
| E1 | 最新記事が配信 | `https://bwdsf3104.github.io/my-auto-blog/` | 新記事がトップに表示 |
| E2 | 商品画像表示 | ブラウザ確認 | 破線枠でなく実画像 |
| E3 | モバイル表示 | 390px幅確認 | カードが縦積みに切り替わる |
| E4 | リンク有効 | Amazon/楽天ボタンクリック | 正しいページに遷移 |

## 注意事項

- **レート制限**: 楽天APIは連続呼び出しで429。呼び出し間隔1.5秒+リトライ実装済み。記事1本あたりAPI 1〜3回
- **APIクォータ**: 楽天API上限10万/日。本テストは1〜3回のみ（大幅余裕）
- **HF API**: 画像生成に使用。前回runでは正常動作
- **初回実行**: `data/rakuten_cache.json` が未生成のため全kwがAPI検索（キャッシュヒットなし）
- **キーワード特性**: kemono_story の tags 由来kw（例: 「ケモノ」「ライバル」）は商品性が低く、0件/画像なしでフォールバックする可能性あり。これは正常動作（B7）

## 関連ファイル

- `scripts/generate_article.py`: `_rakuten_search`(L1143) / `_generate_rakuten_card`(L1241) / `process_inline_products`(L956) / `inject_affiliate_links`(L1352)
- `src/styles/global.css`: `.pc-img`（80px商品画像）
- `.github/workflows/deploy.yml`: Rakuten env + cache git add
- `data/rakuten_cache.json`: 30日TTLキャッシュ（初回実行で生成）
- `data/affiliate_links/`: リンク生成ログ（初回実行で生成）
