# GitHub ワークフロー実テスト 汎用手順書

## 目的

機能変更後に、実際のGitHub ActionsワークフローでEnd-to-Endテストを実施する標準手順。

---

## 前提条件

- `gh` CLIがインストールされログイン済み
- ローカルリポジトリが最新の状態（`git pull` 済み）
- テスト対象の変更がローカルでpytest/build検証済み

---

## ステップ1: テスト計画の作成

`docs/ai/tasks/YYYY-MM-DD-github-workflow-test-plan.md` にテスト計画を作成。

**必須記載事項:**
- テスト対象コミットのリスト
- 確認項目（変更内容ごとに1項目ずつ）
- 各項目の確認方法・成功基準・関連ファイル
- 注意事項（レート制限、APIクォータ、外部サービス依存等）

---

## ステップ2: 基準値の記録

直近の成功したワークフロー実行時間を記録。

```bash
gh run list --limit 5 --json name,status,conclusion,createdAt,event
```

記録する情報:
- 直近成功runのID
- 全体所要時間
- 各jobの所要時間

---

## ステップ3: ワークフローの手動トリガー

```bash
gh workflow run "Auto Generate Content and Deploy to GitHub Pages"
```

実行後、返されたrun IDを記録する。

---

## ステップ4: 実行中の監視

cronタスクで定期的にステータス確認。

```bash
# ステータス確認
gh run view <RUN_ID> --json status,conclusion,jobs

# 詳細なjob情報取得
gh run view <RUN_ID> --json jobs
```

**監視間隔:** 約3分ごと（ワークフローの完了目安は5-10分）

---

## ステップ5: 完了・失敗の確認

### 成功時

```bash
git stash
git pull --rebase
git stash pop
```

ローカルに最新の変更を取得後、ステップ6に進む。

### 失敗時

```bash
# job IDの確認
gh run view <RUN_ID> --json jobs

# 失敗したjobのログ取得
gh run view <RUN_ID> --log --job <JOB_ID> 2>&1 | Select-String -Pattern "error|Error|failed" -Context 5
```

**失敗箇所に応じた対応:**

deploy-onlyワークフローは「記事と画像が既にコミット済み」の状態からビルド・デプロイを実行する。そのため、切り替えの可否は失敗箇所による。

| 失敗箇所 | deploy-only切り替え | 対応 |
|---------|-------------------|------|
| generate job | ❌ 不可 | 修正→コミット→push→フルワークフローで再実施 |
| build-and-deploy job | ✅ 可（generate jobは成功済み） | 修正→コミット→push→deploy-onlyで再実施 |

**deploy-onlyの切り替え条件:**
- generate jobがsuccessで完了していること（記事・画像がリモートにコミット済み）
- build-and-deploy jobで失敗した場合にのみ適用可能

```bash
gh workflow run "Deploy Only (no article generation)"
```

---

## ステップ6: 指定された試験の実施

テスト計画に記載した試験項目を順番に実施。

各試験項目に対して:
- 計画に記載した確認方法に従って検証を実行
- 成功基準と比較してPass/Failを判定
- 関連ファイルの内容を確認

---

## ステップ7: 結果記録

`test-results/YYYY-MM-DD-github-workflow-test.md` にテスト結果を記録。

**必須記載事項:**
- テスト概要（日付、対象コミット、使用ワークフロー）
- 各確認項目のPass/Failと根拠
- ワークフロー実行時間の測定値
- 失敗した場合のタイムラインと原因
- 発見された問題と対応
- 総括表

---

## 注意事項

- **外部サービスの待機時間**: 外部APIが冷えている場合、初回リクエストで待機がかかる
- **レート制限**: リクエスト回数が増加する変更には注意
- **APIクォータ**: API呼び出し回数の増加を確認
- **ワークフロー実行時間**: 変更内容に応じて実行時間が変動する
