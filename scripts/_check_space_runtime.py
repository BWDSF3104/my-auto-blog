import os
import httpx
import json

hf_token = os.environ.get("HF_TOKEN", "")
headers = {}
if hf_token:
    headers['Authorization'] = f'Bearer {hf_token}'

r = httpx.get(
    'https://huggingface.co/api/spaces/blume/kemono-image-api',
    headers=headers,
    timeout=10
)
data = r.json()
runtime = data.get('runtime', {})
print(json.dumps(runtime, indent=2))
