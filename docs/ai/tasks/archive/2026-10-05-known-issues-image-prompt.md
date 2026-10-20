# タスク: 既知問題の記録 + 画像プロンプト調査

開始日: 2026-10-05
Status: 進行中

## 内容

1. ハンバーガーメニューの記事一覧リンクが反応しない問題を `known-issues.md` に記録
2. ヒーローセクションの最新記事ボタンが記事一覧以外では動作しない問題を `known-issues.md` に記録
3. 記事内画像のプロンプト生成手順を調査
4. HuggingFace API の使用可能状況を `backlog.md` に記録

## Next Action

- [x] known-issues.md に2件の問題を追加 (KI-001, KI-002)
- [x] backlog.md に HuggingFace API 確認を追加 (P1)
- [x] 画像プロンプト生成の手順を調査 (scripts/generate_article.py)
- [x] 調査結果を known-issues.md に記録 (KI-001, KI-002, KI-003)
- [ ] KI-001, KI-002 のコード修正
- [ ] KI-003 のプロンプトテンプレート強化

## 調査結果

### KI-001: ハンバーガーメニュー記事一覧リンク
- 原因: `href="#main-content"` が `page/[page].astro` で機能しない（id 属性なし）
- 修正: `href={baseUrl}` に変更

### KI-002: ヒーローセクション最新記事ボタン
- 原因: KI-001と同様 + ヘッダーが全ページ共通のため
- 修正: `href={baseUrl}` に変更 + `page/[page].astro` に `id="main-content"` を追加

### KI-003: 画像プロンプトの関連性
- フロー: Gemini が `<!-- IMAGE_PROMPT: "..." -->` を生成 → `compose_image_prompt()` でキャラ定義等を合成 → HF Space に送信
- 問題: Gemini のプロンプトが簡略的・一般的になりがち
- 修正: `kemono_story.txt` の指示を強化

## Verification

(未開始)
