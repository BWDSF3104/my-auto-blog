# 課題一覧 (Issue Inventory)

生成日: 2026-10-02
検証方法: ファイル読み取り、grep検索、globパターンマッチによる実コード検証

---

## A. ドキュメント不整合 (docs/ai/)

### A-1. current-task.md: 完了タスクが11件残存
- **ファイル**: `docs/ai/current-task.md`
- **ルール**: アクティブタスクのみ保持。完了タスクは `tasks/` へ個別ファイルとして移動
- **検証結果**: 11件の完了タスクが記録されていることを確認。ルール違反。
- **優先度**: 低
- **対応**: 完了タスク参照行を削除。個別ファイルは `tasks/` に存在するため削除不要。

### A-2. decisions.md: 閾値超過・英語エントリ・重複・廃止マーク欠如
- **ファイル**: `docs/ai/decisions.md`
- **ルール**: 15件以上でアーカイブへ移動
- **検証結果**:
  - エントリ数: 約17件（閾値15件超過）
  - 10/02エントリが英語で記述（言語ルール違反: 新規エントリは日本語）
  - 重複する決定エントリが存在
  - 新決定によって無効化された旧決定に「廃止」マークがない
- **優先度**: 低
- **対応**: 古いエントリを `decisions-archive.md` へ移動。英語エントリを日本語に翻訳。重複を削除。無効化された決定にマークを追加。

### A-3. known-issues.md: 解決済がアーカイブされていない
- **ファイル**: `docs/ai/known-issues.md`
- **ルール**: 解決済エントリは即時アーカイブへ移動（閾値: 1件以上）
- **検証結果**: 解決済としてマークされた問題が本体に残存していることを確認。
- **優先度**: 低
- **対応**: 解決済エントリを `known-issues-archive.md` へ移動。

### A-4. plans.md: Completed Plansが10件残存
- **ファイル**: `docs/ai/plans.md`
- **ルール**: Completed Plansは直近5件まで保持。6件以上でアーカイブへ移動
- **検証結果**: Completed Plansに10件の完了計画が記録されていることを確認。
- **優先度**: 低
- **対応**: 古い5件を `plans-archive.md` へ移動。直近5件を保持。

### A-5. ~~architecture.md: 古くなった情報~~ ✅ 完了
- **ファイル**: `docs/ai/architecture.md`
- **検証結果**:
  - シンボリックリンク参照: `data/topics/latest.json` は存在確認済み
  - Bluesky: 実装確認済み（`collect_bluesky()` 関数存在、公開エンドポイント使用、APIキー不要）
  - RSS Feedparser: 実際のコードは `xml.etree.ElementTree` を使用（feedparser不使用）
  - Kemono API: 実装確認済み（`collect_kemono_api()` 関数存在）
  - RSSカテゴリ: 記載は "tech" のみだが、実際は tech/pokemon の両方
  - GitHubカテゴリ: 記載は "tech/kemono" だが、実際は kemono/pokemon
  - Redditカテゴリ: 記載は "kemono/tech" だが、実際は kemono/pokemon/tech
  - Bluesky APIキー: APIキー不要だが、API Keysテーブルに `BLUESKY_API_KEY` が記載されていた
- **優先度**: 中
- **対応**:
  - RSS API列: "Feedparser" → "xml.etree.ElementTree"
  - RSS カテゴリ列: "tech" → "tech/pokemon"
  - GitHub カテゴリ列: "tech/kemono" → "kemono/pokemon"
  - Reddit カテゴリ列: "kemono/tech" → "kemono/pokemon/tech"
  - API Keysテーブルから Bluesky行を削除

### A-6. ideas.md: 膨張・重複・実装済み項目の残存
- **ファイル**: `docs/ai/ideas.md`
- **検証結果**: 約500行。重複するアイデアと、既に実装された機能のアイデアが残存。
- **優先度**: 低
- **対応**: 重複を削除。実装済み項目を削除またはアーカイブ。

### A-7. ~~memory-bank-guide.md: コミットタイミングの矛盾~~ ✅ 完了
- **ファイル**: `docs/ai/memory-bank-guide.md`
- **検証結果**:
  - 4行目: 「更新タイミングは git commit 前」
  - 50行目: 「After git commit & push: Update docs/ai/current-task.md」
  - 同一ドキュメント内でコミット前 vs コミット後という矛盾した指示が存在
- **優先度**: 中
- **対応**: 50行目の指示を「タスク完了時（git commit 前）」に修正。4行目のルールと整合させた。

### A-8. tasks/2026-10-02-rate-limit-research.md: 古いステータス・AGENTS.md参照
- **ファイル**: `docs/ai/tasks/2026-10-02-rate-limit-research.md`
- **検証結果**:
  - Status: 「完了 (コミット前)」のまま
  - AGENTS.mdの更新方法を記載しているが、現在のAGENTS.mdとは内容がずれている
- **優先度**: 低
- **対応**: Statusを「完了」に更新。AGENTS.mdの参照を更新。

### A-9. tasks/2026-10-01-reddit-alternatives.md: 古いNext Action
- **ファイル**: `docs/ai/tasks/2026-10-01-reddit-alternatives.md`
- **検証結果**: 完了タスクだが「Next Action」セクションが残存。
- **優先度**: 低
- **対応**: Next Actionを削除。

---

## B. コードのバグ・問題

### B-1. ~~記事ファイルにfrontmatterがない~~ ✅ 完了
- **ファイル**: `src/content/posts/2026-09-30-224625-auto-post.md`
- **検証結果**: frontmatterブロックが存在しないことを確認。
- **対応**: title, pubDate, description, author, tagsを含むfrontmatterを補完。ビルド成功を確認。

### B-2. ~~e621 API: 日付フィルタ未実装~~ ✅ 完了
- **ファイル**: `scripts/fetch_topics.py:396`
- **検証結果**: `date_min` パラメータが含まれていなかった。
- **対応**: URL構築に `date_min` パラメータを追加（直近30日の投稿のみ）。pytest 134件全テスト通過。

### B-3. ~~e621 API: タグフィルタの補強~~ ✅ 完了
- **ファイル**: `scripts/fetch_topics.py:271-287`
- **検証結果**: `_is_nsfw_post()` は rating `e` (explicit) と既知のNSFWタグセットでフィルタするが、`q` (questionable) レーティングの投稿は通過する。
- **優先度**: 中
- **対応**: `rating in ("e", "q")` に変更して questionable もフィルタ対象に追加。関連テストを更新。134 tests passed.

### B-4. ~~記事に character_1 プレースホルダーが残存~~ ✅ 完了
- **ファイル**: `src/content/posts/*.md` (複数ファイル)
- **検証結果**: 本文内の `[character_N]` 形式とaltテキスト内の `character_N` が残存していた。
- **対応**:
  - `generate_article.py` に `replace_character_placeholder()` 関数を追加。`process_inline_images()` のaltテキスト処理で `character_N` を種族記述に置換。
  - 既存記事の本文 `[character_N]` を手動置換（2026-10-01-180939のみ）。
  - 既存記事のaltテキスト `character_N` を5ファイル6件分クリーンアップ。
  - pytest 134件全テスト通過。ビルド成功。

### B-5. ~~PostLayout.astro: TOCハイライトの複数同時付与~~ ✅ 完了
- **ファイル**: `src/layouts/PostLayout.astro:616-630`
- **検証結果**: 複数の見出しが同時に交差領域内にあると複数のTOCリンクにアクティブクラスが付与された。
- **対応**: `isIntersecting` 時に全TOCリンクからアクティブクラスを削除してから対象に付与するよう修正。ビルド成功。

### B-6. ~~PostLayout.astro: ダークモードセレクタの脆弱性~~ ✅ 対応不要
- **ファイル**: `src/layouts/PostLayout.astro`, `src/styles/global.css`
- **検証結果**: `:root[class~="dark"]` は Tailwind の `darkMode: 'class'` 設定が生成する標準セレクタ。ThemeInit コンポーネントが `<html>` に `dark` クラスを付与する仕組みと整合。
- **結論**: Tailwind の設計仕様でありバグではない。フォールバック不要。

### B-7. ~~[tag].astro: 未使用のHeaderインポート~~ ✅ 完了
- **ファイル**: `src/pages/tags/[tag].astro:2`
- **検証結果**: `Header` コンポーネントをインポートしているが、テンプレート側で使用されていないことを確認。
- **優先度**: 低
- **対応**: 未使用インポートを削除。ビルド成功。

### B-8. ~~tailwind.config.mjs: ESMでrequire()使用~~ ✅ 完了
- **ファイル**: `tailwind.config.mjs:9`
- **検証結果**: `.mjs` ファイル（ESMモジュール）内で `require('@tailwindcss/typography')` を使用。
- **優先度**: 低
- **対応**: `import typography from '@tailwindcss/typography'` に書き換え。ビルド成功。

### B-9. ~~test_real_apis.py: pytest収集防止の不確実性~~ ✅ 完了
- **ファイル**: `scripts/tests/conftest.py`
- **検証結果**: `collect_ignore` が設定されていない。
- **対応**: `collect_ignore = ["test_real_apis.py"]` を追加。pytest 134件全テスト通過。

### B-10. ~~test_real_apis.py: PYTHONIOENCODINGの設定タイミング~~ ✅ 完了
- **ファイル**: `scripts/tests/test_real_apis.py:34-35`
- **検証結果**: `os.environ["PYTHONIOENCODING"]` はインタープリタ起動時にのみ有効。
- **優先度**: 低
- **対応**: `sys.stdout.reconfigure(encoding="utf-8")` に変更。pytest 134件全テスト通過。

---

## C. 環境・プロジェクトの問題

### C-1. Reddit APIの収集機能
- **ファイル**: `scripts/fetch_topics.py:220-268`
- **検証結果**: `collect_reddit()` 関数が存在し、`reddit.com/r/{sub}/hot.json` と `old.reddit.com/r/{sub}/hot.json` の2つのエンドポイントをフォールバック付きで呼び出す。
- **状態**: 機能は実装済み。ユーザーの優先順位では「Kemono API削除 & e621フィルタ」が優先。Redditの削除・変更はユーザーの指示を待つ。
- **優先度**: 高 (ユーザー指定)
- **対応**: 未着手。ユーザーの指示を待つ。

### C-2. ~~古いデータファイル~~ ✅ 完了
- **ファイル**: `data/latest_topics.json`, `scripts/data/latest_topics.json`
- **検証結果**: 両方とも旧ファイル。現在の真理源は `data/topics/latest.json`。
- **優先度**: 低
- **対応**: 両ファイルを削除。AGENTS.md のパス参照を `data/topics/latest.json` に更新。

### C-3. ~~Astroテンプレートの残骸~~ ✅ 完了
- **ファイル**: `src/components/Welcome.astro`, `src/assets/astro.svg`, `src/assets/background.svg`
- **検証結果**: Astro デフォルトテンプレートの残骸。未使用。
- **優先度**: 低
- **対応**: Welcome.astro と関連アセットを削除。`src/assets/` ディレクトリは空（safe-rmdir アローリスト外のため残留）。
  - `src/layouts/Layout.astro`
  - `src/assets/astro.svg`
  - `src/assets/background.svg`
- **検証結果**: 4ファイルがすべて存在することを確認。これらはAstroプロジェクト生成時のデフォルトテンプレート。
- **優先度**: 低
- **対応**: 未使用であることを確認後、削除する。

### C-4. ~~CLAUDE.md~~ ✅ 対応不要
- **検証結果**: リポジトリ内に `CLAUDE.md` は存在しないことを確認。
- **結論**: 本プロジェクトはKiloを使用。`AGENTS.md` と `.kilocoderules` が同等の役割を果たしているため、作成不要。

### C-5. ~~.vscode/settings.json~~ ✅ 対応不要
- **検証結果**: ファイルは存在し、Kilo auto-approve 設定として機能中。
- **優先度**: 低
- **対応**: 削除不要。有用な設定ファイルとして維持。

---

## 優先順位まとめ (ユーザー指定順)

1. ~~**B-1**: frontmatter欠落記事の修正~~ ✅ 完了
2. ~~**B-2**: e621日付フィルタ~~ ✅ 完了
3. ~~**C-4**: CLAUDE.md対応~~ ✅ 対応不要
4. ~~**B-4**: character_1プレースホルダー~~ ✅ 完了
5. ~~**B-5**: TOCハイライトバグ~~ ✅ 完了
6. ~~**B-9**: pytest収集防止~~ ✅ 完了
7. ~~**A-5**: architecture.md更新~~ ✅ 完了
8. ~~**A-7**: memory-bank-guide.mdの矛盾~~ ✅ 完了
9. ~~**B-3**: e621レーティングフィルタ~~ ✅ 完了
10. **C-1**: Reddit API (高、ユーザー指示待ち)
11. その他 (低)
