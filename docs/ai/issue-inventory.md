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

### A-5. architecture.md: 古くなった情報
- **ファイル**: `docs/ai/architecture.md`
- **検証結果**:
  - シンボリックリンク参照: 現在のプロジェクト構造にシンボリックリンク不存在
  - Bluesky: 「Active」と記載されているが、実際の収集コードでは実装されていない
  - RSS Feedparser: 実際のコードは `xml.etree.ElementTree` を使用（feedparser不使用）
  - Kemono API: 削除済みのコードがまだ記載されている
- **優先度**: 中
- **対応**: 実際のコードベースに合わせて更新。

### A-6. ideas.md: 膨張・重複・実装済み項目の残存
- **ファイル**: `docs/ai/ideas.md`
- **検証結果**: 約500行。重複するアイデアと、既に実装された機能のアイデアが残存。
- **優先度**: 低
- **対応**: 重複を削除。実装済み項目を削除またはアーカイブ。

### A-7. memory-bank-guide.md: コミットタイミングの矛盾
- **ファイル**: `docs/ai/memory-bank-guide.md`
- **検証結果**:
  - 4行目: 「更新タイミングは git commit 前」
  - 50行目: 「After git commit & push: Update docs/ai/current-task.md」
  - 同一ドキュメント内でコミット前 vs コミット後という矛盾した指示が存在
- **優先度**: 中
- **対応**: 指示を統一。AGENTS.mdの記述と整合させる。

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

### B-1. 記事ファイルにfrontmatterがない (最重要)
- **ファイル**: `src/content/posts/2026-09-30-224625-auto-post.md`
- **検証結果**: ファイルの先頭に `---` で囲まれたfrontmatterブロックが存在しないことを確認。
- **影響**: Astroのcontent collectionがこの記事を認識せず、ビルド時に除外される可能性。`PostLayout.astro` の `getStaticPaths` がこの記事をパスリストに含めない。
- **優先度**: 最高
- **対応**: frontmatterを補完するか、ファイルを削除する。

### B-2. e621 API: 日付フィルタ未実装
- **ファイル**: `scripts/fetch_topics.py:396`
- **検証結果**: API URLは `https://e621.net/posts.json?tags={encoded}&limit={limit_per_tag}` であり、`date_filter`、`date_min`、`date_max` パラメータが含まれていない。
- **影響**: 古い投稿がトレンドデータに混入する可能性。e621 APIは日付範囲フィルタをサポートしているが未活用。
- **優先度**: 高
- **対応**: URL構築に `date_min` パラメータを追加。例: `date_min=1727740800` (2024/10/01のUnix timestamp)。

### B-3. e621 API: タグフィルタの補強
- **ファイル**: `scripts/fetch_topics.py:389-396`
- **検証結果**: 検索クエリは `E621_TAGS` 配列で定義されているが、取得結果のタグに明示的なフィルタロジックが弱い。`_is_nsfw_post()` は rating `e` (explicit) と既知のNSFWタグセットでフィルタするが、`r` (questionable) レーティングの投稿は通過する。
- **優先度**: 中
- **対応**: 物語モードでは `r` レーティングもフィルタするか、`safe` レーティングのみを許可する。

### B-4. 記事に character_1 プレースホルダーが残存
- **ファイル**: `src/content/posts/*.md` (複数ファイル、36件)
- **検証結果**: `character_1` というプレースホルダー文字列が生成記事に36件残存していることを確認。
- **影響**: 記事本文に未置換のプレースホルダーが表示される。
- **優先度**: 高
- **対応**: `generate_article.py` のキャラクター名置換ロジックを修正。既存記事のプレースホルダーをバッチ置換。

### B-5. PostLayout.astro: TOCハイライトの複数同時付与
- **ファイル**: `src/layouts/PostLayout.astro:616-630`
- **検証結果**: `IntersectionObserver` のコールバックで `entry.isIntersecting` 時に `toc-link-active` を追加、`false` 時に削除する。しかし、複数の見出しが同時に交差領域内にある場合、複数のTOCリンクにアクティブクラスが付与される。
- **コード**:
  ```javascript
  entries.forEach(entry => {
    const link = tocList.querySelector('a[href="#' + entry.target.id + '"]');
    if (link) {
      if (entry.isIntersecting) {
        link.classList.add('toc-link-active');
      } else {
        link.classList.remove('toc-link-active');
      }
    }
  });
  ```
- **優先度**: 中
- **対応**: 交差する見出しが見つかった場合、まず全TOCリンクからアクティブクラスを削除してから対象に付与する。

### B-6. PostLayout.astro: ダークモードセレクタの脆弱性
- **ファイル**: `src/layouts/PostLayout.astro:393, 457, 466, 497, 502`
- **検証結果**: `:root[class~="dark"]` セレクタを使用。これは `<html>` 要素に `dark` クラスが付与されていることを前提とする。ThemeInitコンポーネントがこれを管理しているが、セレクタがグローバルスタイル内で使用されているため、コンポーネントのバグ時にダークモードCSSが効かなくなる。
- **優先度**: 低
- **対応**: Tailwindの `dark:` 修飾子と整合するセレクタに統一するか、`@media (prefers-color-scheme: dark)` のフォールバックを追加。

### B-7. [tag].astro: 未使用のHeaderインポート
- **ファイル**: `src/pages/tags/[tag].astro:2`
- **検証結果**: `Header` コンポーネントをインポートしているが、テンプレート側で使用されていないことを確認。
- **優先度**: 低
- **対応**: 未使用インポートを削除。

### B-8. tailwind.config.mjs: ESMでrequire()使用
- **ファイル**: `tailwind.config.mjs:9`
- **検証結果**: `.mjs` ファイル（ESMモジュール）内で `require('@tailwindcss/typography')` を使用。現在のNode.jsバージョンでは機能するが、厳密なESM環境ではエラーになる。
- **優先度**: 低
- **対応**: `import createPlugin from '@tailwindcss/typography'` 形式に書き換えるか、`.cjs` に拡張子を変更する。

### B-9. test_real_apis.py: pytest収集防止の不確実性
- **ファイル**: `scripts/tests/test_real_apis.py:31`
- **検証結果**: `__test__ = False` を設定しているが、`conftest.py` に `collect_ignore` が設定されていない。pytestのバージョンによっては収集される可能性。
- **優先度**: 中
- **対応**: `conftest.py` に `collect_ignore = ["test_real_apis.py"]` を追加。

### B-10. test_real_apis.py: PYTHONIOENCODINGの設定タイミング
- **ファイル**: `scripts/tests/test_real_apis.py:34-35`
- **検証結果**: `os.environ["PYTHONIOENCODING"] = "utf-8"` をモジュール読み込み時に設定。しかし、PythonのIOストリームはインタープリタ起動時に決定されるため、この設定は効果がない可能性。
- **優先度**: 低
- **対応**: スクリプトの先頭で `sys.stdout` / `sys.stderr` を再ラップするか、実行時のコマンドラインオプションで設定する。

---

## C. 環境・プロジェクトの問題

### C-1. Reddit APIの収集機能
- **ファイル**: `scripts/fetch_topics.py:220-268`
- **検証結果**: `collect_reddit()` 関数が存在し、`reddit.com/r/{sub}/hot.json` と `old.reddit.com/r/{sub}/hot.json` の2つのエンドポイントをフォールバック付きで呼び出す。
- **状態**: 機能は実装済み。ユーザーの優先順位では「Kemono API削除 & e621フィルタ」が優先。Redditの削除・変更はユーザーの指示を待つ。
- **優先度**: 高 (ユーザー指定)
- **対応**: 未着手。ユーザーの指示を待つ。

### C-2. 古いデータファイル
- **ファイル**:
  - `data/latest_topics.json`
  - `scripts/data/latest_topics.json`
- **検証結果**: 両方のパスに `latest_topics.json` が存在。`scripts/data/` 下のファイルは古いデータを含む可能性。
- **優先度**: 低
- **対応**: `scripts/data/latest_topics.json` を削除するか、データフローの単一真理源を明確にする。

### C-3. Astroテンプレートの残骸
- **ファイル**:
  - `src/components/Welcome.astro`
  - `src/layouts/Layout.astro`
  - `src/assets/astro.svg`
  - `src/assets/background.svg`
- **検証結果**: 4ファイルがすべて存在することを確認。これらはAstroプロジェクト生成時のデフォルトテンプレート。
- **優先度**: 低
- **対応**: 未使用であることを確認後、削除する。

### C-4. CLAUDE.md
- **検証結果**: リポジトリ内に `CLAUDE.md` は存在しないことを確認。
- **優先度**: 高 (ユーザー指定)
- **対応**: 未着手。Kilo用の設定ファイル (`AGENTS.md`, `.kilocoderules`) が代替として機能している。

### C-5. .vscode/settings.json
- **検証結果**: ファイルが存在しないことを確認。
- **優先度**: 低
- **対応**: 必要に応じて作成する。

---

## 優先順位まとめ (ユーザー指定順)

1. **B-1**: frontmatter欠落記事の修正 (最高)
2. **C-1 + B-2**: Reddit/Kemono対応 + e621日付フィルタ (高)
3. **C-4**: CLAUDE.md対応 (高、ユーザー指定)
4. **B-4**: character_1プレースホルダー (高)
5. **B-5**: TOCハイライトバグ (中)
6. **B-9**: pytest収集防止 (中)
7. **A-5**: architecture.md更新 (中)
8. **A-7**: memory-bank-guide.mdの矛盾 (中)
9. **B-3**: e621レーティングフィルタ (中)
10. その他 (低)
