# cp932 Console Encoding Fix

**Date**: 2026-10-02

**Decision**: Change `_safe_print()` to use `.encode("cp932", errors="replace")` instead of `.encode("utf-8", errors="replace")` for Windows console output.

**Reason**: Windows console uses cp932 encoding by default. Non-ASCII characters (e.g., "PokéCommunity") caused `UnicodeEncodeError` when printed to the console.

**Rejected Alternatives**:
- UTF-8 を維持: Windows コンソールで引き続きエラーが発生
- `chcp 65001` で UTF-8 に切り替え: 環境ごとに設定が必要で信頼性低い

**Impact**:
- `fetch_topics.py`: `_safe_print()` のエンコーディングを cp932 に変更
