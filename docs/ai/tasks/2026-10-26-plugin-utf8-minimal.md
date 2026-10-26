# powershell-utf8.js プラグイン最小化実装

**Status**: 完了
**Date**: 2026-10-26
**Next Action**: 実装完了。新セッション（VS Code 再起動後）で pwsh 7 シェル・新プラグインの動作を確認
**Related**: `2026-10-26-pwsh7-plugin-design`（設計・pwsh 7 導入）

## 意図 / 背景

ユーザー指示: 「実装開始、完了後vscode再起動バッチ実行」。前段階設計（`2026-10-26-pwsh7-plugin-design`）の承認済み方針どおり、Kilo シェルが pwsh 7 化された以上、`C:\Users\fujim\.config\kilo\plugin\powershell-utf8.js` のコマンド注入（コンソール設定 + `$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'`）は不要で、プラグインを **`shell.env`（Python 用 `PYTHONIOENCODING`/`PYTHONUTF8`）のみ** へ最小化する。バックアップは同タスクで取得済み（`.2026-10-26.bak`）。

## 調査結果 / 変更内容

### 変更: `C:\Users\fujim\.config\kilo\plugin\powershell-utf8.js` 書き換え

**削除**（`tool.execute.before` フック全域）:
- `[Console]::InputEncoding/[OutputEncoding]/$OutputEncoding` 注入（Kilo 内蔵層 `@opencode-ai/core/kilocode/powershell` + pwsh 7 既定 utf8NoBOM でカバー）
- `$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'` 注入（pwsh 7 の Get-Content 既定が utf8NoBOM）
- `PLUGIN_MARKER` 定数・再挿入ガード・ps1 構文保護チェック（フック消滅）

**保持**:
- `shell.env`: `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`（Python 3.10.8 現行、PEP 686 未導入のため pytest/ad-hoc python の cp932 フォールバック対策。Python 3.15 移行後に不要化）

```js
const PowerShellUtf8 = async () => {
  return {
    "shell.env": async (_input, output) => {
      if (process.platform !== "win32") return;
      output.env.PYTHONIOENCODING = "utf-8";
      output.env.PYTHONUTF8 = "1";
    },
  };
};

export default {
  id: "powershell-utf8",
  server: PowerShellUtf8,
};
```

### 発見（タスク外）: 2026-10-26 判定

- `2026-10-26-giscus-external-repo`（828400e）で Giscus 外部リポジトリ化。`.env` に Giscus 公開変数 4 件追加。
- `.env.public`（2026-10-23 方針でトラッキング公開値）は未作成。
- `.env` は **公開 Giscus 変数 4 件のみ**（シークレットは削除済み）。
- 詳細: `docs/ai/known-issues/KI-20261026-01-local-gemini-key-missing.md`

## Verification

- **プラグイン書き換え**: `C:\Users\fujim\.config\kilo\plugin\powershell-utf8.js` を上記最小構成に更新。バックアップ `powershell-utf8.js.2026-10-26.bak`（変更前状態）取得済み。
- **pytest**: 実鍵 `.env` が欠落のため、`generate_article.py` の入口環境変数チェックで**収集失敗**（テスト実行前の import 時）。テストは全件モック（実 Gemini 呼出禁止・AGENTS.md ルール）のため、**dummy key（`local-test-dummy`）で実行** → **454 passed (8.36s)**。
- **maintenance テスト**: `pytest maintenance/tests/ -v` → **53 passed (3.84s)**。
- **npm run build**: `163 page(s) built in 4.77s` 成功。
- **kilo-safe-remove.cmd / safe-rmdir.cmd スモーク**: テスト用ファイル・ディレクトリを `docs\ai\tmp\` で削除 → ゴミ箱へ移動成功（`Test-Path` False）。5.1 経路不変確認。
- **pwsh 7 確認**: 新 Kilo セッションでは `which("pwsh")` で pwsh 7.6.9 が選択される（既存検証: pwsh 本体 Get-Content utf8NoBOM 確認済み）。

### 備考

- 本タスクはプラグインファイル変更のみ（Python・Astro 源なし）。
- 現行セッション（5.1）はプラグイン読み込み前・変更前状態が有効。新セッション（VS Code 再起動後）から pwsh 7 + 新プラグイン。
- VS Code 再起動バッチ: 実行済みだが WM_CLOSE 一部失敗 → ユーザーが手動再起動（自動再起動失敗は `known-issues/KI-20261026-02-vscode-restart-wmclose-failure.md` に記録）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [ ] `known-issues/` ファイルの archive 移動（本タスクで解決した KI あり）
- [ ] `backlog.md` の完了項目を削除（該当なし）
