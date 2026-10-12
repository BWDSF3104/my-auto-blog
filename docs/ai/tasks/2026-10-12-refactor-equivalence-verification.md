# リファクタリング等価性検証（テスト計画 + ログ選定）

**Status**: **完了（L0/L1/L3 PASS）**（2026-10-12 完了。L2 = 2026-10-13 本番 CI 確認のみ残）
**日付**: 2026-10-12
**ユーザー指示**: リファクタリング前と同じ機能を達成していることを確認するためのテスト計画の作成、および必要なログ等の選定

## 目的・背景

`generate_article.py`（3561→484 行）+ `fetch_topics.py` のリファクタリング（Phase 0-7、ベースライン `69bb5e8` → HEAD `9ac496e`）で、**行動の等価性**を「既存ユニットテスト緑」よりも強く証明する。既存 365 テストは各フェーズで緑だが、これは「テストがカバーする範囲」での回帰保証であり、パイプライン全体の決定論的出力がベースラインと一致することの直接検証は未実施。

## 等価性の定義（比較対象）

同一入力を与えた際の**最終アウトプット群**がバイト一致すること:

1. **最終記事 Markdown**（`src/content/posts/{ts}-auto-post.md`）— frontmatter + 本文 + 生成情報セクション（最重要）
2. **Gemini pass1 プロンプト**（`data/prompt_logs/{ts}.txt`、パイプラインが自動記録）
3. **Gemini pass2（精製）プロンプト**（refine_content 入力、モックで捕捉）
4. **画像プロンプト**（`compose_image_prompt` 出力、`generate_and_save_image` モックで捕捉）
5. **出力ログ 3 種**: `data/trend_usage_logs/`（トレンド利用ログ）/ `data/drafts/`（draft メタデータ）/ `data/affiliate_logs/`（アフィリエイトリンクログ）
6. **標準出力ログ**（進行・警告メッセージ列）
7. **`data/slug-redirects.json`**（変更なしを期待）

## 検証レイヤー

| レイヤー | 内容 | 性質 |
|---|---|---|
| **L0** | 既存ユニットスイート `pytest scripts/tests/ -v`（365 件） | 回帰ガード（各フェーズで実施済み・緑） |
| **L1** | **決定論的リプレイ A/B**（ベースライン `69bb5e8` vs HEAD `9ac496e`）— 本計画の中核 | 出力バイト一致 |
| **L2** | 本番 CI デプロイ（2026-10-13 毎日実行）の構造チェック（カナリア） | 実 API 使用、構造マーカー照合 |
| **L3** | 任意: 実 Gemini 1 回実行の構造健全性確認（A/B 不可・クォータ要） | ユーザー承認後 |

## 確定設計（調査で確定したパラメータ）

### 固定時刻・seed
- **FIXED_EPOCH = `1791766800`** = 2026-10-12T01:00:00Z = **JST 2026-10-12T10:00:00**。派生: `file_timestamp="2026-10-12-100000"`、`pub_date_str="2026-10-12 10:00:00"`、最終記事 `2026-10-12-100000-auto-post.md`、画像 `2026-10-12-100000-header.avif`
- **seed = `20261012`**（`generate_post()` 直前に設定）
- 乱数消費順序（両ツリー同一＝検証対象）: ① `_randomize_kemono_params`（kemono のみ）② `random.sample(candidates[:6],2)`（default は len==2 で発火**なし** / ai_deep・kemono は発火）③ `_select_two_posts`（e621 2 投稿）④ `article_seed`

### 楽天キャッシュ（読み取り専用共有入力）
- `_rakuten_search` 挙動（確定）: **cache hit → product 返却（書き込みなし）/ 無クレデンシャル miss → None（書き込みなし）/ 有クレデンシャル miss → 書込**。L1 は無クレデンシャルのため **キャッシュファイルは絶対に書き換わらない**。
- ∴ **両ツリーに同一ファイルコピーすれば同一出力が保証** → キャッシュの完全性は**等価性には不要**（カバレッジ＝コードパス運動のためだけ）。
- 事前投入（カバレッジ）: dummy 商品で固定下書きの抽出語・gemini 商品名 + 先頭句・kemono カスケード（`ケモノ`/`ケモノ {12 world_tags}`/`ケモノ {4 rels}`/anchors）・`_improve_keyword` 後 trend キーワード・fallback 語。
- dummy 商品: `itemName=f"{kw} テスト商品ケモノ"`（`_rakuten_is_relevant` 全分岐通過）、`itemPrice=1980`、`affiliateUrl`/`imageUrl` は kw 固有（`seen_urls` 重複排除回避）、`reviewCount=100`。
- cache TTL は `datetime.now(utc)` 基準（fake が有効）→ 各エントリ `fetched_at="2026-10-11T00:00:00+00:00"`（30 日以内・新鮮）。

### トピックス（latest.json）
- 実データ: tech=0 / kemono=36 / pokemon=40。**tech=0 のままだと "default"（categories=[\"tech\"]）で `_auto_fetch_topics`（subprocess + ネットワーク）が発火**するため tech 2 件 + `TechCrunch RSS` source を追加。
- `fetched_at`（全局 + kemono sources + 新 tech source）を **now−1h = 2026-10-12T09:00:00+09:00** に改写（全 source TTL 新鮮）。pokemon sources は 10 日前だが **out-of-scope**（category 交点なし → 期限切れ扱いにならない）ため発火しない。
- 結果: default → tech 2 件（sample 発火なし）/ kemono_story → kemono 36 件 + genre フィルタ + sample / ai_deep → tech2+kemono36=38 件 + sample。

### L3（実 Gemini 1 回）
- `eq/realrun`（git archive 9ac496e）、**実 .env の `GEMINI_API_KEY`**、`article.gemini.MODELS_TO_TRY[:1]`（=`"gemini-3.8-flash"` 固定）。
- **pass1 = 実 Gemini**（`client` 実体）、**pass2 = fake**（`generate_article.refine_content` を `(fixed_refined, "eq-fake-refine")` にパッチ）→ コスト 1 分・決定論的。
- バリアント `default` ×1。**構造健全性のみ**（A/B 不可）: frontmatter YAML 妥当性 / セクション順序 / `public/images/{ts}-header.avif` 存在 / 生成情報節。
- `max_retries=3` のリスク（失敗時 RuntimeError → 記事非生成）を報告に明記。

## L1: 決定論的リプレイ A/B（詳細仕様）

### 原理

外部 API（Gemini / 画像生成 / 楽天）をモックし、乱数と時刻を固定して `generate_post()` を 2 つのコードツリーで実行し、出力群を diff。**時刻を固定すればファイル名（ts）も一致するため、等価ならバイト一致が期待できる**（diff ゼロを合格基準とする）。

### 固定化・モック一覧

| 対象 | 手法 | 備考 |
|---|---|---|
| 乱数 | `random.seed(20261012)` を `generate_post()` 直前に設定 | kemono 抽選・article_seed・e621 2 投稿選出を固定。**呼び出し順序の差分はまさに本検証が検出する真の回帰** |
| 時刻 | **クラス級パッチ必須**: `datetime.datetime.now = classmethod(lambda cls, tz=None: datetime.fromtimestamp(1791766800, tz))`。加えて `time.time` → `1791766800.0+0.05n`（単調増加）、`time.sleep` → no-op | `meta/trends/affiliate/geninfo` が `from datetime import datetime` を使うため `generate_article.datetime` 属性パッチでは**不十分**。ts・pubDate・TTL 判定（全局 + per-source）・楽天 cache TTL（`datetime.now(utc)`）・生成情報の「データ時点」を固定 |
| PROMPT_TYPE | 環境変数で **3 バリアント**実行: `default` / `kemono_story` / `ai_deep` | 分岐（ng 指示・カテゴリ・テンプレート・kemono パラメータ）を網羅 |
| Gemini | **Fake client**（`client.models.generate_content(model, contents)` が固定レスポンスを返す）を `client` 属性にパッチ | pass1=固定下書き / pass2=固定精製文（別テキストで pass2 反映を検証）。リトライ・コードブロック除去を含む移設済みコードも A/B 対象になる |
| 画像生成 | `generate_and_save_image(prompt, filename, seed)` をモックし**画像プロンプトを捕捉** + ダミー AVIF 書き出し | `compose_image_prompt` 本体は実行される |
| 楽天 API | `data/rakuten_cache.json` を**固定下書きの全キーワードで事前投入**（TTL 新鮮）→ キャッシュヒット経路のみ | ネットワーク呼び出しゼロ |
| トピックス | `data/topics/latest.json` を TTL 新鮮な固定スナップショットに → `_auto_fetch_topics`（subprocess）が発火しない | fetch_topics.py 自体は A/B 対象外（Phase 1 の関数抽出は L0 で検証済み） |
| e621 / ジャンル | `data/character_features.json` / `data/genre_scores/topics.json` を固定スナップショットでローカル読取 | ネットワークなし |

### ツリーごとのモックパッチ経路

| モック | ベースライン `69bb5e8`（単一ファイル） | 現行（パッケージ） |
|---|---|---|
| Gemini client | `generate_article.client` | `article.gemini.client` |
| 画像生成 | `generate_article.generate_and_save_image` | **両方**: `generate_article.generate_and_save_image`（build_header_image）と `article.image.generate_and_save_image`（process_inline_images） |
| datetime | クラス級 `datetime.datetime.now` | クラス級 `datetime.datetime.now`（同一） |

### サンドボックス構成（**git archive 展開 = サンドボックス自体**）

`git worktree` の代わりに **`git archive`** でコミットを展開し、**展開ディレクトリ自体がサンドボックス**（cwd = 展開先）。`PROJECT_DIR`（絶対・config.py 基準）も相対パス（`data/...`・`src/content/posts`）も両方展開先に解決される:

```
C:\Users\fujim\AppData\Local\Temp\kilo\eq\
├── baseline\   # git archive 69bb5e8 展開（= サンドボックス）
├── current\    # git archive 9ac496e 展開（= サンドボックス）
├── realrun\    # L3 用（git archive 9ac496e 展開）
└── out\
    ├── selftest_{1,2}_{variant}\   # 自己整合（現行 ×2）
    ├── baseline_{variant}\  と  current_{variant}\   # A/B 成果物
    └── realrun_{variant}\    # L3
```

**各サンドボックスへのデプロイ（両ツリー同一）**:
- `data/` ← golden: `topics/latest.json`（TTL 新鮮 + tech 2 件追加）・`genre_scores/topics.json`（実コピー）・`character_features.json`（実コピー）・`rakuten_cache.json`（事前投入）・`slug-redirects.json`（`{}`）・空ログディレクトリ `drafts/` `trend_usage_logs/` `affiliate_logs/` `prompt_logs/`
- `src/content/posts/` ← 現行作業ツリーの 53 記事コピー（recent titles / 内部リンクの対象）
- `scripts/prompts/` ← 現行作業ツリーの 5 テンプレートコピー
- **`.env` は置かない**（全 env をサブプロセス env で制御・hermetic。`git archive` は未追跡 `.env` を含まない）
- 冪等: 実行前に展開ディレクトリを削除して再展開（ハーネスが Python で実施）

### サブプロセス env（L1・両ツリー同一）

```
PROMPT_TYPE=<default|kemono_story|ai_deep>
GEMINI_API_KEY=dummy-eq-test
HF_TOKEN=dummy-eq-test
RAKUTEN_APPLICATION_ID=          # 空 → 楽天 API は cache miss 時スキップ（ネットワークゼロ）
RAKUTEN_ACCESS_KEY=
RAKUTEN_AFFILIATE_ID=eq-test-rakuten-id      # リンク生成用（値は両ツリー同一で十分）
AMAZON_TRACKING_ID=eq-test-amazon-tag-22     # リンク生成用
PYTHONIOENCODING=utf-8
MAX_INLINE_IMAGES=7
MIN_SCORE_THRESHOLD=0
```

### 自己整合性チェック（A/B 前に必須）

現行ツリーを**同一設定で 2 回実行 → 出力がバイト一致**を確認してから A/B を実施（検証装置自体の決定論性を保証）。

### 合格基準

- 3 バリアント ×（自己整合 2 回 + A/B）で **diff が全て空**
- 差分が出た場合: 各差分を「リファクタ由来か / 入力の非決定論由来か」に分類。リファクタ由来は修正対象、非決定論由来は固定化の漏れとしてハーネスを修正して再実行

## 入力フィクスチャ（ゴールデンスナップショット）

`data/equivalence_golden/` にコミット（将来のリファクタで A/B 不要に再実行可能にするため）:

| ファイル | 内容 |
|---|---|
| `inputs/data/` | `topics/latest.json`（TTL 新鮮）・`genre_scores/topics.json`・`character_features.json`・`rakuten_cache.json`（全キーワード事前投入）・`slug-redirects.json`・ログディレクトリ初期状態 |
| `inputs/posts/` | `src/content/posts/` スナップショット（recent titles / 内部リンクの対象） |
| `inputs/prompts/` | `scripts/prompts/` 5 テンプレート |
| `fixtures/fixed_draft.txt` / `fixed_refined.txt` | Gemini 固定レスポンス（下書き / 精製文）。下書きは **HTML comment プレースホルダー** `<!-- IMAGE_PROMPT: "..." -->` ×2 / `<!-- AFFILIATE: "kw" | "anchor" -->` / `<!-- AFF_PRODUCT: "kw" -->` / `## よくある質問`（Q:/A:）/ キャラ欄 / `product_recommendations:` を含み事後処理全経路を触る。**「関連のおすすめアイテム」/「スポンサーリンク」の文字列は含めない**（`inject_affiliate_links` guard 早期 return 回避） |
| `fixtures/fake_now.json` | 固定時刻（JST） |
| `fixtures/seed.txt` | `20261012` |
| `out/<variant>/` | 初回実行時の現行コード出力（ゴールデンアウトプット） |

## ログ・成果物の選定（キャプチャ対象）

### 各実行ごとにキャプチャ（3 バリアント × 2 ツリー = 6 実行 + 自己整合 2 実行）

| # | 成果物 | 来源 | 用途 |
|---|---|---|---|
| 1 | `article.md` | `src/content/posts/{ts}-auto-post.md` | 主要アウトプット・diff 対象 |
| 2 | `prompt_pass1.txt` | `data/prompt_logs/{ts}.txt`（パイプライン自動記録） | pass1 プロンプト diff |
| 3 | `prompt_pass2.txt` | Fake client が捕捉した 2 回目の `contents` | 精製入力 diff |
| 4 | `image_prompt.txt` | `generate_and_save_image` モックが捕捉した引数 | 画像プロンプト diff |
| 5 | `stdout.log` | サブプロセス標準出力 | 進行・警告メッセージ列の一致確認 |
| 6 | `trend_usage_log.json` | `data/trend_usage_logs/` | トレンド選出結果 diff |
| 7 | `draft_metadata.json` | `data/drafts/` | draft メタ diff |
| 8 | `affiliate_link_log.json` | `data/affiliate_logs/` | アフィリエイトリンク diff |
| 9 | `slug_redirects.json` | `data/slug-redirects.json` | 変更なし確認（diff 空） |

### 横断・補助

| # | 成果物 | 用途 |
|---|---|---|
| 10 | `diff_report.txt` | 成果物ディレクトリの `diff -r` 出力（合格時=空） |
| 11 | `pytest_full.log` | L0 全テスト出力（`-v`・経過時間付き） |
| 12 | `scope_diff.txt` | `git diff --stat 69bb5e8..9ac496e -- scripts/`（変更範囲の証跡） |
| 13 | L2: GitHub Actions デプロイ実行ログ（URL + ログ） | 本番カナリアの証跡 |
| 14 | L2: 本番生成記事 + `search-index.json` の該当エントリ | 構造マーカー照合 |

### 保存先

- ハーネス: `scripts/tests/equivalence_check.py`（コミット。`test_` 接頭辞なしのため pytest 集外・AGENTS.md の外部 API 禁止ルールに適合: 全モック）
- ゴールデン: `data/equivalence_golden/`（コミット）
- 初回検証の証跡: `docs/ai/verification/2026-10-12-refactor-equivalence/`（上記 #5-#12 をコミット）

## ハーネス実装仕様（`scripts/tests/equivalence_check.py`）

```
python scripts/tests/equivalence_check.py --baseline 69bb5e8 --variants default,kemono_story,ai_deep
python scripts/tests/equivalence_check.py --golden data/equivalence_golden   # A/B 不要の再検証モード
```

手順:
1. `git archive` で baseline + current（L3 用 realrun）を `eq/{baseline,current,realrun}` へ展開
2. 各サンドボックスへ入力デプロイ（golden `data/` + 現行 `posts/` + 現行 `prompts/`）+ ツリー別 runner `eq_runner.py` を書込
3. 各サンドボックスで `cwd=サンドボックス` + サブプロセス env（上記）で `python eq_runner.py` を実行（runner が datetime/time/random パッチ + モック適用 + `generate_post()` 呼出）
4. 成果物収集 → `out/`（パス正規化: 絶対パス `data_file` を `<ROOT>` に置換）
5. 自己整合（現行 ×2）→ A/B（baseline × current）をバリアントごとに再帰 diff
6. `diff_report.txt` 書き出し、**diff 空なら exit 0 / 差分ありで exit 1**

## 成功基準（全体）

- L0: `pytest scripts/tests/ -v` → 365 passed
- L1: 3 バリアントすべてで自己整合・A/B の diff が空
- L2: 2026-10-13 の CI 記事が構造マーカー一致（frontmatter キー集合 / セクション順序（生成情報・トレンド・e621・キャラデータ）/ 画像枚数 / アフィリエイト節 / search-index エントリ）
- 証跡（#5-#14）を `docs/ai/verification/2026-10-12-refactor-equivalence/` に保存し、本ファイルと `current-task.md` に結果を記録

## リスク・留意点

| リスク | 対策 |
|---|---|
| 固定下書きが一部の分岐を触らない（偽の等価） | 下書きを事後処理全経路（本文画像 / アフィリエイト / 商品カード / FAQ / キャラ設定）を触る内容に設計。3 バリアントで prompt_type 分岐を網羅 |
| 楽天キャッシュの TTL 判定で API 発火 | キャッシュ投入時のタイムスタンプを固定時刻の直前に設定し、発火したらハーネスが失敗として検知（`requests` のモックがネットワーク禁止アサート付き） |
| `_auto_fetch_topics` の subprocess 発火 | latest.json を TTL 新鮮に固定 + 発火検知アサート |
| `_cleanup_old_logs` がサンドボックスの固定ログを削除 | 両ツリーで同一挙動のため diff に影響しない（削除自体は期待動作） |
| サンドボックス展開の残留 | `eq/` は Temp 配下（作業ツリー外）で無害。ハーネスは実行前に Python で削除・再展開（冪等） |
| 固定時刻と `datetime.now` の参照先 | クラス級 `datetime.datetime.now` パッチ（両ツリー共通）。ハーネスが開始時に固定値を返すことをアサート |
| ゴールデンの肥大化 | 記事 md + プロンプト 3 種 + ログ 3 種 × 3 バリアントで概算数十 KB 程度と推定 |

## 実施順序・見積

1. 固定下書き・固定精製文・楽天キャッシュ投入データの設計（固定化の漏れがないか L1 実行で検証）
2. `equivalence_check.py` 実装 + 自己整合チェック緑
3. A/B 実行 + diff 確認（差分があれば分類→修正→再実行）
4. ゴールデンスナップショット + 証跡の保存・コミット（コミット方針に従い検証済み状態で 1 コミット）
5. L2: 2026-10-13 の CI デプロイ後、構造マーカー照合 + 結果記録

## 実施結果（2026-10-12 完了）

| レイヤー | 結果 |
|---|---|
| L0 | `pytest scripts/tests/ -v` → **365 passed** (7.23s) |
| L1 | 全 3 バリアント（default / kemono_story / ai_deep）で **自己整合（2 回実行バイト一致）+ A/B 全成果物一致** → **PASS** |
| L3 | 実 Gemini 1 回（`gemini-3.8-flash`、初試行成功）で記事生成 → 構造健全性チェック **PASS**（`--l3-recheck` で API なし再検証可能） |

証跡: `docs/ai/verification/2026-10-12-refactor-equivalence/`（README + L1/L3 レポート + pytest 全ログ + scope diff + 13 run ディレクトリの全成果物）

### 設計と実装の差分（実施中に確定・修正したもの）

- `datetime` パッチ: クラス属性パッチは不可（C 拡張型で不変）→ `_FakeDateTime(datetime)` サブクラスを各モジュールの `sys.modules` 参照へ差し替え（効果は同一）。
- 差分判定: 「diff ゼロ」を合格基準とした設計に対し、`diff_dirs` を **fatal（内容差分・ファイル欠落・バイナリ差分）/ order_only（行集合同一・順序のみ）** に分離。selftest は order_only も失敗扱い、A/B は order_only を装飾差として許容。
- パス正規化: JSON ファイルは盲fold（`replace("\\","/")`）が JSON エスケープ（`\n`）を壊すため、parse→文字列 deep-normalize→再シリアライズへ変更。

### L1 の唯一の差異（装飾・許容・成果物に無影響）

`stdout.log` の `🎲 記事のbase seed: N` 出力位置のみ baseline（キャラクタ検出後）と現行（検出前）で異なる。seed 値・RNG 消費順序は同一で、記事・ログ・メタデータ等の全成果物は一致。

### L3 実施時の事象（記録）

- 初回実行は Gemini API `503 UNAVAILABLE`（モデル高需要の一時的障害）で失敗。リトライ（3 試行）が設計通り動作し RuntimeError 伝播。数分後の再実行で成功（API クォータ消費 = 成功 1 回分のみ）。
- ハーネスの構造チェックで「生成情報」セクションを markdown 見出し `## 生成情報` として探していたが、実際は `geninfo.py` が HTML（`<summary>🤖 生成情報</summary>`）で組立する → チェックを両形式許容に修正（`equivalence_check.py`）。
