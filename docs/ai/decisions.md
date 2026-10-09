# Design Decisions

古い決定は `decisions-archive.md` に移動する。直近15件のみ保持。

## 2026-10-09: リファインプロンプトに画像プロンプト形式チェックを追加

**Decision**: `refine_story.txt`（【11. 画像プロンプト形式チェック】新設）と `refine_tech.txt`（【10. 画像プロンプト形式チェック】新設）に形式チェック節を追加し、2-passリファイナーの役割に「画像生成プロンプトの書式が正しいことの確認」を追加。修正権限は**形式のみ**に厳密限定: 括弧の欠落・無効なcharacter_N参照（有効IDへ）、自然言語句→簡潔タグ、masterpiece等品質タグの削除、日本語・全角→英語・半角、表情欠落時の1-2タグ（Danbooru実在タグ・場面感情に一致）追加。変更不可: シーンの選定・配置・枚数、シーンキーワードの意味、表情の意図、記事本文。「タグ内英語は変更しない」ルール（旧82行目）は「内容として書き換えない（形式誤りは新節に従って修正する）」へ書き換え、構成維持節の例外注記を併記。

**Reason**: 「画像プロンプトに場面ごとの表情/ポーズ指定追加」(2026-10-09) の実Gemini検証で書式逸脱（自然言語句1件+2件）を観測し、現状のリファイナー（画像プロンプトを変更しないよう明示指示）では無修正通過、Python側フォールバック解析で黙って劣化することを確認。リファイナーは抽出・画像生成より前に走るため修正が `compose_image_prompt` へ伝播し、追加API呼び出しなし。観測された逸脱は意味的（自然言語句・表情と場面の一貫性）で正規表現では完全捕捉不能のためプロンプトによるチェックが適切。

**Rejected Alternatives**:
- B: Python構造化検証（`validate_image_prompts()`）のみ: 信頼性・テスト性は高いが意味的品質（自然言語句・Danbooru実在性）を判定不能。今回は未採用（逸脱頻度定量化の警告ログとして後日追加可能）
- C: A+Bハイブリッド: 最も堅牢だが作業量最大。Aの効果評価後に判断
- リファイナーによる画像プロンプト全面書き換え: 「キャラ及びシチュエーション再現度を最優先」原則に反。LLMが正当な形式を不正に書き換えたりシーン内容を書き換えたりするリスク
- 現状維持: 2026-10-09「画像プロンプトのキャラ別表情/ポーズ指定」の Impact 行（`refine_story.txt`: 変更なし）を本決定で取り下げ・取代

**Impact**:
- `scripts/prompts/refine_story.txt`: 【11. 画像プロンプト形式チェック】新設、82行目書き換え、【12. 構成と形式】番号振り直し＋例外注記、自己検証前チェックリスト1項目追加
- `scripts/prompts/refine_tech.txt`: 【10. 画像プロンプト形式チェック】新設、【9. 見出し・構成】の「各種タグ」例外注記、【11. 情報追加に関する制限】番号振り直し
- 適用対象: refine_story = kemono_story (novel/story)、refine_tech = default/ai_deep
- pytest 200通過 (3.28s)。リファイナーの実Gemini挙動検証未実施

## 2026-10-09: Windowsコンソールエンコーディング対策の統一（stdio reconfigure）

**Decision**: エントリスクリプト冒頭（import直後・最初のprint前）に `if sys.platform == "win32":` ガード付きで `sys.stdout.reconfigure(encoding="utf-8")` / `sys.stderr.reconfigure(encoding="utf-8")` を配置し、既存のワークアラウンドをこの方式に統一。`fetch_topics.py`（無効な `os.environ["PYTHONIOENCODING"]` 設定を置換）・`generate_article.py`（新設）・`fix_affiliate_links.py`（`io.TextIOWrapper` 差し替え方式から移行、`import io` 削除）・`fix_descriptions.py`（新設）の4エントリに適用。`_safe_print()`（fetch_topics / test_real_apis）はUTF-8下ではフォールバックが発火しない防御コードとして維持。

**Reason**: Kilo CLI が stdout をキャプチャ（パイプ扱い）すると Python はコンソール直結時の `WindowsConsoleIO`（UTF-8対応）を使わず**ロケール cp932 にフォールバック**し、絵文字等非収録文字で `UnicodeEncodeError`・cp932バイト列のUTF-8解读で文字化けする（2026-10-09 実測で確認）。`PYTHONIOENCODING` はインタプリタ起動時のみ参照されるため実行時設定は現在プロセスに無効（`fetch_topics.py` 旧コードの欠陥）。`reconfigure()` は既存オブジェクトをインプレースで書き換えるため、旧方式（TextIOWrapper差し替え）の旧stream参照分裂・二重ラッパー問題を回避でき、環境変数に依存せず別マシンでも確実に効く。`test_real_apis.py:33-36` に既に同じ方式があり、コードベースの先例として採用。

**Rejected Alternatives**:
- `os.environ["PYTHONIOENCODING"]`（実行時設定）: 現在プロセスに無効（起動時のみ参照）。子プロセス専用修正
- `io.TextIOWrapper` 差し替え: 有効だが旧streamを保持するコードがcp932書き続行する分裂状態の恐れ、同一バッファ上の二重ラッパー
- `_safe_print()` のみ: 逐次的な例外処理で出力先が2系統に分裂。根本対策にならない（防御として維持）
- 環境変数 `PYTHONUTF8=1` のみ: 運用ベースとして `workflow-test-procedure.md` に記載済みだが、env未設定環境（別マシン・CI・新セッション）では無効になるためコード側の自己完結と併用
- 共有ヘルパモジュール化: スクリプトは「単体実行前提」の独立設計のため、3行ブロックの重複を許容（`hf-space/app.py` は HF Space=Linux 実行のため対象外）

**Impact**:
- `scripts/fetch_topics.py`, `scripts/generate_article.py`, `scripts/fix_affiliate_links.py`, `scripts/fix_descriptions.py`: reconfigureブロック追加/置換
- `docs/ai/workflow-test-procedure.md`: 「ローカル実行注意」セクション追加（`$env:PYTHONUTF8="1"` 現セッション設定・`python -X utf8` 1回限り代替）
- pytest 200通過、パイプ環境スモークテストで utf-8 化確認

## 2026-10-09: 画像プロンプトのキャラ別表情/ポーズ指定

**Decision**: kemono_story の画像プロンプトに場面ごとの表情/ポーズ指定を追加。形式は `[character_1: blushing, smile, character_2: frown, narrowed eyes] scene`（コロン=キャラ別）/ `[character_1, character_2, smile] scene`（コロンなし末尾エントリ=共有）/ `[character_1, character_2] scene`（legacy後方互換）の3種。`compose_image_prompt` が括弧をパースし、表情/ポーズタグを各キャラクター外見の直後にインターリーブ。全キャラの表情が同一の場合はキャラブロックの後に1回だけ出力（dedupe）。キャラ別ポーズは括弧内、相互作用ポーズ（hugging, facing each other 等）はシーンキーワードで指定。

**Reason**: 既存の画像プロンプトに表情データがなく、生成画像の2匹が同じ・無関係な表情になりストーリー再現度が低下。Illustrious系（Nova-Furry-XL）のベストプラクティス調査で、表情タグは各キャラの描述の直後（隣接性ヒューリスティック）がキャラへの結合に最も有効と判明。

**Rejected Alternatives**:
- 合成順序の変更（quality先頭化等）: ユーザーが「キャラ及びシチュエーションの再現度を最優先」と明示。既存順序（被写体数→キャラ→シチュエーション→artist→quality→style）を維持
- `BREAK` / `(tag:1.2)` 重み付け: パイプラインは素のdiffusers（Compelなし）でパースされない
- テンプレートに表情例の長いリスト: 22行目の「Danbooru互換タグ形式」ルールと冗長（ユーザー修正で削除）。「実在タグ」要求＋具体例2つで十分と判断
- `app.py` 変更: HF Spaceアプリは最終プロンプト文字列をそのまま受け取るため、`compose_image_prompt` 側で合成

**Impact**:
- `scripts/prompts/kemono_story.txt`: ルール2項目（キャラ別表情・シーンキーワードの構成）追加＋例4箇所更新
- `scripts/generate_article.py`: `_parse_image_prompt_targets()` 新設、`compose_image_prompt` をインターリーブ合成に変更
- `scripts/tests/test_generate_article.py`: テスト5件追加（個別/単独/dedupe/共有/legacy）
- `refine_story.txt`: 当時変更なし（82行目の「タグ内英語は変更しない」が新形式も維持するため）→ 同日の「リファインプロンプトに画像プロンプト形式チェックを追加」で形式修正許可へ取代

## 2026-10-04: 重複YAMLキーの自動修復ロジック

## 2026-10-06: 画像生成上限を3枚→8枚に増加

**Decision**: `MAX_INLINE_IMAGES` のデフォルトを 2 → 7 に増加（ヘッダー含めて合計最大8枚）。ストーリー系（kemono_story）は各章ごとに画像を配置する指示に変更。技術系（default, ai_deep）も挿絵上限を 2 → 7 に増加。

**Reason**: HF ZeroGPU の `duration=20` はタイムアウト予約であり、実稼働時間分のみ消費されることを確認。初回9秒、ウォーム2秒/枚で1日約101枚生成可能。以前の3枚/記事ではクォータの大幅な余剰があった。

**Rejected Alternatives**:
- 画像数を維持: クォータの余剰を無駄にする
- Pollinations.ai への完全移行: HF の画質が安定しているためプライマリは維持

**Impact**:
- `scripts/generate_article.py`: `MAX_INLINE_IMAGES` デフォルト 2 → 7
- `scripts/prompts/kemono_story.txt`: 画像選出ルールを「合計最大8枚、各章に1つ以上」に変更
- `scripts/prompts/default.txt`: 挿絵上限 2 → 7
- `scripts/prompts/ai_deep.txt`: 挿絵上限 2 → 7
- `docs/ai/api-rate-limits.md`: HF ZeroGPU の実稼働時間消費を反映

**Decision**: `generate_article.py` の `validate_and_fix_frontmatter()` 内で、PyYAML `safe_load` 検証より前に重複キーチェックを无条件で実行。キャラクターキーの命名規則を `character_N` に強制し、AI が出力したキャラクタータイプ名（例: `少年:`）を自動リネーム。

**Reason**: AI がプロンプト指示の `character_1`/`character_2` を無視し、キャラクタータイプ名をキーとして出力するため、2人以上で重複し Astro/Vite が `duplicated mapping key` でビルド中断。PyYAML の `safe_load` は重複キーでエラーを発生させないので、事前チェックが必須。

**Rejected Alternatives**:
- AI プロンプトの修正のみ: AI が指示を無視する根本問題は解決しない
- `safe_load` のみの検証: 重複キーを検出できない
- ビルド失敗後の手動修正のみ: CI/CD パイプラインが毎度ブロックされる

**Impact**:
- `scripts/generate_article.py`: `_fix_duplicate_yaml_keys()` と `_is_character_like_key()` ヘルパー関数を追加、`validate_and_fix_frontmatter()` に无条件の重複チェックを組み込み
- `scripts/tests/test_generate_article.py`: 重複キー修復のテストケースを追加

## 2026-10-03: npm サプライチェーン攻撃対策の適用

**Decision**: npm の依存パッケージをバージョン固定化し、npm グローバル設定でサプライチェーン攻撃対策を有効化。

**Reason**: 2025-2026年にnpmエコシステムで複数の大規模なサプライチェーン攻撃（Shai-Hulud, ChainDrop, Miasma, IronWorm, GHAPPIER など）が発生。自己複製型のマルウェアが500〜1300以上のパッケージを汚染し、install-time script を経て資格情報を窃取する攻撃が常態化。本项目の直のパッケージ（astro, tailwindcss 等）は汚染リストには含まれていないが、推移的依存の `http-cache-semantics` に high 脆弱性（GHSA-ch52-4w7c-c8xp）が存在。

**Applied Settings**:

- `package.json`: 全パッケージのバージョン指定を `^` から exact version に変更（例: `^7.3.5` → `7.3.5`）
- `npm config set save-exact=true`: 今後 `npm install` する際にexact versionを記録
- `npm config set min-release-age=7`: 公開後7日未満のバージョンはインストールしない（汚染された新バージョンの回避）
- `npm config set ignore-scripts=true`: install-time script（postinstall, preinstall など）を無効化（マルウェア拡散経路の遮断）

**Impact**:
- `package.json`: `astro`, `tailwindcss`, `@tailwindcss/vite`, `@tailwindcss/typography` のバージョンを固定
- `package-lock.json`: 既存のロックファイルと整合性あり
- `allowScripts.esbuild`: `ignore-scripts=true` により無効化されるが、esbuildのネイティブバイナリは別パッケージとしてインストールされるためビルドに影響なし
- ビルド動作は確認済み（`npm run build` 成功）
- 今後 install script が必要なパッケージを追加する場合は `npm install --ignore-scripts=false` で明示的に有効化する必要がある

**Rejected Alternatives**:
- `^` を維持: メジャーバージョン内の自動更新が許可され、汚染された新バージョンがインストールされるリスク
- `~` (minor以下のみ) の使用: patch版本の自動更新が許可され、完全な固定ではない
- npm v12のリリースを待機: npm v12ではinstall scriptがデフォルト無効化されるが、リリース時期が不明確

## 2026-10-02: レート制限テーブルを独立ドキュメントに分離

**Decision**: AGENTS.md のレート制限テーブルを `docs/ai/api-rate-limits.md` に分離。`fetch_topics.py` 更新後に `test_real_apis.py --save` を実行する検証ルールを追加。

**Reason**: AGENTS.md にインラインで配置していたレート制限テーブルがファイル肥大化の原因。分離して保守性を向上し、AGENTS.md を運用ルールに集中させる。検証ルールにより、トレンド収集スクリプト変更後のデータソース可用性をチェック。

**Impact**:
- `AGENTS.md`: インラインレート制限テーブルを `docs/ai/api-rate-limits.md` への参照に置換。`fetch_topics.py` 変更後の `test_real_apis.py --save` 検証ルールを追加。
- `docs/ai/api-rate-limits.md`: 確認済みのレート制限テーブルを含む新ファイル。

## 2026-10-01: Remove Deploy Success Skip Logic

**Decision**: Remove `check_deploy_success()` function and `data/.last-deploy-success.json` deploy timestamp recording. Generation no longer skips based on same-day deploy records.

**Reason**: The skip logic was intended to prevent duplicate generation on the same day, but it blocked legitimate regeneration when needed. Removing it simplifies the pipeline and allows the workflow to generate articles on each run.

**Rejected Alternatives**:
- スキップロジックを維持: 再生成が必要な場合にブロックされる問題が残る

## 2026-10-01: Mandatory Impressive Scenes and 3-Image Role Distribution for Kemono Story

**Decision**: Add condition 8 "印象的なシーンの必須配置" to `kemono_story.txt`, requiring at least one impressive scene from four categories: physical intimacy (kiss, hug, head pat, hand-holding), tense close contact (fall collision, narrow space closeness, protective embrace), intense action (duel, chase, magic battle, life-and-death fight), emotional decisive moments (tears, confession, parting, reunion, trust declaration). Redesign image prompt selection rules so the 3 images (1 header `image_prompt` + 2 inline `IMAGE_PROMPT`) each target a distinct moment with no overlap.

**Rationale**: Stories lacked memorable, emotionally impactful scenes. Image prompts for header and inline images targeted "the most impressive scene" identically, causing visual duplication when only 3 images are generated total. Role-based distribution ensures the 3 images cover different emotional beats: header = poster/climax, inline 1 = early-mid intimate/emotional, inline 2 = mid-late action/introspective.

**Rejected Alternatives**:
- 全画像に「最も印象的なシーン」を指定: 3枚で同じ瞬間が描かれ、視覚的に被る
- 画像枚数の増加: 生成コストと読み込み時間が伸びる

**Impact**:
- `scripts/prompts/kemono_story.txt`: 条件8追加、画像選出ルールを3枚の役割分担に書き換え、テンプレート例を更新
- `scripts/prompts/refine_story.txt`: クライマックス精製段階に印象的なシーンの弱化防止チェックを追加

## 2026-10-01: Pollinations.ai Fallback for Image Generation

**Decision**: Add Pollinations.ai as a fallback image generation service when HuggingFace API fails, plus an `IMAGE_PROVIDER` environment variable for direct Pollinations usage during local testing.

**Rationale**: HuggingFace free tier has usage limits. When the quota is exhausted, article generation fails entirely. Pollinations.ai provides a free, no-API-key alternative using the Flux model. The `IMAGE_PROVIDER=pollinations` environment variable allows bypassing HF entirely for quick local testing without consuming HF quota.

**Rejected Alternatives**:
- HuggingFaceの完全な置き換え: HFの画質がPollinationsより安定しているため、プライマリは維持
- APIキーが必要なサービス (SiliconFlow, Cloudflare Workers AI): 設定コストが高く、ローカルテストの利便性が下がる

**Impact**:
- `scripts/generate_article.py`: `import requests`追加、`_save_as_avif()` ヘルパー関数分離、`_generate_image_pollinations()` フォールバック関数追加、`generate_and_save_image()` にフォールバックロジック追加、`IMAGE_PROVIDER` 環境変数対応

## 2026-09-30: Meta Description Validation

**Decision**: Extract first sentence from article body to extend short descriptions. Add regex safety.

**Rationale**: `_validate_description()` padded short descriptions with meaningless characters (`。` and spaces). 30% of recent articles had descriptions under 80 chars. Regex substitution was vulnerable to backslash characters in description text.

**Rejected Alternatives**:
- LLMでdescriptionを再生成: APIコストが高く、生成時間が伸びる
- 既存記事の無視: SEOが継続的に劣化する

## 2026-09-30: CSS-Only Bullet List Affiliate Card Styling

**Decision**: Style bullet list affiliate links as card-style elements using CSS `:has()` selector, without modifying Python templates.

**Rationale**: Bullet list links (`- 📦 [Amazonで〜を探す](url)`) were rendered as plain underlined text, inconsistent with the visual product cards. CSS-only approach avoids template changes and retroactively applies to all existing posts.

**Rejected Alternatives**:
- Pythonテンプレートの変更: 既存記事に遡及適用できない
- HTMLの完全な書き換え: 既存記事の再生成が必要でコストが高い

## 2026-09-30: Affiliate Keyword Contextualization

**Decision**: Change affiliate keyword priority to "article-extracted > filtered trend_keywords > tags fallback".

**Rationale**: `inject_affiliate_links()` used `trend_keywords` directly, which contained GitHub repo names (e.g., "o3-pro", "langgraph") that produced irrelevant affiliate search results. Article tags and body text reflect the actual article theme, producing more relevant product search links.

**Rejected Alternatives**:
- trend_keywordsをそのまま使用: GitHubリポジトリ名が混入し、無関係な検索結果になる
- tagsのみを使用: 記事のテーマを十分に反映できない

## 2026-09-30: Affiliate Link HTML `<a>` Tag Conversion

**Decision**: Change `inject_affiliate_links()` to generate HTML `<a>` tags instead of Markdown `[text](url)` links for affiliate search links.

**Rationale**: Markdown link syntax exposes the full URL with UTM tracking parameters in the rendered page source and potentially in the visual output. HTML `<a>` tags hide the raw URL, showing only the link text. Existing post files are left unchanged as a separate batch-fix issue.

**Rejected Alternatives**:
- 内部リダイレクトページ: 実装コストが高く、既存のデプロイフローを変更する必要あり
- CSSのみで隠蔽: MarkdownリンクのURLはHTMLソースに残るため完全な隠蔽不可能
- 既存記事の一括修正: 修正スクリプトの作成・検証に時間がかかるため保留

**Impact**:
- `scripts/generate_article.py`: `inject_affiliate_links()` のリンク生成ロジックを `<a>` タグに変更
- `docs/ai/known-issues.md`: 既存記事のリンク形式を保留イシューとして追加

## 2026-10-02: e621 rating:safe for Kemono Trending Works

**Decision**: Add `rating:safe` or `rating:questionable` to e621 tag queries to avoid NSFW filtering. Expand tags to include furry/wolf/fox/rabbit species with `order:score` for trending works tracking.

**Reason**: Without rating restrictions, e621 queries returned mostly NSFW content that was filtered out (30/35 posts filtered). Adding `rating:safe` ensures usable SFW results. Expanding species tags captures more kemono/furry trending works.

**Rejected Alternatives**:
- NSFWフィルタの緩和: 生成された記事に不適切なコンテンツが含まれるリスク
- e621の完全な置き換え: 公開APIで認証不要な代替ソースが限られる

**Impact**:
- `fetch_topics.py`: `E621_TAGS` に `rating:safe` または `rating:questionable` を追加、furry/wolf/fox/rabbit の `order:score` クエリを追加
- kemono カテゴリの e621 収集件数が 3件 → 30件に増加

## 2026-10-02: Replace latest.json Symlink with File Copy

**Decision**: Replace `os.symlink()` with `shutil.copy2()` for `data/topics/latest.json`, converting it from a symlink to a regular file copy of the latest timestamped file.

**Reason**: The symlink stored an absolute path (e.g., `/home/runner/work/...` from GitHub Actions) in git, making it broken on local Windows and GitHub Pages. Symlinks require `core.symlinks` configuration and admin privileges on Windows, causing cross-platform incompatibility. Both consumers (`generate_article.py` reading topics and `fetch_topics.py` inheriting `fetched_at`) only need the file content, not symlink behavior.

**Rejected Alternatives**:
- シンボリックリンクを維持: 絶対パスがコミットされ、クロスプラットフォームで壊れる
- `.gitattributes` で `core.symlinks=true` 設定: 開発環境ごとに設定が必要で信頼性低い
- `data/latest_topics.json` の単一ファイルに戻す: タイムスタンプファイルの履歴追跡が失われる

**Impact**:
- `fetch_topics.py`: `os.symlink()` → `shutil.copy2()`, `import shutil` 追加
- `test_fetch_topics.py`: シンボリックリンク検証テストをファイルコピー検証に更新
- `data/topics/latest.json`: git 管理下の通常ファイルとしてコミット可能に


