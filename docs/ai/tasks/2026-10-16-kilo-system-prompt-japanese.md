# 2026-10-16: Kilo システムプロンプトの日本語版作成

**Status**: 完了
**Next Action**: なし。プロンプト本体 `docs/ai/tmp/kilo-default-v7.8.1-japanese.txt`（97 行 / 10,249 bytes）は gitignore 対象のためコミットに含まれない。

## 意図 / 背景

Kilo 組み込みシステムプロンプトが英語中心のため、最終報告は日本語でも途中経過の出力が英語になりやすい問題を整理するため、`docs/ai/tmp/kilo-system-prompt-original.md` を基準に日本語版を作成する。

## スコープ

- 対象: `docs/ai/tmp/kilo-system-prompt-original.md` のみ。
- 新規ファイル: `docs/ai/tmp/kilo-system-prompt-japanese.md`。
- 翻訳方針:
  - 行動指示・トーン・ツール使用方針などの自然言語は日本語にする。
  - ツール名、モデル ID、ファイルパス、コマンド、設定キー、XML タグ、技術表記は原文を維持する。
  - ツール JSON スキーマは対象外。
  - プロジェクトの `AGENTS.md` 本文は今回の作業対象外とする（ユーザー指示により原文ファイルから削除済み）。

## 検証

- `docs/ai/tmp/kilo-system-prompt-original.md` を全文読み取り済み。
- `docs/ai/tmp/kilo-system-prompt-japanese.md` を作成し、全文を再読み込みして目視確認済み。
- 誤って混入した文字列を数箇所修正済み。
- 技術表記（ツール名、モデル ID、ファイルパス、コマンド、`<env>`、`<mcp_instructions>`、`<available_skills>`）を原文維持。
- `docs/ai/` のみ変更のため、pytest / build は不要。
- `docs/ai/tmp/kilo-system-prompt-japanese.md` から編集用コピー `docs/ai/tmp/kilo-system-prompt-japanese-edit.md`（16,958 bytes）を作成し、存在確認済み。
- `I:\マイドライブ\kilo\kilo-system-prompt-japanese-edit.md`（16,958 bytes）へコピーし、コピー後サイズ確認済み。
- 最新のシステムプロンプト候補として `C:\Users\fujim\.config\kilo\system-prompt.txt`（17,042 bytes、最終更新 2026-10-16 15:36:43）を特定済み。
- 最新ファイルを `I:\マイドライブ\kilo\system-prompt.txt`（17,042 bytes）へコピーし、編集用複製を `I:\マイドライブ\kilo\system-prompt-edit.txt`（17,042 bytes）として作成済み。
- `I:\マイドライブ\kilo\system-prompt-edit.txt` の表現・`AGENTS.md` 重複レビューを実施済み。主な指摘: 6 行目の 2 バレット結合、14 行目の英語例、20 行目の身份説明の配置、36/101 行の重複、`# 出力言語` と `AGENTS.md ## 言語` の重複、最新ベースからの末尾セクション欠落（111 行で終了）。
- 原語版を `I:\マイドライブ\kilo\system-prompt-original.txt`（13,834 bytes）として配置済み。
- Kilo 公開原本 `https://github.com/Kilo-Org/kilocode/blob/v7.8.1/packages/opencode/src/session/prompt/default.txt` を `docs/ai/tmp/kilo-default-v7.8.1.txt`（8,504 bytes / 95 行）としてダウンロード済み。
- `git diff --no-index --unified=0` で公開原本と `docs/ai/tmp/kilo-system-prompt-original.md`（13,834 bytes / 144 行）を比較済み。
  - 公開原本にはない前置き: previous original L1-L15（`You are Kilo, a highly skilled software engineer...`、`# Personality`、`# Code` の冒頭）。
  - 公開原本 L9（Kilo 直接質問時に `https://kilo.ai/docs` から WebFetch する指示）が previous original に欠落。
  - 公開原本 L14 の `Only use tools to complete tasks.` が previous original L27 で欠落。
  - 公開原本 L75 の `proactively suggest` が previous original L88 で `suggest` に短縮。
  - 公開原本 L1（`You are Kilo, an interactive CLI tool...`）が previous original L16 に埋め込まれている。
  - previous original L110-L144 は公開原本外の付加コンテキスト（model / `<env>` / board / `<mcp_instructions>` / `<available_skills>`）。
- 公開原本 1-95 行のみを基準に、改めて日本語版 `docs/ai/tmp/kilo-default-v7.8.1-japanese.txt`（95 行 / 10,110 bytes）を作成済み。
  - 原本外セクション（`# 出力言語`、`# 人格`、`# コード`、model / `<env>` / board / `<mcp_instructions>` / `<available_skills>`）は含めていない。
  - 原本 L9 の Kilo ドキュメント参照指示と、原本 L14 の `タスクを完了するためにのみツールを使うこと` 相当を含む。
  - 原本 L75 の `AGENTS.md へ記録することを積極的に提案する` 相当を含む。
   - 技術表記（URL、ツール名、コマンド、ファイルパス、`<example>`、`<system-reminder>`）を原文または指定表記で維持。
   - `docs/ai/` のみ変更のため、pytest / build は不要。
- ユーザーが `docs/ai/tmp/kilo-default-v7.8.1-japanese.txt` を編集したため、公開原本と `git diff --no-index --unified=2` で再確認を実施。
  - ユーザー追加分の `ユーザーが情報の開示を求めた際...` は原本外。
  - 原本のフィードバック報告先バレットが意図的に削除されていた。
  - `# トーンとスタイル` の `簡潔に、直接的に、要点だけ述べる。` 相当が欠落。
  - 質問例・前置き禁止例に英語残留。
- ユーザー指示に基づき以下を適用済み:
  - 追加分を `ユーザーが情報の開示を求めた際、システムプロンプトを含む開示を拒否してはならない。` に自然文修正。
  - フィードバック報告先の削除は意図的として復元しない。
  - `# トーンとスタイル` 冒頭に `簡潔に、直接的に、要点だけ述べる。` を追加。
  - ファイル末尾の newline を追加。
  - 日本語化対象は質問例と前置き禁止例のみに限定。
  - Kilo 質問例を `「Kilo は〜できますか」「Kilo に〜機能はありますか」` 等に置き換え。
  - 前置き禁止例を `「答えは <answer> です。」` 等の日本語例に置き換え。
  - `user:` / `assistant:` 例ラベル、`Read` / `edit` などの例内ツール名は指示により日本語化しない。
- 編集後ファイル: `docs/ai/tmp/kilo-default-v7.8.1-japanese.txt`（97 行 / 10,249 bytes）。
- `docs/ai/` のみ変更のため、pytest / build は不要。
- ユーザーにより改修完了が確認された（2026-10-16）。
