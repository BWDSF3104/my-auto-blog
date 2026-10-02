# Memory Bank archive files の作成

**Status:** 完了
**Date:** 2026-10-02
**Commit:** 37538c4, 87c3af9

## Objective

`docs/ai/` の Memory Bank ファイルが膨張したため、完了したエントリを `-archive.md` ファイルへ分離してファイルサイズを削減。

## Summary

1. AGENTS.md のドキュメントルールを更新（全タスク対象、アーカイブファイルの構造と閾値を定義）
2. `known-issues-archive.md` 作成（解決済問題を移動）
3. `plans-archive.md` 作成（古い完了計画を移動）
4. `decisions-archive.md` 作成（古い決定を移動）
5. `current-task-archive.md` 作成（古い完了タスクを移動）

## Verification

- pytest: 134 passed in 2.09s
- npm run build: 92 pages in 3.83s
