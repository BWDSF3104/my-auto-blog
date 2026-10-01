import os, re
d = "src/content/posts"
for f in sorted(os.listdir(d)):
    if not f.endswith(".md"):
        continue
    content = open(os.path.join(d, f), encoding="utf-8").read()
    m = re.search(r'^description:\s*["\']?(.*?)(?<!\\)["\']?\s*$', content, re.M)
    if m:
        desc = m.group(1).strip()
        flag = " <-- SHORT" if len(desc) < 80 else ""
        print(f"{f}: {len(desc)} chars{flag}")
