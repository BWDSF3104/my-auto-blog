# HF Space テストルール

## app.py 更新後の手順

### 1. HF Space にアップロード

```python
from huggingface_hub import HfApi
api = HfApi(token='HF_TOKEN')  # .env から取得
api.upload_file(
    path_or_fileobj=open('hf-space/app.py', 'rb'),
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
- テスト回数は 1 回に限定（長プロンプトのみで十分）

#### テスト順序

1. **長プロンプト (~65トークン)**: chunking動作確認（steps=18, 512x512）← **これのみ必須**

**注意:** 短プロンプトはchunking機能を使わないためテスト意味なし。長文プロンプトのみが修正箇所を実際に検証する。

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

#### テスト画像の保存（必須）

生成したテスト画像は必ず `docs/ai/tmp/` に保存する（例: `docs/ai/tmp/space-test-YYYY-MM-DD.png`）。

- **API テスト**（`gradio_client` 経由）: `predict()` が返す一時パスから必ず `PIL.Image.open(...).convert("RGB").save(out_path)` で保存し、保存後にファイルの存在とサイズ非ゼロを検証する（`os.path.getsize(out_path) > 0`）。検証に失敗した場合はテスト失敗とする。
  - **注意**: コードで `img.save()` を呼ばず、ログに「Saved to: ...」と print するだけの書き方はバグ（2026-10-17 に実在した。gradio 一時ファイルからの事後復旧に頼った）。保存はコード内で実行すること。
- **Web UI テスト**: 生成された画像を「画像を別の名前で保存」等で `docs/ai/tmp/` へ保存する。
- 理由: gradio 一時ファイル（`%TEMP%\gradio\...`）は永続化されず消去される可能性がある。保存しないと後から画像内容の検証（Groq 画像解析など）ができない。
- `docs/ai/tmp/` は 7 日経過エントリが自動削除されるため、手動で片付ける必要はない。

#### テスト画像の内容検証（必須）

保存した画像は、画像認識（MCP ツール `analyze_image_with_groq`）で**意図した内容になっているか**を確認し、結果をユーザーに報告する。

- プロンプトから意図される主要要素（キャラ種別・人数・目立つ特徴・シーン・安全/不適切要素の有無）が質問に列挙し、保存済み PNG の絶対パスを指定して呼び出す
- 使い方・焦点化分析の例: `docs/ai/image-analysis.md`
- **SDXL の仕様上、細部（色・形・表情など）の誤差は許容する**。主要要素の欠落（例: プロンプトに `1boy` なのに 2 人描画、指定種別と異なるキャラ、意図しない NSFW 要素）がある場合は「**失敗の可能性あり**」と判定し、**ユーザーへの報告にとどめる**（自動失敗とはしない）
- 細部記述のブレ（同一画像の複数回実行で瞳孔の色・形が異なる等）は既知の応答品質特性であり、それ単体で失敗としない（`docs/ai/image-analysis.md` 参照）
- Kilo 自身の作成による画像やプロジェクトフォルダ内の画像は、送信前の確認が不要（画像に機微・個人情報を含む場合は確認を取る）
- 検証結果（主要要素の合致状況・判定）をテスト結果の記録（`docs/ai/tasks/` の現行タスクファイル）に含める

#### 失敗判定

**確実な失敗は、完全に真っ黒・真っ白・ノイズのみなどのエラー画像の場合のみ**。主要要素の欠落は「失敗の可能性あり」としてユーザーに報告するにとどめる。

#### 成功基準

- エラー画像（完全に真っ黒・真っ白・ノイズのみなど）でない
- コンソールログにエラーがない
- 生成時間が 20 秒以内（`@spaces.GPU(duration=20)` の制限）
- **テスト画像が `docs/ai/tmp/` に保存済みである**
- **テスト画像の内容を検証しユーザーに報告済みである**（主要要素の欠落は「失敗の可能性あり」として報告。SDXL 仕様上の細部の誤差は許容）

### 4. テスト結果の記録

テスト結果を `docs/ai/tasks/` の現行タスクファイルに追記。

## 注意事項

- ZeroGPU は無料枠 3.5 分/日の制限がある
- `@spaces.GPU(duration=20)` で 1 リクエストあたり 20 秒予約
- 予約ベースで 1 日約 10 リクエスト（3.5 分 ÷ 20 秒）。実推論時間（初回 9 秒・ウォーム 2 秒）消費ベースでは約 101 リクエスト。詳細: `docs/ai/api-rate-limits.md`
- テスト後は不要な一時ファイルを削除する（`docs/ai/tmp/` に保存したテスト画像は残してよい。7 日で自動クリーンアップされる）
- HF Space の API エンドポイントはスリープ時に 404 を返すことがある（Web UI 経由が安定）
