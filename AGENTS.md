# my-auto-blog

Astro、Gemini AI、トレンドデータ収集で動作する自動ブログ生成システム。
静的サイトジェネレーターによるブログ。認証なし、データベースなし、SSR なし。GitHub Pages（`BWDSF3104.github.io/my-auto-blog`）へデプロイ。

## 言語

- 送信メッセージの言語に関わらず、ユーザーへの回答、進捗報告、説明、質問、作業結果、最終結果は日本語で行う。
- コード、コマンド、ファイルパス、API名、ライブラリ名などの正確な技術表記は原文を維持する。
- ユーザー向け回答を日本語にすることを理由として、プロジェクト内のファイル・データ・スクリプトの入力・出力を翻訳・変更してはならない。
- `docs/ai/` Memory Bank の新規エントリは日本語で記述。
- Git commit message: prefix は英語 (`feat:`, `fix:` など)、説明部分は日本語。

## 実装開始ゲート

- 明示的な実装開始指示を受けなければ、決して実装・ファイル変更を行わない。
  - 「実装」に含む除外: タスクファイル、decisions、`current-task.tsv`、`backlog.md`、known-issues、memory bank 等の「記録」更新。
  - 例外: ユーザーが設計〜実装を一任した場合は、別途の実装開始指示は不要。
  - 「明示的な実装開始指示」: 合意した設計の実装着手を示すユーザーの明らかな言葉（例: 「実装を開始して」「実装して」）。

## ターミナル安全

- 明示的なユーザー確認なしに、破壊的なターミナルコマンドを実行してはならない。
- 禁止: `rm -rf`、`git push --force`、`sudo`。
- ワークスペースルート外のファイル変更は禁止。**例外**: docs 内で参照されている外部フォルダでのユーザーとのファイル交換のみ。
- **ファイル削除**: `kilo-safe-remove <file>` を使う（`Remove-Item` / `del` は不可）。
- **フォルダ削除**: `kilo-safe-rmdir <folder>` を使う（`Remove-Item -Recurse` / `rmdir /s` は不可）。
- この2コマンドは **Windows ゴミ箱** へ削除する（復元可能・恒削除ではない）。実装（VB ラッパー）と根拠は `docs/ai/decisions/2026-10-18-recycle-bin-deletion.md` を参照。
- **正典ツール一元化**: `kilo-safe-*` / `task_manager.py` / `archive_memory_bank.py` はプロジェクトごとにコピーを持たず、`S:\Documents\Kilo_Commons\Common_Operations\bin\`（PATH 登録）の単一正典を使用。プロジェクトルート判定チェーン: `--root` 明示 > cwd（または指定パス）から `.git` 親方向探索 > cwd 自体。git は前提ではなく「あれば使う」（git add は repo 存在時のみ、なければ skipped）。詳細は Kilo_Commons `AGENTS.md` / `decisions/2026-10-29-central-tooling-bin.md`。
- **決して** PowerShell の `Get-Content` / `Set-Content` パイプラインでファイル内容を操作しないこと。UTF-8 エンコーディングを破損させる（BOM 付与、日本語文字化け）。
- **editツール以外でファイルを改写する場合**: 必ず事前に `git diff` でリモートとの差異がないことを確認し、改写後はファイルが破損していないことを確認すること。

## コマンド実行ルール

- **1 コマンド 1 行**: シェルコマンドは 1 行で実行する。コマンドを複数行に分割しないこと。複数の文が必要な場合は `;` で 1 行に結合する。
- **インラインコード実行禁止（言語無関係）**: コマンドラインに実行コードを埋め込む形のコマンドは、言語を問わず禁止（`python -c "..."`、`python -`、`powershell -c` / `powershell -Command "..."`、`node -e`、コードを `python` / `powershell` / `node` にパイプする等）。境界は「言語」ではなく「コードが埋まっているか」: フラグ・パスのみ（`git log`、`pytest`、`python -m pytest` 等）のコマンドは除外される。
  禁止の意図: 使い捨てのインライン文字列は許可コマンドリストと一致しないため、リストが再利用不可能なコマンドで汚染される。加えて PowerShell 5.1 ではクォーティング・エンコーディングが壊れやすい。
  代わりに（全言語共通）:
  1. コードをスクラッチフォルダ `docs\ai\tmp\` にファイルとして書き出す（例: `docs\ai\tmp\fetch_check.py` / `.ps1`）。
  2. `python <file>` / `powershell docs\ai\tmp\<file>.ps1` で実行する。
  3. 出力ファイルも同じスクラッチフォルダに保持する。
  - 使い捨てスクリプトを本番コードディレクトリ（例: `scripts/`）に置かないこと。`docs/ai/tmp/` は gitignore 対象で、7 日以上更新のないエントリは正典 `S:\Documents\Kilo_Commons\Common_Operations\bin\archive_memory_bank.py`（cwd ルート）で削除される。

## コード検証

- **Python変更後**: `pytest scripts/tests/ -v` で全テスト通過を確認。`maintenance/`（開発ツール）を変更した場合は加えて `pytest maintenance/tests/ -v` も実行する。正典ツール（task_manager / archive_memory_bank）のテストは Kilo_Commons `tests/`（`python -m pytest tests/ -v`）に集約済み。
- **Astro変更後・記事生成後**: `npm run build` でビルド成功を確認。
- **`scripts/prompts/` のみ変更**: 検証不要。
- **レイアウト変更後**: ビルド後、出力HTMLを解析して構造を検証（クラス名、要素階層、コンテンツ順序）。修正完了時に、ユーザーに `I:\マイドライブ\kilo` 下のスクリーンショットを送付する（サブフォルダで日付・タスク名を区切可）。
- **git commit 前**: 変更内容に応じて再実行（Python→pytest, Astro→build、両方→両方）。
- 現行項目のビルド/テスト完了基準を満たすまで、次の計画項目を開始しないこと。
- 成功時は `docs/ai/tasks/` の該当タスクファイルの Verification セクションにコマンド・結果・経過時間を記録。
- **例外**: `docs/ai/` と `AGENTS.md` のみの変更は pytest / build 不要。
- **fetch_topics.py 更新後**: `python scripts/tests/test_real_apis.py --save` で各データソースの応答を確認（結果は `scripts/data/api_test_results/` に保存）。

### テストスクリプトルール

- テストスクリプトは外部APIを実際に呼び出してはならない。API キー・クォータ・レート制限がかかるサービス（Gemini AI, HuggingFace, Kemono API, e621 など）は `unittest.mock` でモックする。
- **例外**: RSS フィードは公開エンドポイントで認証・クォータ不要のため実呼出しを許可。
- レート制限の詳細: `docs/ai/api-rate-limits.md`

## 開発

- Dev サーバー: `astro dev --background`
- バックグラウンドサーバー: `astro dev stop`、`astro dev status`、`astro dev logs`

## ユーザーやり取りフォルダ

- ユーザーとのファイル交換用: `I:\マイドライブ\kilo`
- `I:` は Google Drive for Desktop の仮想ドライブ（VDF）。

## 画像解析

- 画像の視覚解析: `analyze_image_with_groq`。クラウド送信しない画像（認証情報・APIキー・個人情報等を含む）はローカルモデルで解析。
- 使い方・例・メンテナンス: `docs/ai/image-analysis.md`。

## コード規約

- Python スクリプト: UTF-8 エンコーディング
- トレンドデータ: `data/topics/latest.json`
- 生成記事: `src/content/posts/`
- 生成画像: `public/images/`

## ドキュメント

- Astro ドキュメント: https://docs.astro.build
- 変更前にガイドを確認すること: routing、components、framework integration、content collections、styling、i18n

## AI Memory Bank

`docs/ai/memory-bank-guide.md` を以下のタイミングで参照すること:

- **タスク開始時**
- **意味のあるステップ完了後**
- **設計・方針を選定・確定したタイミング**
- **タスク完了時（git commit 前）**
- **中断からの再開時**

### タスク開始時（調査開始段階）

調査開始段階（タスク受理直後・調査着手時）で実行（初回コード変更前では遅い）:
`python S:\Documents\Kilo_Commons\Common_Operations\bin\task_manager.py add --slug <short-name> --title "<タスク名>" [--backlog "P<N> #<N>"] [--next-action "<next action>"]`
実行効果: タスクファイル `docs/ai/tasks/YYYY-MM-DD-short-name.md` の作成 + `current-task.tsv` 参照行追加（自動）
- `--slug`: タスク短名（小文字英数字とハイフンのみ。例 `task-slash-commands`）
- `--title`: タスク名（タスクファイルの `#` 見出し）
- `--backlog`: バックログ参照 `P<N> #<N>`（該当する場合）
- `--next-action`: 次のアクション（`current-task.tsv` の 3 列目に記録）
タスク作成後は `python S:\Documents\Kilo_Commons\Common_Operations\bin\archive_memory_bank.py`（dry-run 確認後 `--apply`）を実行する。
タスク開始の完了前に実装着手しないこと。

### 設計・方針を選定・確定したタイミング

設計や方針（構造・データフロー・新しい統合・採用技術など）を選定・確定したタイミングで、タスクファイル（`docs/ai/tasks/` の該当ファイル）の「調査結果 / 変更内容」セクションを即座に更新すること。選定した内容とその根拠（必要に応じて代替案）を記録し、タスク完了時の一括記録を先延ばしにしてはならない。重要な設計判断は加えて `decisions/` に新ファイルとして記録する。

### タスク実行中に発見した非必須問題

タスク実行中に、そのタスクの完了に必須でない問題（主進行を阻害しない）を見つけた場合は、その場で修復に枝打つことなく `known-issues/` に新ファイルとして記録し、タスクを先に進めること。
タスク完了を阻害する問題（blocker）は本ルールの対象外であり、先に修復するかユーザーに報告すること。

用語: 「issue」は本プロジェクトのローカル `docs/ai/known-issues/`（解決済みは `archive/` サブフォルダへ移動）を指す。GitHub Issues を指すものではない。

### タスク終了

タスク完了時に実行:
`python S:\Documents\Kilo_Commons\Common_Operations\bin\task_manager.py end --task <パス / date-slug / slug>`
実行効果:
- `Status` を `完了` へ
- `current-task.tsv` 参照行削除
- レポート出力（「対応項目チェック」含む）

**対応項目チェック**（`end` の読み取り専用出力 — 判断・実行はエージェント）:
- `docs/ai/known-issues/`（top・`archive/`）をタスクファイルの KI ID（`KI-\d{8}-\d{1,3}`）/ タスクパス参照で照合
- `docs/ai/backlog.md` をタスクファイルの `**Backlog**: P<N> #<N>` 欄 / 行内タスク参照で照合
- 一致候補について: ファイルパス・現在の位置（未解決/解決済）・推奨動作（archive へ mv / 完了時に backlog 削除）を報告

### 中断と compaction

- タスクが中断された場合は、`docs/ai/current-task.tsv` を再開可能な状態に残しておくこと。
- compaction 以降、以前の会話コンテキストがまだ使えると仮定しないこと。

## ワークフロー

- タスク開始: コマンド・パラメータ・効果は「タスク開始時（調査開始段階）」を参照
- タスク終了: コマンド・効果・対応項目チェックは「タスク終了」を参照
- 両とも既定で反映、プレビューのみなら `--dry-run`、staging スキップなら `--no-git-add`。
- git commit / push / deploy: `docs/ai/workflows.md` を参照する。commit・push は検証完了時点で判断可。**前提**: 変更の詳細について事前にユーザーから承認を受けていること。
- タスク切り替え: 現行タスクが「進行中」なら、先にそのタスクの end を実行。「保留」のタスクは除外。
- ユーザーが手動記事作成を依頼した際: `docs/ai/manual-article-workflow.md` を参照する。
- デバッグが必要な際（Python スクリプトのバグ調査・変数確認・ステップ実行）: `docs/ai/debugging.md` を参照する。

## プロジェクト構成

```
my-auto-blog/
├── scripts/                   # Python 自動化スクリプト
│   ├── fetch_topics.py        # トレンドデータ収集
│   ├── generate_article.py    # 記事生成（エントリ + パイプライン）
│   ├── article/               # article/ パッケージ（config/gemini/image/affiliate/trends/frontmatter/slug_links/meta/characters/geninfo）
│   └── prompts/               # プロンプトテンプレート
├── hf-space/                  # 自社 HuggingFace Space のデプロイ元ソース（blume/kemono-image-api / SDXL パイプライン）
├── maintenance/               # 開発ツール（本番パイプライン外）
│   ├── archive_memory_bank.py # Memory Bank バッチクリーンアップ（デフォルトは dry-run）
│   └── task_manager.py        # タスク開始/終了ヘルパー（add / end）
├── src/                       # Astro ソース
│   └── content/posts/         # 生成された Markdown 記事
├── public/                    # 静的アセット
│   └── images/                # 生成画像
├── data/                      # 収集データ
│   └── topics/                # トレンドトピック（タイムスタンプ付き + latest.json）
└── docs/ai/                   # AI Memory Bank（変化する知識）
```
