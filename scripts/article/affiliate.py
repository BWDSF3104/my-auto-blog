"""アフィリエイトリンク・楽天API・商品カード処理モジュール。

generate_article.py から分離（Phase 4）。
- 本文内・比較表内アフィリエイトプレースホルダーの置換
- 楽天API商品検索（30日キャッシュ・レート制限・429リトライ）
- アフィリエイトリンク自動挿入
- product_recommendations パーサーと商品カードHTML生成
"""
import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import requests

from article.config import *  # noqa: F401,F403
from article.meta import _save_affiliate_link_log


# --------------------------------------------------
# 本文内アフィリエイトプレースホルダーの置換
# --------------------------------------------------
def process_inline_affiliates(content: str) -> str:
    """
    本文内の <!-- AFFILIATE: "keyword" | "anchor" --> を検出し、
    anchorテキストのみ（プレーンテキスト）で置換する。
    商品カードが唯一のリンク表示となるため、本文内はテキストのみ残す。
    """
    matches = list(INLINE_AFFILIATE_PATTERN.finditer(content))
    if not matches:
        return content

    print(f"🔗 本文内アフィリエイトプレースホルダーを {len(matches)} 箇所検出（プレーンテキスト化）")

    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        keyword = match.group(1).strip()
        anchor = match.group(2).strip()

        # プレーンテキストで置換（商品カードが唯一のリンク表示）
        replacement = anchor
        content = content.replace(full_tag, replacement, 1)
        print(f"   🔗 インラインアフィリエイト {idx}: 「{anchor}」→ {keyword}（プレーンテキスト化）")

    # 連続する過剰な改行を整理
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


# --------------------------------------------------
# 比較表内の商品リンクプレースホルダーの置換
# --------------------------------------------------
def process_inline_products(content: str) -> str:
    """
    比較表内の <!-- AFF_PRODUCT: "keyword" --> を検出し、
    Amazon・楽天の検索リンクボタンに置換する。
    さらに楽天APIで商品検索し、比較表の直後に商品画像カードを追加する。
    """
    matches = list(INLINE_AFF_PRODUCT_PATTERN.finditer(content))
    if not matches:
        return content

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")

    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "post"
    utm_content = urllib.parse.quote(title[:50])

    type_match = re.search(r'^prompt_type:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    prompt_type = type_match.group(1).strip() if type_match else "default"

    print(f"🛒 比較表内商品プレースホルダーを {len(matches)} 箇所検出")

    keywords: list[str] = []
    for idx, match in enumerate(matches, start=1):
        full_tag = match.group(0)
        keyword = match.group(1).strip()
        encoded_kw = urllib.parse.quote(keyword)

        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        # 比較表内に埋め込むコンパクトなリンク形式
        replacement = f"[Amazon]({amazon_url}) | [楽天]({rakuten_url})"
        content = content.replace(full_tag, replacement, 1)
        print(f"   🛒 商品リンク {idx}: {keyword}")
        keywords.append(keyword)

    # 楽天API商品カードの追加（比較表の直後に挿入）
    cards_html = ""
    seen_kw: set[str] = set()
    for kw in keywords:
        if kw in seen_kw:
            continue
        seen_kw.add(kw)
        if _is_affiliate_bad_keyword(kw):
            continue
        product = _rakuten_search(kw)
        if product and _rakuten_is_relevant(product.get("itemName", ""), kw, prompt_type):
            cards_html += _generate_rakuten_card(product, kw, title)
        elif product:
            print(f"   🛒 [filter] {kw} → 関連性不足、カードをスキップ: {product.get('itemName', '')[:40]}")

    if cards_html:
        # テーブルの最終行を特定し、その直後にカードを挿入
        card_div_open = '<div class="product-card">'
        first_amazon_marker = "amazon.co.jp/s?k="
        end_line = _find_table_end_line(content, first_amazon_marker)
        if end_line is not None:
            lines = content.split('\n')
            lines.insert(end_line + 1, f"\n<div class=\"product-cards\">{cards_html}\n</div>")
            content = '\n'.join(lines)
            card_count = cards_html.count(card_div_open)
            print(f"   🖼️ 楽天API商品カードを {card_count} 枚追加（比較表の直後）")

    return content


# --------------------------------------------------
# アフィリエイトリンク自動挿入
# --------------------------------------------------


def _is_affiliate_bad_keyword(kw: str) -> bool:
    """アフィリエイト検索に適さないキーワードを判定"""
    kw_lower = kw.lower().strip()
    if len(kw_lower) < 2:
        return True
    for prefix in _AFFILIATE_BAD_PREFIXES:
        if kw_lower.startswith(prefix):
            return True
    # 半角英数字のみで構成され、かつスペースを含む場合は検索不适
    if re.match(r'^[a-zA-Z0-9\s]+$', kw) and kw.count(' ') > 3:
        return True
    return False


def _improve_keyword(kw: str, prompt_type: str) -> str:
    """
    キーワードを購買意欲の高い検索語に改善する。
    技術系は「入門書」「本」などを付与、物語系は関連グッズに転換。
    """
    kw_lower = kw.lower().strip()

    # 辞書で直接マッチする場合は改善語を使用
    for key, improved in _KEYWORD_ENHANCEMENT.items():
        if key in kw_lower:
            return improved

    # prompt_type に応じてサフィックスを付与
    if prompt_type in ("default",):
        # 技術記事: 書籍・グッズを検索
        if re.match(r'^[a-zA-Z]+$', kw):
            return f"{kw} 書籍"
        return f"{kw} 関連グッズ"
    elif prompt_type in ("kemono_story", "novel", "story"):
        # 物語系: キーワードをそのまま使用（作品名のみで検索すれば商品がヒットする）
        return kw

    return kw


def _extract_article_body(content: str) -> str:
    """Frontmatter を除去した記事本文を返す。"""
    m = re.search(r'^---\s*\n.*?\n---\s*\n?', content, re.DOTALL)
    if m:
        return content[m.end():]
    return content


def _is_github_repo_name(keyword: str) -> bool:
    """
    GitHubリポジトリ名（技術識別子）の判定。
    単一の英単語、キャメルケース、ハイフン区切り、または「/」を含むパターンを除外対象とする。
    """
    kw = keyword.strip()
    if not kw:
        return False
    # スラッシュを含む場合はowner/repo形式
    if "/" in kw:
        return True
    # 英字・数字・ハイフン・アンダースコアのみで構成され、日本語文字を含まない
    if re.match(r'^[a-zA-Z0-9_\-]+$', kw) and not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', kw):
        return True
    return False


# --------------------------------------------------
# 楽天市場API 商品検索
# --------------------------------------------------
_rakuten_last_call_time: float = 0.0


def _rakuten_load_cache() -> dict:
    if not os.path.exists(RAKUTEN_CACHE_FILE):
        return {}
    try:
        with open(RAKUTEN_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _rakuten_save_cache(cache: dict):
    os.makedirs(os.path.dirname(RAKUTEN_CACHE_FILE), exist_ok=True)
    now = datetime.now(timezone.utc)
    ttl = timedelta(days=RAKUTEN_CACHE_TTL_DAYS)
    cleaned = {}
    for kw, entry in cache.items():
        try:
            fetched_at = datetime.fromisoformat(entry["fetched_at"])
            if now - fetched_at < ttl:
                cleaned[kw] = entry
        except (KeyError, ValueError):
            continue
    with open(RAKUTEN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)


def _rakuten_search(keyword: str) -> dict | None:
    """
    楽天市場APIで商品を検索し、画像付きの先頭商品を返す。
    30日キャッシュ・429リトライ・呼び出し間隔1.5秒。
    戻り値: {"itemName", "itemPrice", "affiliateUrl", "imageUrl", "reviewCount"} | None
    """
    global _rakuten_last_call_time

    cache = _rakuten_load_cache()
    if keyword in cache:
        entry = cache[keyword]
        try:
            fetched_at = datetime.fromisoformat(entry["fetched_at"])
            if datetime.now(timezone.utc) - fetched_at < timedelta(days=RAKUTEN_CACHE_TTL_DAYS):
                product = entry.get("product")
                if product:
                    print(f"   🛒 [cache] {keyword} → {product['itemName']}")
                else:
                    print(f"   🛒 [cache] {keyword} → 商品なし（キャッシュ）")
                return product
        except (KeyError, ValueError):
            pass

    app_id = os.environ.get("RAKUTEN_APPLICATION_ID", "")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
    if not app_id or not access_key:
        print(f"   ⚠️ 楽天APIクレデンシャル未設定: 「{keyword}」をスキップ")
        return None

    elapsed = time.time() - _rakuten_last_call_time
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)

    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "affiliateId": affiliate_id,
        "keyword": keyword,
        "hits": 3,
        "sort": "-reviewCount",
        "format": "json",
        "formatVersion": "2",
    }
    headers = {"Origin": RAKUTEN_ORIGIN, "Referer": RAKUTEN_REFERER}

    max_retries = 3
    for attempt in range(max_retries):
        _rakuten_last_call_time = time.time()
        try:
            resp = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = 2 * (attempt + 1)
                print(f"   ⏳ 楽天API 429: {wait}秒待機 ({attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            items = data.get("Items", [])

            product = None
            for item in items:
                images = item.get("mediumImageUrls") or []
                if images and images[0]:
                    product = {
                        "itemName": item.get("itemName", ""),
                        "itemPrice": item.get("itemPrice", 0),
                        "affiliateUrl": item.get("affiliateUrl") or item.get("itemUrl", ""),
                        "imageUrl": images[0],
                        "reviewCount": item.get("reviewCount", 0),
                    }
                    break

            cache[keyword] = {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "product": product,
                "hits": len(items),
            }
            _rakuten_save_cache(cache)

            if product:
                print(f"   🛒 [rakuten] {keyword} → {product['itemName']} (¥{product['itemPrice']:,})")
            else:
                print(f"   🛒 [rakuten] {keyword} → 画像付き商品なし（{len(items)}件）")
            return product

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 * (attempt + 1)
                print(f"   ⚠️ 楽天APIエラー: {e} — {wait}秒待機 ({attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"   ❌ 楽天API失敗: 「{keyword}」— {e}")
                return None

    return None


def _generate_rakuten_card(product: dict, keyword: str, title: str) -> str:
    """楽天API商品から商品カードHTMLを生成（既存 .product-card 体系に統合）"""
    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    encoded_kw = urllib.parse.quote(keyword)
    utm_content = urllib.parse.quote(title[:50])
    amazon_url = (
        f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
        f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
    )
    price = product.get("itemPrice", 0)
    price_html = f'<div class="pc-price">¥{price:,}</div>' if price else ""
    name = product.get("itemName", "")
    img = product.get("imageUrl", "")
    afl = product.get("affiliateUrl", "")
    return f"""
<div class="product-card">
  <img class="pc-img" src="{img}" alt="{name}" loading="lazy" />
  <div class="pc-info">
    <div class="pc-name">{name}</div>
    <div class="pc-category">{keyword}</div>
    {price_html}
  </div>
  <div class="pc-links">
    <a href="{amazon_url}" target="_blank" rel="noopener noreferrer nofollow" class="pc-btn pc-btn-amazon">Amazon</a>
    <a href="{afl}" target="_blank" rel="noopener noreferrer nofollow sponsored" class="pc-btn pc-btn-rakuten">楽天</a>
  </div>
</div>"""


def _find_table_end_line(content: str, marker: str) -> int | None:
    """markerを含むmarkdownテーブルの最終行の行番号（0始まり）を返す"""
    lines = content.split('\n')
    marker_idx = None
    for i, line in enumerate(lines):
        if marker in line:
            marker_idx = i
            break
    if marker_idx is None:
        return None
    end_idx = marker_idx
    while end_idx + 1 < len(lines) and lines[end_idx + 1].strip().startswith('|'):
        end_idx += 1
    return end_idx


def _extract_article_keywords(content: str, max_kw: int = 2, prompt_type: str = "default") -> list[str]:
    """
    記事本文（Frontmatter後のテキスト）からテーマキーワードを抽出。
    1. Frontmatterのtagsを優先使用
    2. 本文の先頭 paragraphs から日本語のキーワード候補を抽出
    """
    body = _extract_article_body(content)
    keywords: list[str] = []
    seen = set()

    # 1. tags から抽出
    tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
    if tags_match:
        for t in tags_match.group(1).split(','):
            tag = t.strip().strip('"\'')
            if tag and len(tag) >= 2 and tag not in seen:
                # 日本語フィルタ（一旦無効化: SF/TF/BL等の英字タグも通す）
                # if prompt_type in ("kemono_story", "novel", "story"):
                #     if not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', tag):
                #         continue
                seen.add(tag)
                keywords.append(tag)
                if len(keywords) >= max_kw:
                    return keywords

    # 2. 本文の先頭2段落から日本語のキーワード候補を抽出
    paragraphs = re.split(r'\n\s*\n', body.strip())
    jp_chunks: list[str] = []
    for para in paragraphs[:2]:
        # マークダウン記号を除去
        para = re.sub(r'[#*\-\[]>`]', '', para)
        # 日本語の単語候補を抽出（2文字以上の連続日本語文字列）
        matches = re.findall(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]{2,}', para)
        for m in matches:
            if m not in seen and len(m) >= 2:
                seen.add(m)
                jp_chunks.append(m)

    # 先頭からキーワードを補充
    for kw in jp_chunks:
        if len(keywords) >= max_kw:
            break
        keywords.append(kw)

    return keywords


def _kemono_affiliate_keywords(kemono_params: dict) -> list[str]:
    """kemono_story のスクリプト決定パラメータからアフィリエイト検索キーワードを生成。

    生成順:
    1. ケモノ単体
    2. ジャンル単体（world_tags）
    3. キャラ関係性単体
    4. ケモノ + ジャンル
    5. ケモノ + キャラ関係性
    """
    kws: list[str] = []

    # 1. ケモノ単体
    kws.append("ケモノ")

    # 2. ジャンル（world_tags）を単体使用
    genres = list(kemono_params["world_tags"])
    for g in genres:
        kws.append(g)

    # 3. キャラ関係性単体
    rel_key = kemono_params.get("relationship_key", "")
    relationship = _KEMONO_RELATIONSHIP_AFFILIATE.get(rel_key, "")
    if relationship:
        kws.append(relationship)

    # 4. ケモノ + ジャンル
    for g in genres:
        kws.append(f"ケモノ {g}")

    # 5. ケモノ + キャラ関係性
    if relationship:
        kws.append(f"ケモノ {relationship}")

    # 重複排除（順序維持）
    seen: set[str] = set()
    result: list[str] = []
    for kw in kws:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def _rakuten_is_relevant(item_name: str, keyword: str, prompt_type: str) -> bool:
    """楽天検索結果の関連性を判定する。

    - kemono_story の汎用キーワード（ケモノ/獣人/動物/ケモノ＋ジャンル/関係性）:
      商品名にコアトークンを1つ以上含むこと
    - その他（Gemini商品名・tech系）:
      検索キーワードの実語トークン（2文字以上）が商品名に1つ以上含まれること
    """
    name = item_name.lower()
    is_kemono_generic = (
        prompt_type == "kemono_story"
        and (keyword in _KEMONO_ANCHOR_KEYWORDS or keyword.startswith("ケモノ "))
    )
    if is_kemono_generic:
        return any(tok in name for tok in _KEMONO_CORE_TOKENS)
    tokens = [t for t in keyword.split() if len(t) >= 2]
    if not tokens:
        return True
    return any(t.lower() in name for t in tokens)


def _rakuten_first_phrase(name: str) -> str:
    """Gemini生成商品名から先頭句を抽出する。

    スペースと区切り語（用的/向け/用/的）で分割し先頭セグメントを採用する。
    平仮名1文字（の/に/へ/と/や）は「にゃんこ」の「に」「けもの」の「の」のように
    単語内で使われるため、区切り語に含めない。
    先頭セグメントが2文字未満なら2番目のセグメントを連結する。
    区切りがどこにも無く商品名そのまま（1語）になる場合は、
    既に検索済みの商品名と重複するため空文字を返す（スキップ）。
    """
    name = name.strip()
    if not name:
        return ""
    segments = [s for s in re.split(r'\s+|' + _RAKUTEN_PHRASE_DELIMITERS, name) if s]
    if len(segments) < 2:
        return ""
    phrase = segments[0]
    if len(phrase) < 2:
        phrase = f"{phrase} {segments[1]}"
    if phrase == name:
        return ""
    return phrase


def _rakuten_api_keywords(
    gemini_products: list[str] | None,
    base_keywords: list[str],
    prompt_type: str,
    kemono_params: dict | None,
) -> list[str]:
    """楽天API検索キーワードリスト（カスケード順序）を構築する。

    kemono_story:
      Gemini商品名 → 先頭句 → ケモノ+ジャンル → ケモノ+関係性 → ケモノ → 獣人 → 動物
    その他:
      Gemini商品名 → 先頭句 → 基底キーワード（既存の改善キーワード）

    ジャンル単体語・関係性単体語はAPIに送らない（検索リンクのみ）。
    英語のみのキーワードも送らない（楽天では0ヒット）。
    """
    kws: list[str] = []
    for name in gemini_products or []:
        name = name.strip()
        if not name or _is_affiliate_bad_keyword(name):
            continue
        if not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', name):
            continue
        kws.append(name)
        phrase = _rakuten_first_phrase(name)
        if phrase and phrase != name and not _is_affiliate_bad_keyword(phrase):
            kws.append(phrase)

    if prompt_type == "kemono_story" and kemono_params:
        for g in kemono_params.get("world_tags", []):
            kws.append(f"ケモノ {g}")
        rel = _KEMONO_RELATIONSHIP_AFFILIATE.get((kemono_params or {}).get("relationship_key", ""), "")
        if rel:
            kws.append(f"ケモノ {rel}")
        kws.extend(_KEMONO_ANCHOR_KEYWORDS)
    else:
        kws.extend(base_keywords)

    # 重複排除（順序維持）
    seen: set[str] = set()
    result: list[str] = []
    for kw in kws:
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def _rakuten_collect(keywords: list[str], prompt_type: str, max_products: int = 3) -> list[tuple[str, dict]]:
    """カスケード順序で楽天を順次検索し、関連性フィルタ通過した最大 max_products 商品を収集する。

    max_products 到達で即停止。同一商品（affiliateUrl）は重複排除する。
    戻り値: (keyword, product) タプルのリスト。
    """
    collected: list[tuple[str, dict]] = []
    seen_urls: set[str] = set()
    for kw in keywords:
        if len(collected) >= max_products:
            break
        product = _rakuten_search(kw)
        if not product:
            continue
        if not _rakuten_is_relevant(product.get("itemName", ""), kw, prompt_type):
            print(f"   🛒 [filter] {kw} → 関連性不足、スキップ: {product.get('itemName', '')[:40]}")
            continue
        url = product.get("affiliateUrl", "")
        if url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        collected.append((kw, product))
    return collected


def _fallback_keyword_from_tags_title(content: str) -> str | None:
    """frontmatter の tags 先頭、なければ title の先頭語からフォールバックキーワードを抽出する。"""
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""

    tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
    keyword = None
    if tags_match:
        tag_items = [t.strip().strip('"\'') for t in tags_match.group(1).split(',') if t.strip()]
        if tag_items:
            keyword = tag_items[0]

    if not keyword:
        cleaned = re.sub(r'[【】「」『』\[\]()（）\s]', ' ', title).strip()
        words = [w for w in cleaned.split() if len(w) > 1]
        keyword = words[0] if words else None

    return keyword


def _append_trend_keywords(
    keywords_to_use: list[str],
    keyword_sources: list[str],
    trend_keywords: list[str] | None,
    prompt_type: str,
) -> None:
    """trend_keywords で最大3件まで補充する（GitHubリポジトリ名・重複・悪質キーワードは除外）。"""
    if not trend_keywords or len(keywords_to_use) >= 3:
        return
    seen = set(k.replace(" 書籍", "").replace(" 関連グッズ", "").replace(" 関連作品", "") for k in keywords_to_use)
    for kw in trend_keywords:
        kw_clean = kw.strip()
        if _is_github_repo_name(kw_clean):
            continue
        if _is_affiliate_bad_keyword(kw_clean):
            continue
        if kw_clean in seen:
            continue
        seen.add(kw_clean)
        improved = _improve_keyword(kw_clean, prompt_type)
        keywords_to_use.append(improved)
        keyword_sources.append("trend")
        if len(keywords_to_use) >= 3:
            break


def _resolve_affiliate_keywords(
    content: str,
    prompt_type: str,
    script_keywords: list[str] | None,
    trend_keywords: list[str] | None,
) -> tuple[list[str], list[str]]:
    """
    アフィリエイト検索キーワードを優先順位で解決する。
    1. script_keywords（スクリプトが直接生成したキーワード。ストーリー系）
    2. 記事本文からの抽出 → trend_keywords で補充（GitHubリポジトリ名は除外）
    3. tags / title のフォールバック → 最終フォールバック
    戻り値: (keywords, keyword_sources)
    """
    keywords_to_use: list[str] = []
    keyword_sources: list[str] = []

    # 1. スクリプトが直接生成したキーワード（最優先）
    if script_keywords:
        for kw in script_keywords:
            if not _is_affiliate_bad_keyword(kw):
                keywords_to_use.append(kw)
                keyword_sources.append("script")
    else:
        # フォールバック: 記事本文からテーマキーワードを抽出
        article_kw = _extract_article_keywords(content, max_kw=2, prompt_type=prompt_type)
        for kw in article_kw:
            if _is_affiliate_bad_keyword(kw):
                continue
            improved = _improve_keyword(kw, prompt_type)
            keywords_to_use.append(improved)
            keyword_sources.append("article_extract")

    # 2. trend_keywords を補充（GitHubリポジトリ名は除外）
    _append_trend_keywords(keywords_to_use, keyword_sources, trend_keywords, prompt_type)

    # 3. 全て空の場合は tags / title 抽出にフォールバック
    if not keywords_to_use:
        keyword = _fallback_keyword_from_tags_title(content)
        if keyword:
            keywords_to_use = [_improve_keyword(keyword, prompt_type)]
            keyword_sources = ["fallback_tags_title"]
        else:
            # 最終フォールバック
            if prompt_type in ("kemono_story", "novel", "story"):
                keywords_to_use = ["ライトノベル おすすめ"]
            else:
                keywords_to_use = ["プログラミング 入門書"]
            keyword_sources = ["fallback_default"]

    return keywords_to_use, keyword_sources


def _build_search_link_rows(
    keywords_to_use: list[str],
    keyword_sources: list[str],
    amazon_tag: str,
    rakuten_id: str,
    utm_content: str,
) -> tuple[str, list[dict]]:
    """キーワードごとの Amazon / 楽天検索リンクを product-card 系行 HTML とリンクログエントリで組立する。
    キーワードごとに 1 行（商品名欄にキーワード + 検索ボタン 2 つ）とし、
    先頭キーワードは 🔥 で強調する（旧メイン CTA カード廃止・キーワード重複排除）。"""
    rows_html = ""
    link_log_entries: list[dict] = []
    for i, kw in enumerate(keywords_to_use):
        encoded_kw = urllib.parse.quote(kw)

        # Amazon: 検索リンク + UTM
        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        # Rakuten: 検索リンク
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        mark = "🔥 " if i == 0 else ""
        rows_html += f"""
<div class="product-card">
  <div class="pc-info">
    <div class="pc-name">{mark}「{kw}」</div>
    <div class="pc-category">Amazon / 楽天市場で検索</div>
  </div>
  <div class="pc-links">
    <a href="{amazon_url}" target="_blank" rel="noopener noreferrer nofollow sponsored" class="pc-btn pc-btn-amazon">Amazon</a>
    <a href="{rakuten_url}" target="_blank" rel="noopener noreferrer nofollow sponsored" class="pc-btn pc-btn-rakuten">楽天</a>
  </div>
</div>"""
        link_log_entries.append({
            "keyword": kw,
            "source": keyword_sources[i] if i < len(keyword_sources) else "unknown",
            "amazon_url": amazon_url,
            "rakuten_url": rakuten_url,
        })
    return rows_html, link_log_entries


def _build_rakuten_cards_section(
    gemini_products: list[str] | None,
    keywords_to_use: list[str],
    prompt_type: str,
    kemono_params: dict | None,
    title_for_card: str,
) -> str:
    """楽天API商品カードを組立する（末尾セクションの検索リンク行の上に追加）。
    カスケード検索: キーワードを優先順位順に辿り、関連性フィルタ通過した最大3商品を収集。
    ラッパー（.product-cards）なしの生カード HTML を返す（組立は呼び出し側）。"""
    api_keywords = _rakuten_api_keywords(gemini_products, keywords_to_use, prompt_type, kemono_params)
    collected = _rakuten_collect(api_keywords, prompt_type, max_products=3)
    rakuten_cards_html = "".join(
        _generate_rakuten_card(product, kw, title_for_card) for kw, product in collected
    )
    if rakuten_cards_html:
        card_div_open = '<div class="product-card">'
        card_count = rakuten_cards_html.count(card_div_open)
        print(f"   🖼️ 楽天API商品カードを末尾セクションに {card_count} 枚追加")
    return rakuten_cards_html


def inject_affiliate_links(content: str, trend_keywords: list[str] = None, script_keywords: list[str] = None, file_timestamp: str = None, gemini_products: list[str] = None, kemono_params: dict = None) -> str:
    """
    記事末尾にAmazon・楽天のアフィリエイト検索リンクブロックを自動挿入する。

    キーワード優先順位:
    1. script_keywords（スクリプトが直接生成したキーワード。ストーリー系）
    2. trend_keywords（GitHubリポジトリ名は除外）
    3. tags / title のフォールバック

    改善点:
    - スクリプト決定パラメータからキーワード生成（ストーリー系）
    - UTM パラメータによるトラッキング
    - 複数のプラットフォーム対応
    - 楽天商品カード + キーワード検索リンクを product-card 系に統一
      （旧インラインスタイルのメイン CTA カードは廃止、キーワード重複排除）
    - タグ由来の検索リンク行は ENABLE_TAG_AFFILIATE でトグル（デフォルトOFF。
      OFF時は楽天APIカードのみ維持、カードも無ければセクション全体をスキップ）
    """
    if "関連のおすすめアイテム" in content or "スポンサーリンク" in content:
        return content

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")

    # prompt_type を取得（キーワード改善用）
    type_match = re.search(r'^prompt_type:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    prompt_type = type_match.group(1).strip() if type_match else "default"

    keywords_to_use, keyword_sources = _resolve_affiliate_keywords(
        content, prompt_type, script_keywords, trend_keywords
    )

    # UTM トラッキングパラメータ
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    utm_content = urllib.parse.quote((title_match.group(1).strip() if title_match else "post")[:50])

    # トグル: ENABLE_TAG_AFFILIATE（デフォルトOFF）。OFF時はタグ由来の検索リンク行を生成しない
    if ENABLE_TAG_AFFILIATE:
        search_rows_html, link_log_entries = _build_search_link_rows(
            keywords_to_use, keyword_sources, amazon_tag, rakuten_id, utm_content
        )
    else:
        search_rows_html, link_log_entries = "", []
    rakuten_cards_html = _build_rakuten_cards_section(
        gemini_products, keywords_to_use, prompt_type, kemono_params,
        title_match.group(1).strip() if title_match else "post",
    )
    cards_inner = (rakuten_cards_html + search_rows_html).strip()
    if not cards_inner:
        # 楽天APIカードも無い場合は末尾セクション全体をスキップ（空見出しの回避）
        print("   🔗 タグ由来検索リンク無効かつ楽天APIカードなし → 末尾アフィリエイトセクションをスキップ")
        return content
    cards_html = f"\n<div class=\"product-cards\">{cards_inner}\n</div>"

    affiliate_section = f"""

---

### 📚 テーマ関連のおすすめアイテム・書籍
この記事のテーマに関連する作品や人気アイテムをチェック！{cards_html}

<small style="color: #64748b;">※ 当サイトはアフィリエイト広告（Amazonアソシエイト・楽天アフィリエイト等）を利用して収益を得ています。</small>
"""

    # リンク生成ログの保存
    if file_timestamp:
        title_match_log = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
        article_title = title_match_log.group(1).strip() if title_match_log else ""
        _save_affiliate_link_log(file_timestamp, prompt_type, article_title, link_log_entries)

    return content.strip() + "\n" + affiliate_section


def _extract_affiliate_keyword(title: str) -> str | None:
    """
    トレンドタイトルからアフィリエイト検索用のキーワードを1つ抽出する。
    購買意欲のある検索語になるよう、固有名詞・製品名・技術名を優先。
    品質フィルタは inject_affiliate_links 側で実施するため、ここでは粗抽出。
    """
    # e621 などのタイトルは除外
    if title.startswith("e621"):
        return None
    # GitHub リポジトリ形式 "owner/repo: description" → repo名側を抽出
    if ":" in title:
        before_colon = title.split(":", 1)[0].strip()
        after_colon = title.split(":", 1)[1].strip()
        # "owner/repo" 形式の場合、repo名を抽出
        if "/" in before_colon:
            parts = before_colon.split("/")
            repo_name = parts[-1].strip()
            # repo名が意味のある名前（2-20文字）の場合使用
            if 2 <= len(repo_name) <= 20:
                return repo_name
        # 説明側が長すぎる場合は短縮
        if after_colon and len(after_colon) > 0:
            title = after_colon
    # 長すぎる場合は主要語を抽出
    if len(title) > 50:
        words = title.split()
        # 固有名詞候補（大文字始まり）を優先
        capitalized = [w for w in words if w[0].isupper() if len(w) > 1]
        if capitalized:
            title = " ".join(capitalized[:3])
        else:
            title = " ".join(words[:4])
    # 意味のあるキーワードか判定（2文字以上）
    cleaned = re.sub(r'[^\w\s\u3000-\u9fff]', ' ', title).strip()
    if len(cleaned) < 2:
        return None
    return cleaned[:30]


# --------------------------------------------------
# product_recommendations パーサー
# --------------------------------------------------
def extract_product_recommendations(content: str) -> list[dict]:
    """
    Frontmatter から product_recommendations YAML ブロックを抽出・パースする。
    例:
      product_recommendations:
        - name: "商品名"
          category: "書籍"
          price_range: "1000円台"
    """
    block_match = re.search(
        r'^product_recommendations:\s*\n((?:\s*-\s+.*\n?)+)',
        content,
        re.MULTILINE,
    )
    if not block_match:
        return []

    block = block_match.group(1)
    products = []
    current = {}
    for line in block.splitlines():
        item_match = re.match(r'^\s+-\s+name:\s*["\']?(.*?)["\']?\s*$', line)
        if item_match:
            if current:
                products.append(current)
            current = {"name": item_match.group(1).strip()}
            continue
        cat_match = re.match(r'^\s+category:\s*["\']?(.*?)["\']?\s*$', line)
        if cat_match and current:
            current["category"] = cat_match.group(1).strip()
            continue
        price_match = re.match(r'^\s+price_range:\s*["\']?(.*?)["\']?\s*$', line)
        if price_match and current:
            current["price_range"] = price_match.group(1).strip()
            continue

    if current and "name" in current:
        products.append(current)

    return products


# --------------------------------------------------
# 商品カード HTML 生成
# --------------------------------------------------
def generate_product_cards(products: list[dict], title: str) -> str:
    """
    商品リストから商品カード風のHTMLブロックを生成。
    各カードは商品名・価格帯・Amazon/楽天検索リンクを含む（スリム: 絵文字・カテゴリ行なし）。
    """
    if not products:
        return ""

    amazon_tag = os.environ.get("AMAZON_TRACKING_ID", "your-amazon-tag-22")
    rakuten_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "your-rakuten-id")
    utm_content = urllib.parse.quote(title[:50])

    cards_html = ""
    for prod in products:
        name = prod.get("name", "").strip()
        if not name:
            continue

        price = prod.get("price_range", "")
        encoded_kw = urllib.parse.quote(name)

        amazon_url = (
            f"https://www.amazon.co.jp/s?k={encoded_kw}&tag={amazon_tag}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )
        rakuten_url = (
            f"https://search.rakuten.co.jp/search/mall/{encoded_kw}/?scid={rakuten_id}"
            f"&utm_source=autoblog&utm_medium=affiliate&utm_content={utm_content}"
        )

        price_html = ""
        if price:
            price_html = f'<div class="pc-price">{price}</div>'

        cards_html += f"""
<div class="product-card">
  <div class="pc-info">
    <div class="pc-name">{name}</div>
    {price_html}
  </div>
  <div class="pc-links">
    <a href="{amazon_url}" target="_blank" rel="noopener noreferrer nofollow" class="pc-btn pc-btn-amazon">Amazon</a>
    <a href="{rakuten_url}" target="_blank" rel="noopener noreferrer nofollow" class="pc-btn pc-btn-rakuten">楽天</a>
  </div>
</div>"""

    return f'\n<div class="product-cards">\n{cards_html}\n</div>\n'


def process_product_cards(content: str) -> str:
    """
    Frontmatter の product_recommendations をパースし、記事末尾に
    商品カードHTMLブロックを挿入する（アフィリエイトセクションの手前）。
    """
    products = extract_product_recommendations(content)
    if not products:
        return content

    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "post"

    cards_html = generate_product_cards(products, title)
    if not cards_html:
        return content

    print(f"🛍️ 商品カードを {len(products)} 件生成")

    # product_recommendations ブロックを Frontmatter から完全に削除
    # 改訂: インデントされた継続行をすべてキャッチ（[-:] 制限を撤廃）
    content = re.sub(
        r'^product_recommendations:\s*\n(?:[ \t].*\n?)*',
        '',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # アフィリエイトセクションの手前に挿入
    aff_marker = "### 📚 テーマ関連のおすすめアイテム"
    if aff_marker in content:
        content = content.replace(
            aff_marker,
            cards_html + "\n\n" + aff_marker,
        )
    else:
        # アフィリエイトセクションがない場合は記事末尾に追加
        content = content.strip() + "\n\n" + cards_html

    return content
