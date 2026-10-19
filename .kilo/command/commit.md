---
description: コミットとプッシュを実行（詳細はエージェントが判断）
---

commit と push を実行してください。

$ARGUMENTS

- コミットメッセージが指定されていればそれを使用。なければ変更ファイルから推論・作成
- コミット前チェック、remote 同期、commit → push、デプロイ検証などの詳細はエージェントが判断
- 手順・チェック項目は `docs/ai/workflows.md` を参照
