"""
重複フロントマターキーの修復に関する回帰テスト。

2026-11-19 の障害の再発防止: 2 キャラクター分のスタイル定義が両方とも
`semi-anthro:` キーで出力されたが、重複キー修復のキー検出パターンが
ハイフンを含まず `semi-anthro` をキーとして認識できなかったため修復が
素通りし、ビルド側 (generate-search-index.js) が duplicated mapping key
で失敗した。
"""

import yaml

from article.frontmatter import _fix_duplicate_yaml_keys, validate_and_fix_frontmatter

VAL1 = "semi-anthro, 1boy, blue wolf, golden eyes, white chest fur, red scarf"
VAL2 = "semi-anthro, 1boy, blue wolf, golden eyes, white chest fur, blue neckerchief"

BROKEN_FM = (
    "\n"
    'title: "鏡像のオルフェウス"\n'
    'slug: "kyouzou-no-orpheus"\n'
    f'semi-anthro: "{VAL1}"\n'
    f'semi-anthro: "{VAL2}"\n'
)


def test_duplicate_hyphenated_key_renamed_to_characters():
    """ハイフン付きキーの重複が character_1 / character_2 にリネームされる"""
    fixed = _fix_duplicate_yaml_keys(BROKEN_FM)
    data = yaml.safe_load(fixed)
    assert data["character_1"] == VAL1
    assert data["character_2"] == VAL2
    assert "semi-anthro" not in data


def test_normal_frontmatter_unchanged():
    """正常なフロントマターは変更されない"""
    fm = (
        "\n"
        'title: "テスト"\n'
        'slug: "test"\n'
        'character_1: "semi-anthro, 1boy, wolf"\n'
        'character_2: "semi-anthro, 1girl, fox"\n'
    )
    assert _fix_duplicate_yaml_keys(fm) == fm


def test_validate_and_fix_frontmatter_repairs_duplicate_keys():
    """記事全体を通しても重複キーが修復され、本文は保持される"""
    doc = "---" + BROKEN_FM + "---\n\n# 本文\n\nテスト本文です。\n"
    fixed = validate_and_fix_frontmatter(doc)
    data = yaml.safe_load(fixed.split("---")[1])
    assert data["character_1"] == VAL1
    assert data["character_2"] == VAL2
    assert fixed.endswith("テスト本文です。\n")
