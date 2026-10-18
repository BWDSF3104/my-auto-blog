"""GSC API（URL Inspection）で新規記事URLのインデックス登録を要求する。

Search Console API v1 の `urlInspection/index:inspect` を呼び出し、
Google に URL のインデックス状態を確認（再チェックを促す）させる。
scope は `webmasters`（API が正式に受け付ける read/write scope）。

CI 内で generate_article.py の後に実行される。
失敗してもデプロイをブロックしない（continue-on-error）。
"""
import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


SITE_URL = "https://bwdsf3104.github.io/my-auto-blog/"
API_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"


def load_credentials() -> service_account.Credentials:
    sa_json = os.environ.get("GSC_SA_JSON")
    if not sa_json:
        raise RuntimeError("GSC_SA_JSON env var is not set.")
    return service_account.Credentials.from_service_account_info(
        json.loads(sa_json),
        scopes=["https://www.googleapis.com/auth/webmasters"],
    )


def get_latest_urls(date_str: str) -> list[str]:
    """data/new_urls/{date}.txt からURLリストを読み取り。"""
    path = Path("data") / "new_urls" / f"{date_str}.txt"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def request_indexing(session: AuthorizedSession, url: str) -> bool:
    """AuthorizedSession で `index:inspect` を呼び出して URL のインデックス
    状態を確認（再チェックを促す）させる。

    トークンは AuthorizedSession が自動でリフレッシュ・付与するため、
    手動 refresh や Authorization ヘッダーは不要。
    """
    body = {
        "inspectionUrl": url,
        "siteUrl": SITE_URL,
    }
    resp = session.post(API_URL, json=body, timeout=30)
    if resp.status_code == 200:
        return True
    print(f"  [FAIL] {resp.status_code}: {resp.text[:200]}")
    return False


def main():
    import datetime

    jst = datetime.timezone(datetime.timedelta(hours=9))
    date_str = datetime.datetime.now(jst).strftime("%Y-%m-%d")

    urls = get_latest_urls(date_str)
    if not urls:
        print("ℹ️  本日URLファイルなし（記事未生成？）→ スキップ")
        return

    print(f"🔍 GSC インデックス要求: {len(urls)}件")
    creds = load_credentials()
    session = AuthorizedSession(creds)

    success = 0
    for url in urls:
        ok = request_indexing(session, url)
        if ok:
            success += 1
            print(f"  [OK] {url}")
        else:
            print(f"  [FAIL] {url}")

    print(f"📊 結果: {success}/{len(urls)} 成功")
    if success < len(urls):
        sys.exit(1)


if __name__ == "__main__":
    main()
