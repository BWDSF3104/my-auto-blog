# Giscus コメントバックエンドは外部専用リポジトリに分離

**Date**: 2026-10-26
**Related**: `decisions/2026-10-11-giscus-comments.md`（Giscus 採用）
**Task**: `tasks/2026-10-26-giscus-comments-external-repo.md`

**Decision**: Giscus（クライアントサイド widget）自体は維持するが、その **Discussions バックエンドはブログリポジトリ（`BWDSF3104/my-auto-blog`）ではなく、新規の**「コメント用専用 GitHub リポジトリ」**（公開）を指定する。**リポジトリ名: `BWDSF3104/giscus-comments`**（2026-10-26 ユーザー選択）。

**Reason**:
- 分離: ブロックソース（本リポ）とコメント保存（コメントリポ）を独立管理できる。
- 将来の**複数サイト共用**: 別サイトも同一コメントリポを `data-repo` で参照可能（共有 pool の前提）。
- コメントリポは軽量（コード・CI なし。Discussions + giscus app のみ）。

**制約 / 前提**:
- コメントリポは **公開** 必須（Giscus 要求）。
- コメントリポは **ファイル非依存**（コード・CI・必須ファイルなし。**ローカルクローンは不要**）。コメント本体は GitHub Discussions 上。
- 4 環境変数（`PUBLIC_GISCUS_*`）は**ブログリポ**の GitHub Actions Repository Variables に登録（build 作業がブログリポの CI だから）。
- コメントリポの削除・リネーム → コメント**失われ（復元不可）**。
- slug リネーム → 別 Discussion（コメント非継承）は本設計でも維持。
