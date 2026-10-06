# GitHub ワークフロー実テスト計画

## 概要

最近8コミットで実装した機能変更を、実際のGitHub Actionsワークフロー (`deploy.yml`) でEnd-to-Endテストする。

**テスト対象コミット:**
- `66a3d9c` feat: 2-pass生成のメタデータ追跡機能追加
- `05aa10a` feat: 画像生成上限を3枚→8枚に増加
- `a350023` refactor: 記事内の全画像で同じseedを使用
- `e93b1d4` feat: 画像生成にseed制御を追加
- `fe6c833` perf: HF Space ZeroGPU予約を90→20秒に短縮、SchedulerをEuler aに変更
- `fbbb0ab` feat: Illustrious系推奨順序にプロンプト再配置
- `947009c` feat: 画像プロンプトの順序変更
- `d2686de` feat: e621 artistタグ集計+注入
- `bc9a1c7` feat: 画像プロンプト指示をDanbooruキーワード形式に統一
- `c8eb79e` feat: e621タグ注入を投稿別ランダム選出+フィルタ体系実装

---

## 確認項目

### 1. 2-pass生成の機能測定
- **確認方法**: 生成ログの「✨ 2-pass 精製中...」「✨ 精製完了」出力を確認
- **成功基準**: 精製パスが実行され、エラーなく完了
- **関連ファイル**: `generate_article.py:1269-1305`

### 2. 生成画像枚数の変更影響（3→8枚）
- **確認方法**: 生成された記事の `public/images/` 内の画像数をカウント
- **成功基準**: 最大8枚（ヘッダー1 + 本文内最大7枚）の画像が生成される
- **関連ファイル**: `generate_article.py:44` (`MAX_INLINE_IMAGES=7`), `kemono_story.txt`
- **注意**: AIが実際に8枚分のプロンプトを出力するかはプロンプト指示に依存

### 3. app.pyの変更影響（間接的）
- **確認方法**: ワークフローの画像生成ステップが正常に完了するか
- **変更点**:
  - Scheduler: DPM++ → EulerAncestralDiscreteScheduler
  - ZeroGPU予約待機: 90秒 → 20秒
  - seedパラメータ追加
  - 長プロンプトchunkingサポート
  - ネガティブプロンプトembeddingキャッシュ
- **成功基準**: 画像生成がエラーなく完了、画像品質が破綻していない

### 4. seed制御による画像スタイル一貫性
- **確認方法**: 同一記事内の画像を視覚比較
- **成功基準**: 同じseedベース（base, base+1, base+2...）で、色調・スタイルが一貫している
- **関連ファイル**: `generate_article.py`, `app.py:192-218`

### 5. draftsメタデータファイルの生成とコミット
- **確認方法**: `data/drafts/<timestamp>.json` が生成・コミットされるか
- **⚠️ 既知の問題**: ワークフローの `git add` に `data/drafts/` が含まれていない
- **対応**: テスト前に `deploy.yml` に `git add data/drafts/` を追加する必要がある
- **関連ファイル**: `generate_article.py:1481`, `deploy.yml:72-77`

### 6. プロンプトDanbooruキーワード形式
- **確認方法**: 生成記事内の `art_style` フロントマターと画像altテキストを確認
- **成功基準**: 自然言語ではなく、カンマ区切りキーワード形式
- **関連ファイル**: `kemono_story.txt`, `default.txt`, `ai_deep.txt`

### 7. e621 artistタグ注入
- **確認方法**: 生成記事の `art_style` に `by <artist名>` が含まれているか
- **成功基準**: artist名が注入されている（例: `by wolfy-nail`）
- **関連ファイル**: `generate_article.py`, `kemono_story.txt:34`

### 8. 各章ごとの画像配置
- **確認方法**: 生成記事内の `<!-- IMAGE_PROMPT -->` コメントの配置位置を確認
- **成功基準**: 各章（第1章、第2章、最終章）に1つずつ画像プロンプトが配置されている
- **関連ファイル**: `kemono_story.txt`

### 9. ワークフロー全体の実行時間
- **確認方法**: gh run の開始〜完了時間を計測
- **成功基準**: 前回の成功実行時間との比較。画像枚数増加 + 2pass で増加するか記録
- **基準値**: 直近の実行時間を記録しておく

---

## テスト実行手順

### ステップ0: テスト前の準備（ローカル）

1. 直近のワークフロー実行時間を記録
   ```
   gh run list --limit 5 --json name,status,createdAt
   ```

2. **deploy.yml に `data/drafts/` のコミットを追加**
   - `git add data/drafts/` を `git add data/trend_usage/` の後に追加
   - これをコミットしてpush

3. 最新の自動生成記事を削除（比較のためにクリーンな状態にする）
   - 直近の `2026-10-06-*.md` と関連画像を削除
   - コミットしてpush（またはローカルのみで削除）

### ステップ1: ワークフロー手動トリガー

```bash
gh workflow run deploy.yml
```

### ステップ2: 実行中モニタリング

```bash
gh run watch --log --job generate
```

- 標準出力から以下のログを確認:
  - `✨ 2-pass 精製中...` → 2-pass実行確認
  - `✨ 精製完了` → 2-pass完了確認
  - 画像生成の枚数とseed値
  - HF Spaceのレスポンス時間

### ステップ3: 生成結果の確認（ワークフロー完了後）

1. 最新コミットを確認
   ```bash
   git fetch origin
   git log --oneline origin/main -5
   ```

2. 最新記事をローカルに取得して確認
   ```bash
   git checkout origin/main -- src/content/posts/ public/images/ data/drafts/
   ```

3. 各確認項目の検証:
   - 画像枚数カウント
   - 記事内の画像プロンプト配置確認
   - drafts JSONファイルの内容確認
   - art_style フロントマターの確認
   - 画像の視覚比較（seed一貫性）

### ステップ4: 結果記録

- 各項目のPass/Failを記録
- 実行時間を記録
- 発見された問題を `known-issues.md` に記録
- 計画ファイルを完了としてマーク

---

## 注意事項

- **HF ZeroGPUの待機時間**: ワークフロー実行時にHF Spaceが冷えている場合、初回リクエストで最大数分の待機がかかる
- **レート制限**: 画像枚数が増えた分、HF Spaceへのリクエスト回数が増加。レート制限に注意
- **Gemini APIクォータ**: 2-passによりAPI呼び出し回数が2倍になっている
- **ワークフロー実行時間の増加**: 画像枚数増加 + 2pass + HF待時間で全体が遅くなる可能性がある
- **draftsファイルのサイズ**: 下書き+精製後の全文を保存するため、JSONファイルが大きい（数KB〜数十KB）

---

## 期待される影響のまとめ

| 変更 | 影響 | 許容範囲 |
|------|------|---------|
| 2-pass生成 | API呼び出し2倍、生成時間増加 | 全体3-5分増 |
| 画像3→8枚 | HFリクエスト増、保存時間増 | 全体5-10分増 |
| seed制御 | 影響なし（パラメータ追加のみ） | なし |
| Scheduler変更 | 画像品質の変化 | 品質低下なし |
| ZeroGPU20秒 | 待機時間の短縮 | 成功率維持 |
| drafts保存 | ディスク使用量増 | 無視可能 |
