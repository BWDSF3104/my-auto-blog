import httpx
import json
import time

# Test with short prompt (~15 tokens)
prompt_short = 'masterpiece, best quality, furry, anthro, 1boy, wolf, kemono, standing in a forest'
neg = 'worst quality, low quality, bad quality, bad anatomy, bad hands, missing fingers, extra digits, cropped, deformed'

# Test with long prompt (~65 tokens)
prompt_long = ('masterpiece, best quality, amazing quality, ultra-detailed, furry, anthro, 1boy, wolf, kemono, '
    'blue eyes, white fur, wearing a red jacket, standing in a beautiful forest with tall trees, '
    'sunlight filtering through the leaves, peaceful atmosphere, detailed background, '
    'a young wolf boy with a gentle smile, looking at the camera, wind blowing through his fur')

def test_prompt(name, prompt, width=512, height=512):
    print(f'=== {name} ===')
    start = time.time()
    try:
        r = httpx.post(
            'https://blume-kemono-image-api.hf.space/run/predict',
            json={
                'data': [
                    prompt,
                    neg,
                    25,
                    5.0,
                    width,
                    height,
                ]
            },
            timeout=120
        )
        elapsed = time.time() - start
        print(f'Status: {r.status_code}, Time: {elapsed:.1f}s')
        if r.status_code == 200:
            data = r.json()
            path = data['data'][0]
            print(f'Output: {path[:80]}...')
            return True
        else:
            print(f'Error: {r.text[:200]}')
            return False
    except Exception as e:
        elapsed = time.time() - start
        print(f'Exception after {elapsed:.1f}s: {e}')
        return False

# Run tests
results = []
results.append(('short', test_prompt('短プロンプト (~15トークン)', prompt_short)))
time.sleep(2)
results.append(('long', test_prompt('長プロンプト (~65トークン)', prompt_long)))
time.sleep(2)
results.append(('full_res', test_prompt('フル解像度 (1152x768)', prompt_long, 1152, 768)))

print('\n=== 結果 ===')
for name, ok in results:
    status = '成功' if ok else '失敗'
    print(f'{name}: {status}')
