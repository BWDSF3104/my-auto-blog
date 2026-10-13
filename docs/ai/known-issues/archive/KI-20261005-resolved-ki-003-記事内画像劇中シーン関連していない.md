# KI-003: 記事内画像が劇中シーンと関連していない

**Date**: 2026-10-05
**Status**: 解決済

- 発見日: 2026-10-05
- 症状: 記事内に生成される挿絵画像が、周囲の本文のシーンと関連性が低い
- 影響範囲: 物語系記事（kemono_story）
- 根本原因: `compose_image_prompt()` が合成するプロンプトが SDXL の CLIP エンコーダー 77 トークン上限を超過（実測 78-155 トークン）、末尾の「シチュエーション」が破棄される
- 修正案: SDXL長プロンプトchunking実装 (2026-10-05 成功)。HF Space `app.py` に `get_long_prompt_embeddings_sdxl` 関数を追加。75トークン単位でチャンク分割 → 各チャンクをtext encoderに通す → embeddingを連結
- 詳細: `docs/ai/tasks/2026-10-05-long-prompt-v2.md`
