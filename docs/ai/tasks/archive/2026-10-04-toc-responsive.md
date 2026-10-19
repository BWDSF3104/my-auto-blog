# 目次 (TOC) のレスポンシブ対応 (2026-10-04)

**Status**: 完了

**Commit**: `fecc41a`

**Summary**:
- デスクトップ (lg+) は既存の `sticky` サイドバーを維持
- モバイルにアコーディオン型折りたたみTOCを追加
- トグルボタンには chevron SVG、`aria-expanded` 属性、JS トグルハンドラー実装
- `headings` 変数のスコープ問題を修正（条件ブロック外で宣言）

**Files Changed**:
- `src/layouts/PostLayout.astro`: モバイルTOCトグルボタン、`.toc-content` div、chevron SVG、JSハンドラー追加。`headings` 変数スコープ修正

**Verification**:
- `npm run build`: 成功 (108ページ)
