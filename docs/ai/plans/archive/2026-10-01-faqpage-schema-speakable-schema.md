# FAQPage schema + Speakable schema

**Date**: 2026-10-01
**Status**: 完了

記事本文からQ&Aパターンを抽出してFAQPage JSON-LDを自動生成（行単位ステートマシンパーサー）。記事冒頭段落をSpeakable JSON-LDとして出力。`generate_article.py` に `_extract_faq_pairs()` と `_extract_speakable_text()` を追加し、frontmatter にJSON文字列で記録。`PostLayout.astro` で条件付きJSON-LD出力。テスト134件全件通過、ビルド成功 (90ページ)

---
*以下は 2026-10-13 に plans.md からアーカイブ*
