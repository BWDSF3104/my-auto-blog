# UTF-8 化検討（全ファイルエンコード監査）

**Status**: 完了 (2026-10-11)

## 背景

ユーザー依頼: 「全てのファイルのutf8化を検討。現状のプロジェクト内ファイルのエンコードを確認」。

## 調査対象

- 対象: プロジェクト内テキストファイル 323 件（バイナリ: png/avif/ico/pyc 等、`.git`、`node_modules`、`dist` は除外）
- 手法: バイト列ベースの検出スクリプト（BOM 判定 → UTF-8 可変換性 → cp932/shift_jis フォールバック判定）+ git 履歴照合
- git 状態: main ブランチ・worktree（`hallowed-fedora`）ともに作業ツリークリーン。main = 最新。

## 調査結果

| エンコード | 件数 | 内容 |
|-----------|------|------|
| ASCII（UTF-8 互換） | 85 | 非ASCII文字なし。問題なし |
| UTF-8（BOM なし） | 205 | 正常。新記事・スクリプト・docs の大半 |
| UTF-8 BOM 付き | 32 | 旧記事 30 件 + 他 2 件（下記） |
| CP932（Shift_JIS） | 1 | 旧 worktree の `deploy.yml`（文字化け） |

### UTF-8 BOM 付き 32 件の内訳

- `src/content/posts/` 旧記事 30 件: 2026-09-26 〜 2026-09-30-105356（BOM + CRLF）。2026-09-30-224625 以降の記事は BOM なし
- `affiliate-link-context.txt`: BOM + CRLF
- `.kilo/scripts/safe-remove.ps1`: BOM + CRLF（**意図的・必須**）

### CP932 1 件

- `.kilo/worktrees/hallowed-fedora/.github/workflows/deploy.yml`: 旧 worktree ブランチにのみ存在。cp932 としてデコード可能だが日本語が欠損（「日本時間 8:00 に実?」等）= 破損済み
- main の `deploy.yml` は 2026-10-08（`8366c32`）に cp932→UTF-8 変換済み。本件は旧 worktree の残骸のみ

## 分析

1. **新規ファイルは全て UTF-8（BOM なし）** — `generate_article.py` 等の全 Python スクリプトが `encoding="utf-8"` 明示指定で読み書き。パイプライン由来の新規 BOM 発生はなし
2. **BOM 記事の由来は旧方式** — 2026-09-30 以前の記事は PowerShell `Set-Content`（PS 5.1 の utf8 は BOM 付与）等の旧経路で書かれた可能性。AGENTS.md の PowerShell パイプ禁止ルール導入前のもの
3. **BOM が機能に与える影響: なし（現状）** — 記事処理は regex ベースのフィールド抽出（`re.search(r'^title:...')`）で、1 行目の BOM に依存しないコードは grep 確認でなし。Astro build も BOM 記事を含む現行状態で成功
4. **`safe-remove.ps1` の BOM は必須** — Windows PowerShell 5.1 は BOM なし .ps1 を ANSI（cp932）として解析するため、日本語コメント入りの本ファイルは BOM 除去してはならない
5. **改行コードは CRLF/LF 混在** — 本タスクの範囲外だが、`.gitattributes` による正規化は未導入

## 推奨（要ユーザー判断）

| # | 対応 | 推奨 | 理由 |
|---|------|------|------|
| 1 | BOM 付き旧記事 30 件を UTF-8（BOM なし）へ正規化 | **推奨** | 新記事・スクリプトと統一。BOM は frontmatter 直前に `\ufeff` を挟み、ツールによっては不具合の原因になり得る（現状影響なし） |
| 2 | `affiliate-link-context.txt` の BOM 除去 | 推奨（任意） | 上記と同様の一貫性 |
| 3 | `safe-remove.ps1` の BOM | **除去しない** | PS 5.1 の UTF-8 認識に必須 |
| 4 | 旧 worktree `hallowed-fedora` の整理（破損 deploy.yml 含む） | 推奨 | 不要な旧ブランチの削除。main 側は正常 |
| 5 | `.gitattributes` による改行コード正規化 | 任意 | 別タスクとして検討 |

## 実施内容 (2026-10-11)

ユーザー指示で推奨 #1・#2・#4 を実施、#5 は別タスク化（backlog P3 #8 へ）。

### #1・#2: BOM 除去（31 ファイル）

- 対象: BOM 付き旧記事 30 件（2026-09-26 〜 2026-09-30-105356）+ `affiliate-link-context.txt`
- 手法: バイト列ベースのスクリプト（`C:\Users\fujim\AppData\Local\Temp\kilo\strip_bom.py`）。BOM 先頭を検証 → 3 バイト除去 → 残りは UTF-8 検証後に書き戻し。**CRLF 改行は維持**（改行コードは本タスク対象外）
- `safe-remove.ps1` の BOM は PS 5.1 必須のため除去していない（推奨 #3 通り）

### #2 の影響確認

`affiliate-link-context.txt` はコード・スクリプトから参照なし（grep 確認、Memory Bank 記載のみ）。アフィリエイトリンクテンプレートの参照ファイル。BOM 除去はパイプラインに**影響なし**。

### #4: 旧 worktree `hallowed-fedora` の削除

- 旧 worktree のセッション `ses_f17214b09ffejf6DQcyjy7nryh` を Agent Manager で停止・削除
- `git worktree remove` + `git branch -d hallowed-fedora`（`ahead 0, behind 330` で main に完全取り込み済み、破損 deploy.yml は不要な旧ブランチのみ）
- worktree ディレクトリ `.kilo/worktrees/hallowed-fedora` は削除済み（`Test-Path` = False）

### #5: 別タスク化

`.gitattributes` による改行コード正規化は backlog P3 #8 へ記録（単独タスクで実施予定）。

## Verification

- BOM 除去後: 再スキャンで UTF-8 BOM 付きは `safe-remove.ps1` のみ 1 件（意図的）、CP932 は 0 件（旧 worktree 削除で解消）。差分は各ファイル 1 行目 BOM のみ（`git diff` 確認）
- `npm run build` → **135 page(s) built** (8.78s) 成功。BOM 除去で frontmatter 解析・ページ生成に異常なし

## Next Action

なし（#5 は backlog P3 #8 として別タスク化済み）
