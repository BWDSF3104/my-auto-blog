# .gitattributes バイナリ定義追加（改行正規化第1ステップ）

**Status**: 完了
**Date**: 2026-10-21
**Backlog**: P3 #8
**Next Action**: .gitattributes 作成 → git ls-files --eol で画像 binary 化検証 → git diff --stat で画像差分なし確認

## 意図 / 背景

改行正規化（P3 #8）の第1ステップとして、`.gitattributes` に画像/バイナリ拡張子の `binary` 定義を追加。`* text=auto eol=lf`（第2ステップ）導入前に、git が画像を BINARY として扱うことを NUL ヒエウリック判定から**明示属性**に固定し、CRLF 変換による画像破損リスクを排除する。テキストファイル・改行・リポジトリ差分には影響しない安全な先行変更。

## 調査結果 / 変更内容

### 実測（実行前）
- 画像は git が実態では **BINARY** として扱っている（NUL ヒエウリック判定。CRLF 174 バイトを HEAD に保持）。破損リスクは現時点で低いが、判定がヒエウリック依存（脆弱）。
- `git ls-files --eol` は画像を `text`（`-text`）として表示（表示上の不一致・ misleading）。
- `core.autocrlf=true`（システム级）。テキストファイルは commit 時に CRLF→LF 変換・画像は保持。

### 変更内容
`.gitattributes`（リポジトリルート）に以下を追加（`* text=auto eol=lf` は追加しない・第2ステップ対象）:
```
*.avif   binary
*.png    binary
*.ico    binary
*.gif    binary
*.jpg    binary
*.jpeg   binary
*.webp   binary
*.bmp    binary
```
- 画像/バイナリ拡張子を**明示**に `binary` へ固定（ヒエウリック判定からの依存を解除）。
- テキストファイル・改行コード・既存画像 blob に影響なし（差分ゼロ）。

## Verification

- `git check-attr -a public/images/...avif|png|ico` → すべて `binary: set`（`text: unset`）
- `git check-attr -a README.md` → 空（未設定・正常）
- 制御実験（ヒエウリックでは text になる・NUL 無・CRLF 有の `.avif` テストファイル）を `git add` → **CRLF 15/15 保持・size 105 保持**（`.gitattributes` の binary がヒエウリックを上書きし BINARY として扱われること確認）
- 実画像コピー（NUL 有・CRLF=1）を `git add` → CRLF=1・size 58933 保持（破損なし）
- `git diff --stat` → 画像差分なし。変更は `.gitattributes`（新規）および docs 変更のみ
- 実行後リポジトリ clean（テストファイルは削除済み）


## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
