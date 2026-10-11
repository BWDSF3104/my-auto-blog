# 2026-10-11: README を Astro スターター既定からプロジェクト説明へ書き換え

**Status**: 完了 (2026-10-11)

## 概要

ユーザー要望: README が Astro Starter Kit: Basics の既定内容のままなので、本プロジェクトの使用技術・生成フローを詳しく説明したものに書き換える。個人名や API キーなど公開すべきでないものが含まれないよう注意すること。
追加指示: HuggingFace の具体的なリポジトリ名（Space ID・モデルリポジトリ ID）は公開情報でも README に載せない。

## 変更内容

`README.md` 全面書き換え（Astro スターター既定 46 行 → 231 行、日本語）:

- **特徴**: 毎日自動生成（JST 8:00）・トレンド連動・ジャンルスコアリング・2-pass 生成・AI 画像生成・アフィリエイト統合・SEO 最適化
- **生成フロー**: 6 ステップ図（GitHub Actions → ①トレンド収集 → ②ジャンル採点 → ③記事・画像生成 → ④コミット → ⑤ビルド → ⑥デプロイ）+ `generate_article.py` の 11 ステップ詳細（被り防止・世界設定決定・プロンプト構築・Pass1/Pass2・画像生成・アフィリエイト注入・内部リンク/slug・frontmatter 検証・生成情報セクション・保存/ログ）
- **技術スタック表**: Astro 7 / Tailwind CSS 4 / Python 3.10+ / Gemini API / Cloudflare Workers AI（Clef-flash）/ SDXL（自社 HF Space / ZeroGPU）→ Pollinations.ai（Flux）/ 楽天 Web Service API / GitHub Actions / GitHub Pages / pytest
- **データソース表**: アクティブソース + 一時無効化ソース（Reddit 403 / Bluesky 501）
- **環境変数表**: 変数名・用途・必須のみの記載（キー値は記載しない）
- **プロジェクト構造ツリー / ローカル開発手順 / CI/CD ワークフロー表（deploy・deploy-only・genre-score）/ テスト規則 / 注意事項**

## 機微情報排除（確認済み）

- API キー値: 一切なし（環境変数は変数名のみ）
- 個人名: なし
- GitHub ユーザー名: Pages の URL をユーザー名なしで「ベースパス `/my-auto-blog/`」のみと表記
- HuggingFace リポジトリ名（Space ID・モデルリポジトリ ID）: ユーザー指示どおり除外。「自社ホストの HuggingFace Space（ZeroGPU、SDXL パイプライン）」と一般表現
- Cloudflare アカウント ID / Google サイト検証コード: 除外
- 検証: `.env` のキー値断片と既知識別子（HF Space ID / モデル ID / ユーザー名等）を正規表現で全文スキャン → 該当なし

## Verification

- コード変更なし（`README.md` のみ）→ AGENTS.md 規則により pytest / `npm run build` 不要
- エンコーディング: BOM なし（先頭バイト `23 20 6D 79` = `# my`）、UTF-8

## Next Action

- なし
