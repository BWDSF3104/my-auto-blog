import os
import httpx
import time

hf_token = os.environ.get("HF_TOKEN", "")
headers = {}
if hf_token:
    headers['Authorization'] = f'Bearer {hf_token}'

# Get logs
r = httpx.get(
    'https://huggingface.co/api/spaces/blume/kemono-image-api/logs',
    headers=headers,
    timeout=30
)
print(f'Status: {r.status_code}')
logs = r.text
print(f'Log length: {len(logs)} chars')

# Check for errors
error_keywords = ['RuntimeError', 'NameError', 'ImportError', 'SyntaxError', 'Traceback', 'Error']
for keyword in error_keywords:
    if keyword in logs:
        # Find the line with the error
        for line in logs.split('\n'):
            if keyword in line:
                print(f'[{keyword}] {line[:200]}')

# Show last 50 lines
lines = logs.split('\n')
print('\n=== Last 50 lines ===')
for line in lines[-50:]:
    print(line)
