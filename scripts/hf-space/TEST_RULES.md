# HF Space テストルール

## app.py 更新後の手順

### 1. HF Space にアップロード

```python
from huggingface_hub import HfApi
api = HfApi(token='HF_TOKEN')  # .env から取得
api.upload_file(
    path_or_fileobj=open('scripts/hf-space/app.py', 'rb'),
    path_in_repo='app.py',
    repo_id='blume/kemono-image-api',
    repo_type='space'
)
```

### 2. ビルドログ確認（必須）

アップロード後、Space が再起動されるまで待ち、起動ログに致命的なエラーがないか確認。

```python
import httpx

r = httpx.get(
    'https://huggingface.co/api/spaces/blume/kemono-image-api',
    headers={'Authorization': 'Bearer HF_TOKEN'},  # .env から取得
    timeout=10
)
data = r.json()
runtime = data.get('runtime', {})
print(f'Status: {runtime.get("stage")}')
```

- `stage` が `RUNNING` になるまで待つ（通常 1-3 分）
- ZeroGPU はエフェメラルインスタンスなので、各起動でチェックポイントを再ダウンロード
- 起動ログに `RuntimeError`、`NameError`、`ImportError` がないか確認
- Web UI にアクセスして、フォームが正常に表示されることを確認

### 3. テスト実行

ビルドに問題がない場合のみテストを実行。

**重要: ZeroGPU クォータ（3.5分/日）を最小限に使用する**
- ステップ数: **18 以下**（デフォルト 25 は超過リスク）
- 解像度: 512x512 でテスト（1152x768 は本番のみ）
- テスト回数は 1 回に限定（短プロンプトのみで十分）

#### テスト順序

1. **短プロンプト (~15トークン)**: 基本動作確認（steps=18, 512x512）← **これのみ必須**
2. **長プロンプト (~65トークン)**: chunking動作確認（クォータ余裕時のみ、通常不要）
3. **フル解像度 (1152x768)**: 本番環境での動作確認（本番生成時に確認）

**注意:** 短プロンプトテストが成功すれば、app.py の基本動作は確認済み。長プロンプトテストは不要（クォータ消費のみ）。

#### テスト方法

Web UI 経由でテスト（APIエンドポイントは ZeroGPU スリープ時に 404 を返すことがあるため）:

1. `https://blume-kemono-image-api.hf.space` にアクセス
2. Prompt にテスト文字列を入力
3. Steps を **18** に設定
4. Width/Height を設定（512x512 で快速テスト）
5. Submit をクリック
6. 画像が正常に生成されることを確認

#### テストプロンプト

**短プロンプト (~15トークン):**
```
masterpiece, best quality, furry, anthro, 1boy, wolf, kemono, standing in a forest
```

**長プロンプト (~65トークン):**
```
masterpiece, best quality, amazing quality, ultra-detailed, furry, anthro, 1boy, wolf, kemono, blue eyes, white fur, wearing a red jacket, standing in a beautiful forest with tall trees, sunlight filtering through the leaves, peaceful atmosphere, detailed background, a young wolf boy with a gentle smile, looking at the camera, wind blowing through his fur
```

**Negative Prompt（共通）:**
```
worst quality, low quality, bad quality, bad anatomy, bad hands, missing fingers, extra digits, cropped, deformed
```

#### 成功基準

- 画像が真っ黒でない（平均輝度が 0 に近い場合は失敗）
- 画像にキャラクターが描画されている
- コンソールログにエラーがない
- 生成時間が 90 秒以内（`@spaces.GPU(duration=90)` の制限）

### 4. テスト結果の記録

テスト結果を `docs/ai/tasks/2026-10-05-long-prompt-v2.md` に追記。

## 注意事項

- ZeroGPU は無料枠 3.5 分/日の制限がある
- `@spaces.GPU(duration=90)` で 1 リクエストあたり 90 秒予約
- 1 日約 2 リクエストのみ可能（クォータ超過でインスタンスが停止する）
- テスト後は不要な画像を削除する
- HF Space の API エンドポイントはスリープ時に 404 を返すことがある（Web UI 経由が安定）
