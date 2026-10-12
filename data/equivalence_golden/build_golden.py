"""リファクタリング等価性検証（L1 決定論的リプレイ A/B）のゴールデングルフィクスチャ生成スクリプト。

ライブ作業ツリーから `data/equivalence_golden/` を再構築する（冪等・再実行可）。

生成物:
- inputs/data/topics/latest.json        TTL改写 + tech 2 件 + TechCrunch RSS source 追加
- inputs/data/genre_scores/topics.json  実コピー
- inputs/data/character_features.json   実コピー
- inputs/data/rakuten_cache.json        dummy 商品を事前投入（23 hit + 2 意図的 miss）
- inputs/data/slug-redirects.json       {}
- inputs/posts/                         src/content/posts/*.md スナップショット
- inputs/prompts/                       scripts/prompts/* スナップショット
- fixtures/fixed_draft.txt              Gemini pass1 固定レスポンス（下書き）
- fixtures/fixed_refined.txt            Gemini pass2 固定レスポンス（精製文）
- fixtures/fake_now.json                固定時刻（FIXED_EPOCH）
- fixtures/seed.txt                     固定乱数 seed

使い方:
    python data/equivalence_golden/build_golden.py
"""
import json
import shutil
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = Path(__file__).resolve().parent

# 固定時刻: 2026-10-12T01:00:00Z = JST 2026-10-12T10:00:00
FIXED_EPOCH = 1791766800
NOW_MINUS_1H = "2026-10-12T09:00:00+09:00"
SEED = "20261012"

# tech カテゴリに追加するトピック（default バリアントで _auto_fetch_topics が発火しないよう 2 件）
TECH_ITEMS = [
    {
        "title": "Rust 1.90 が公開され新機能追加",
        "url": "https://www.rust-lang.org/blog",
        "score": 1,
        "source": "TechCrunch RSS",
        "category": "tech",
    },
    {
        "title": "Python の新機能が開発効率を向上",
        "url": "https://techcrunch.com/python",
        "score": 1,
        "source": "TechCrunch RSS",
        "category": "tech",
    },
]

# pokemon sources の fetched_at はそのまま古いまま（out-of-scope TTL 分岐を運動するため）
POKEMON_PREFIXES = ("Poké", "Poke", "Pokemon", "Pocket")

# --------------------------------------------------
# 楽天キャッシュ（読み取り専用共有入力）
# --------------------------------------------------
RAKUTEN_FETCHED_AT = "2026-10-11T00:00:00+00:00"  # 固定時刻より 1 日前（TTL 30 日以内）
RAKUTEN_HIT_KEYWORDS = [
    # Gemini 商品名（fixed_draft の product_recommendations）
    "Python 実践プログラミング 5版",
    "プログラマー 人間工学 座椅子",
    # 比較表内 <!-- AFF_PRODUCT: "AI 開発ツール" -->
    "AI 開発ツール",
    # 基底アフィリエイトキーワード（_improve_keyword 後）。非 kemono では 3 商品目で収集
    "Python 本",
    "AI 入門 書籍",
    # kemono カスケード: ケモノ + 全 world_tag（選ばれる world_setting に依存せずカバー）
    "ケモノ ファンタジー",
    "ケモノ 異世界",
    "ケモノ 現代",
    "ケモノ SF",
    "ケモノ スペースオペラ",
    "ケモノ 日常",
    "ケモノ サイバーパンク",
    "ケモノ 冒険",
    "ケモノ ダンジョンクライム",
    "ケモノ ミステリー",
    "ケモノ 歴史",
    # ケモノ + キャラ関係性（_KEMONO_RELATIONSHIP_AFFILIATE 全値）
    "ケモノ バディ",
    "ケモノ BL",
    "ケモノ 百合",
    "ケモノ 恋愛",
    # アンカーキーワード
    "ケモノ",
    "獣人",
    "動物",
]
# 意図的 miss（キャッシュに含めない）: 商品名の先頭句。
# 無クレデンシャル miss 分岐（警告 + None 返却・書込みなし）を運動するため。
RAKUTEN_INTENTIONAL_MISSES = ("Python", "プログラマー")


def _dummy_rakuten_entry(kw: str) -> dict:
    """dummy 商品エントリ。_rakuten_is_relevant の全分岐通過のため itemName にコアトークン「ケモノ」を含む。"""
    return {
        "fetched_at": RAKUTEN_FETCHED_AT,
        "product": {
            "itemName": f"{kw} テスト商品ケモノ",
            "itemPrice": 1980,
            "affiliateUrl": f"https://example.com/aff/{urllib.parse.quote(kw)}",
            "imageUrl": f"https://example.com/img/{urllib.parse.quote(kw)}.png",
            "reviewCount": 100,
        },
        "hits": 1,
    }


# --------------------------------------------------
# Gemini 固定レスポンス
# --------------------------------------------------
# pass1（下書き）: HTML comment プレースホルダーで事後処理全経路を運動。
# 「関連のおすすめアイテム」/「スポンサーリンク」は含めない（inject_affiliate_links guard 早期 return 回避）。
FIXED_DRAFT = '''---
title: "PythonとAIで開発効率を高める実践ガイド"
description: "PythonとAIツールで開発効率を高める実践ガイド。環境構築からAI支援コーディング、自動化スクリプト作成まで、よくある失敗とその解決策を段階的に解説します。"
author: "AI Writer"
tags: ["Python", "AI", "開発ツール"]
image_prompt: "a wolf anthro programmer at a desk with a laptop, blue eyes, white fur, modern office"
character_1: "ルナ（狼、青い目、白い毛皮）"
character_2: "レックス（狐、琥珀色の目、オレンジの毛皮）"
art_style: "anime style, illustration, cel shading"
product_recommendations:
  - name: "Python 実践プログラミング 5版"
    category: "書籍"
    price_range: "3,000円台"
  - name: "プログラマー 人間工学 座椅子"
    category: "グッズ"
    price_range: "20,000円台"
---

## はじめに

ソフトウェア開発において、Python と AI ツールの活用はますます重要になっています。[character_1] が、Python と AI を組み合わせて効率を高める実践的な手法を案内します。

<!-- IMAGE_PROMPT: "a wolf anthro programmer typing code on a laptop, focused expression, modern office background" -->

## 環境構築

Python 環境の構築は最初のステップです。[character_2] はバーチャル環境の利用を推奨します。

<!-- IMAGE_PROMPT: "a fox anthro developer setting up a terminal on a large monitor, code on screen, cozy room" -->

## AI 支援コーディング

AI ツールはコード補完やバグ検出に役立ちます。代表的なツールを比較しましょう。

| ツール | 強み |
|---|---|
| コード補完ツール | 高速 |
| バグ検出ツール | 高精度 |
| <!-- AFF_PRODUCT: "AI 開発ツール" --> | |

## 自動化スクリプト

Python で自動化スクリプトを書くと反復作業が減ります。Python の書籍を探しているなら<!-- AFFILIATE: "Python 書籍" | "定番 Python 書籍" -->がおすすめです。

## よくある質問

Q: どの Python バージョンを使うべきですか？
A: 最新の安定版を推奨します。

Q: 初心者向けの AI ツールはどれですか？
A: コード補完ツールから始めるのがおすすめです。

## まとめ

Python と AI ツールを組み合わせることで、開発効率を大きく高めることができます。
'''

# pass2（精製文）: 同一構造・同一プレースホルダーのまま本文表現を変化。
# draft != refined であることが「pass2 の結果が実際に流れる」ことを検出できる canary。
FIXED_REFINED = '''---
title: "PythonとAIで開発効率を高める実践ガイド"
description: "PythonとAIツールで開発効率を高める実践ガイド。環境構築からAI支援コーディング、自動化スクリプト作成まで、よくある失敗とその解決策を段階的に解説します。"
author: "AI Writer"
tags: ["Python", "AI", "開発ツール"]
image_prompt: "a wolf anthro programmer at a desk with a laptop, blue eyes, white fur, modern office"
character_1: "ルナ（狼、青い目、白い毛皮）"
character_2: "レックス（狐、琥珀色の目、オレンジの毛皮）"
art_style: "anime style, illustration, cel shading"
product_recommendations:
  - name: "Python 実践プログラミング 5版"
    category: "書籍"
    price_range: "3,000円台"
  - name: "プログラマー 人間工学 座椅子"
    category: "グッズ"
    price_range: "20,000円台"
---

## はじめに

Python と AI ツールの組み合わせは、現代のソフトウェア開発を大きく変えています。[character_1] が、効率化の実践テクニックを分かりやすく紹介します。

<!-- IMAGE_PROMPT: "a wolf anthro programmer typing code on a laptop, focused expression, modern office background" -->

## 環境構築

まず取り組むべきは Python 環境の整備です。[character_2] は、バーチャル環境でプロジェクトを隔離することをすすめています。

<!-- IMAGE_PROMPT: "a fox anthro developer setting up a terminal on a large monitor, code on screen, cozy room" -->

## AI 支援コーディング

AI ツールはコードの補完や不具合の発見を助けてくれます。主要なツールを比較してみましょう。

| ツール | 強み |
|---|---|
| コード補完ツール | 高速 |
| バグ検出ツール | 高精度 |
| <!-- AFF_PRODUCT: "AI 開発ツール" --> | |

## 自動化スクリプト

反復する作業を Python スクリプトに任せれば、手作業の負担は大きく減ります。Python の書籍を探しているなら<!-- AFFILIATE: "Python 書籍" | "定番 Python 書籍" -->がおすすめです。

## よくある質問

Q: どの Python バージョンを使うべきですか？
A: 最新の安定版を使うのが無難です。

Q: 初心者向けの AI ツールはどれですか？
A: コード補完ツールで慣れるのがおすすめです。

## まとめ

Python と AI ツールをうまく組み合わせることで、開発効率を大きく向上させることが可能です。
'''


# --------------------------------------------------
# 生成処理
# --------------------------------------------------
def _reset_golden_inputs():
    for sub in ("inputs", "fixtures"):
        p = GOLDEN / sub
        if p.exists():
            shutil.rmtree(p)
    (GOLDEN / "inputs" / "data").mkdir(parents=True)
    (GOLDEN / "inputs" / "posts").mkdir(parents=True)
    (GOLDEN / "inputs" / "prompts").mkdir(parents=True)
    (GOLDEN / "fixtures").mkdir(parents=True)


def build_topics_json(out_path: Path) -> dict:
    src = ROOT / "data" / "topics" / "latest.json"
    d = json.loads(src.read_text(encoding="utf-8"))

    # 1. fetched_at 改写（全局 + 対象カテゴリを持つ source）。pokemon 系はそのまま古い（out-of-scope 分岐運動）
    d["fetched_at"] = NOW_MINUS_1H
    for name, s in d.get("sources", {}).items():
        if name.startswith(POKEMON_PREFIXES):
            continue
        s["fetched_at"] = NOW_MINUS_1H

    # 2. TechCrunch RSS（tech 2 件）追加 → default バリアントの _auto_fetch_topics を抑制
    d["sources"]["TechCrunch RSS"] = {
        "topics": [dict(it) for it in TECH_ITEMS],
        "fetched_at": NOW_MINUS_1H,
    }
    d["by_category"]["tech"] = [dict(it) for it in TECH_ITEMS]
    d["all"] = [it for it in d.get("all", []) if it.get("category") != "tech"] + [dict(it) for it in TECH_ITEMS]
    d["total"] = len(d["all"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return d


def build_rakuten_cache(out_path: Path) -> dict:
    cache = {kw: _dummy_rakuten_entry(kw) for kw in RAKUTEN_HIT_KEYWORDS}
    for kw in RAKUTEN_INTENTIONAL_MISSES:
        assert kw not in cache
    out_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cache


def build_fixtures():
    (GOLDEN / "fixtures" / "fixed_draft.txt").write_text(FIXED_DRAFT, encoding="utf-8")
    (GOLDEN / "fixtures" / "fixed_refined.txt").write_text(FIXED_REFINED, encoding="utf-8")
    (GOLDEN / "fixtures" / "fake_now.json").write_text(
        json.dumps({"fixed_epoch": FIXED_EPOCH, "jst": "2026-10-12T10:00:00+09:00"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (GOLDEN / "fixtures" / "seed.txt").write_text(SEED + "\n", encoding="utf-8")


def build_copies():
    # genre_scores / character_features（実コピー）
    (GOLDEN / "inputs" / "data" / "genre_scores").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "data" / "genre_scores" / "topics.json", GOLDEN / "inputs" / "data" / "genre_scores" / "topics.json")
    shutil.copy2(ROOT / "data" / "character_features.json", GOLDEN / "inputs" / "data" / "character_features.json")

    # slug-redirects
    (GOLDEN / "inputs" / "data" / "slug-redirects.json").write_text("{}\n", encoding="utf-8")

    # posts / prompts スナップショット
    for f in sorted((ROOT / "src" / "content" / "posts").glob("*.md")):
        shutil.copy2(f, GOLDEN / "inputs" / "posts" / f.name)
    for f in sorted((ROOT / "scripts" / "prompts").iterdir()):
        if f.is_file():
            shutil.copy2(f, GOLDEN / "inputs" / "prompts" / f.name)


def _check_draft(name: str, text: str):
    import re
    desc = re.search(r'^description:\s*["\']?(.*?)["\']?\s*$', text, re.M)
    assert desc and 80 <= len(desc.group(1)) <= 120, f"{name}: description 長さ {desc and len(desc.group(1))}"
    assert text.count("<!-- IMAGE_PROMPT:") == 2, f"{name}: IMAGE_PROMPT 数"
    assert text.count('<!-- AFFILIATE:') == 1, f"{name}: AFFILIATE 数"
    assert text.count('<!-- AFF_PRODUCT:') == 1, f"{name}: AFF_PRODUCT 数"
    assert "[character_1]" in text and "[character_2]" in text, f"{name}: character プレースホルダー"
    assert "関連のおすすめアイテム" not in text and "スポンサーリンク" not in text, f"{name}: guard 文字列"
    assert "|---|" in text and "## よくある質問" in text and "Q:" in text, f"{name}: 表/FAQ"
    assert "product_recommendations:" in text, f"{name}: product_recommendations"


def verify():
    d = json.loads((GOLDEN / "inputs" / "data" / "topics" / "latest.json").read_text(encoding="utf-8"))
    bc = {k: len(v) for k, v in d["by_category"].items()}
    assert bc["tech"] == 2 and bc["kemono"] == 36 and bc["pokemon"] == 40, bc
    assert d["total"] == len(d["all"]) == 76, d["total"]
    assert len(d["sources"]) == 9, len(d["sources"])
    for name, s in d["sources"].items():
        assert len(s.get("topics", [])) > 0, f"0-topic source: {name}"
        if not name.startswith(POKEMON_PREFIXES):
            assert s["fetched_at"] == NOW_MINUS_1H, (name, s["fetched_at"])
    assert d["fetched_at"] == NOW_MINUS_1H

    cache = json.loads((GOLDEN / "inputs" / "data" / "rakuten_cache.json").read_text(encoding="utf-8"))
    assert len(cache) == len(RAKUTEN_HIT_KEYWORDS) == 23, len(cache)
    for kw in RAKUTEN_INTENTIONAL_MISSES:
        assert kw not in cache
    for kw, entry in cache.items():
        assert entry["product"]["itemName"].find("ケモノ") >= 0, kw

    posts = list((GOLDEN / "inputs" / "posts").glob("*.md"))
    assert len(posts) >= 50, len(posts)
    assert not any(p.name == "2026-10-12-100000-auto-post.md" for p in posts), "出力ファイル名衝突"
    prompts = list((GOLDEN / "inputs" / "prompts").iterdir())
    assert len(prompts) == 5, [p.name for p in prompts]

    _check_draft("fixed_draft", (GOLDEN / "fixtures" / "fixed_draft.txt").read_text(encoding="utf-8"))
    _check_draft("fixed_refined", (GOLDEN / "fixtures" / "fixed_refined.txt").read_text(encoding="utf-8"))
    draft = (GOLDEN / "fixtures" / "fixed_draft.txt").read_text(encoding="utf-8")
    refined = (GOLDEN / "fixtures" / "fixed_refined.txt").read_text(encoding="utf-8")
    assert draft != refined, "draft == refined（pass2 canary 失効）"

    fake = json.loads((GOLDEN / "fixtures" / "fake_now.json").read_text(encoding="utf-8"))
    assert fake["fixed_epoch"] == FIXED_EPOCH
    assert (GOLDEN / "fixtures" / "seed.txt").read_text(encoding="utf-8").strip() == SEED


def main():
    _reset_golden_inputs()
    build_topics_json(GOLDEN / "inputs" / "data" / "topics" / "latest.json")
    build_rakuten_cache(GOLDEN / "inputs" / "data" / "rakuten_cache.json")
    build_fixtures()
    build_copies()
    verify()
    n_posts = len(list((GOLDEN / "inputs" / "posts").glob("*.md")))
    total_kb = sum(f.stat().st_size for f in GOLDEN.rglob("*") if f.is_file()) // 1024
    print(f"OK: golden fixtures built at {GOLDEN}")
    print(f"   posts={n_posts} prompts=5 latest.json=76items sources=9 rakuten_cache=23hits+2misses total={total_kb}KB")


if __name__ == "__main__":
    main()
