"""generate_article.py パイプラインの静的設定・定数を集中管理するモジュール。

このファイルは純粋なデータ定義のみ（副作用は env 読取りと os.path 計算に限る）。
generate_article.py は `from article.config import *` でこれらを読み込む。
定数の参照先がサブモジュールへ移るにつれ、テストの patch 対象は
「その定数を読むコードが所在するモジュール」に合わせる（AGENTS.md 参照）。
"""
import os
import re

# --------------------------------------------------
# パス
# --------------------------------------------------
# config.py は <root>/scripts/article/config.py に配置されるため、
# プロジェクトルートは 3 階層上の dirname となる。
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOPICS_DIR = os.path.join(PROJECT_DIR, "data", "topics")
TOPICS_JSON_PATH = os.path.join(TOPICS_DIR, "latest.json")

TREND_USAGE_DIR = "data/trend_usage_logs"
DRAFTS_DIR = "data/drafts"
AFFILIATE_LINKS_DIR = "data/affiliate_logs"

LOG_CLEANUP_DAYS = 30
LOG_CLEANUP_DIRS = [
    DRAFTS_DIR,
    TREND_USAGE_DIR,
    AFFILIATE_LINKS_DIR,
    os.path.join("data", "prompt_logs"),
]
_LOG_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})\.")

SLUG_REDIRECTS_FILE = "data/slug-redirects.json"

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RAKUTEN_ORIGIN = os.environ.get("RAKUTEN_ORIGIN") or "https://bwdsf3104.github.io"
RAKUTEN_REFERER = os.environ.get("RAKUTEN_REFERER") or "https://bwdsf3104.github.io/my-auto-blog/"
RAKUTEN_CACHE_FILE = "data/rakuten_cache.json"
RAKUTEN_CACHE_TTL_DAYS = 30
_RAKUTEN_PHRASE_DELIMITERS = r'(?:用的|向け|用|的)'

# --------------------------------------------------
# 画像・モデル
# --------------------------------------------------
HF_TOKEN = os.environ.get("HF_TOKEN")
IMAGE_PROVIDER = os.environ.get("IMAGE_PROVIDER", "hf").lower()

MODELS_TO_TRY = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite"
]

HF_SPACE_ID = "blume/kemono-image-api"
BASE_URL = os.environ.get("SITE_BASE_PATH") or "/my-auto-blog"  # GitHub Pagesのベースパス
MAX_INLINE_IMAGES = int(os.environ.get("MAX_INLINE_IMAGES", "7"))
MIN_SCORE_THRESHOLD = int(os.environ.get("MIN_SCORE_THRESHOLD", "0"))
GENRE_SCORES_PATH = os.path.join("data", "genre_scores", "topics.json")
GENRE_FILTER_MIN_SCORE = int(os.environ.get("GENRE_FILTER_MIN_SCORE", "30"))

# 画像プロンプトの固定ベース・フォールバック指定 (Nova-Furry-XL向け)
# SFWタグを常に付与して安全な画像生成を強制
# アートスタイルは記事ごとにFrontmatterのart_styleで決定（BASE_QUALITY_PROMPTには含めない）
BASE_QUALITY_PROMPT = "masterpiece, best quality, very aesthetic, ultra-detailed, furry, safe for work"
DEFAULT_ART_STYLE = "anime style, illustration, cel shading"
DEFAULT_SITUATION = "dragon, blueeyes, white scale, sitting at desk with laptop, tech room"

# SEOメタ記述の文字数制約
MIN_DESC_LEN = 80
MAX_DESC_LEN = 120

# 本文内画像プレースホルダーの正規表現 (例: <!-- IMAGE_PROMPT: "..." -->)
INLINE_IMAGE_PATTERN = re.compile(
    r'<!--\s*IMAGE_PROMPT:\s*(.*?)\s*-->',
    re.IGNORECASE
)

# 本文内アフィリエイトプレースホルダーの正規表現 (例: <!-- AFFILIATE: "kw" | "anchor" -->)
INLINE_AFFILIATE_PATTERN = re.compile(
    r'<!--\s*AFFILIATE:\s*"([^"]+)"\s*\|\s*"([^"]+)"\s*-->',
    re.IGNORECASE
)

# 比較表内の商品リンクプレースホルダー (例: <!-- AFF_PRODUCT: "keyword" -->)
INLINE_AFF_PRODUCT_PATTERN = re.compile(
    r'<!--\s*AFF_PRODUCT:\s*"([^"]+)"\s*-->',
    re.IGNORECASE
)

# --------------------------------------------------
# プロンプトのトグル
# --------------------------------------------------
# 【キャラクター・テーマ被り防止】セクションの出力トグル（デフォルトOFF）
# キャラクター・テーマのランダム化がPython側（_randomize_kemono_params）で実装済みのため、
# 既定では不要。環境変数 ENABLE_CHAR_DEDUP=1 で有効化
ENABLE_CHAR_DEDUP = os.environ.get("ENABLE_CHAR_DEDUP", "0") == "1"

# --------------------------------------------------
# kemono_story プロンプトのPython側ランダム化設定
# --------------------------------------------------
# 各項目の重み付き選択でテーマの多様性を確保
# 値は体型タグのリスト（個別タグとしてそのまま使用）。
# プロンプト表示文字列は " / " 結合（char_type）で生成する
CHAR_TYPE_WEIGHTS = [
    (["chibi"], 25),
    (["動物"], 25),
    (["動物と獣人のハーフ"], 25),
    (["獣人"], 10),
    (["獣人", "動物と獣人のハーフ"], 5),
    (["獣人", "動物"], 5),
    (["動物と獣人のハーフ", "動物"], 5),
]

WORLD_SETTING_WEIGHTS = [
    ("fantasy", 21),
    ("isekai", 10),
    ("modern", 10),
    ("slice_of_life", 10),
    ("sf", 8),
    ("space_opera", 7),
    ("adventure", 7),
    ("cyberpunk", 7),
    ("dungeon_crawl", 6),
    ("mystery", 5),
    ("historical", 5),
    ("fantasy+sf", 4),
]

TRANSFORM_WEIGHTS = [
    ("none", 75),
    ("tf", 12),
    ("tsf", 10),
    ("tf+tsf", 3),
]

RELATIONSHIP_WEIGHTS = [
    ("yaoi", 55),
    ("yuri", 20),
    ("partnership", 15),
    ("hetero", 10),
]

EXTRA_SETTING_WEIGHTS = [
    ("none", 25),
    ("clone", 35),
    ("dark_persona", 30),
    ("rival", 10),
]


WORLD_SETTING_GENRE_MAP = {
    "fantasy": ["fantasy"],
    "isekai": ["fantasy", "action"],
    "modern": ["slice_of_life", "action", "mystery"],
    "sf": ["sf"],
    "space_opera": ["sf", "action"],
    "slice_of_life": ["slice_of_life"],
    "cyberpunk": ["cyberpunk"],
    "adventure": ["action", "fantasy"],
    "dungeon_crawl": ["fantasy", "action"],
    "mystery": ["mystery"],
    "historical": ["historical"],
    "fantasy+sf": ["fantasy", "sf"],
}

# 世界設定のタグリスト（個別タグとしてそのまま使用）
# プロンプト表示文字列は "と" 結合（_KEMONO_WORLD_TEXT）で生成する
_KEMONO_WORLD_TAGS = {
    "fantasy": ["ファンタジー"],
    "isekai": ["異世界"],
    "modern": ["現代"],
    "sf": ["SF"],
    "space_opera": ["スペースオペラ"],
    "slice_of_life": ["日常"],
    "cyberpunk": ["サイバーパンク"],
    "adventure": ["冒険"],
    "dungeon_crawl": ["ダンジョンクライム"],
    "mystery": ["ミステリー"],
    "historical": ["歴史"],
    "fantasy+sf": ["ファンタジー", "SF"],
}
_KEMONO_WORLD_TEXT = {key: "と".join(tags) for key, tags in _KEMONO_WORLD_TAGS.items()}

_KEMONO_TRANSFORM_TEXT = {
    "none": "",
    "tf": "、TF(変身・変形)",
    "tsf": "、TSF（性転換フィクション）",
    "tf+tsf": "、TF・TSF",
}

# 生成情報セクション用のクリーンな変身ラベル（プロンプト表示用の "、" 接頭文字列は表示に不適のため別定数）
_KEMONO_TRANSFORM_LABEL = {
    "none": "なし",
    "tf": "TF（変身・変形）",
    "tsf": "TSF（性転換フィクション）",
    "tf+tsf": "TF・TSF",
}

# 変身タグ（frontmatter tags に付与。tf+tsf は2タグに分割）
_KEMONO_TRANSFORM_TAGS = {
    "none": [],
    "tf": ["TF"],
    "tsf": ["TSF"],
    "tf+tsf": ["TF", "TSF"],
}

_KEMONO_RELATIONSHIP_TEXT = {
    "partnership": "相棒関係",
    "yaoi": "同性愛（男性同士の恋愛）",
    "yuri": "百合（女性同士の恋愛）",
    "hetero": "異性愛",
}

# 追加設定のタグ（個別タグとしてそのまま使用。frontmatter・生成情報表示用）
_KEMONO_EXTRA_TAGS = {
    "none": "",
    "clone": "クローンによる自分同士",
    "dark_persona": "dark persona",
    "rival": "ライバル関係",
}

# プロンプト表示文字列（タグより詳しい設定説明を付与するため明示定義）
_KEMONO_EXTRA_TEXT = {
    "none": "",
    "clone": "、クローンによる自分同士",
    "dark_persona": "、dark persona（もう一人の自分は自身の闇版。体色は黒っぽい）",
    "rival": "、ライバル関係",
}

# 登場キャラ数説明（char_count は常に2。clone/dark_persona は同じ外見の2人が登場する）
_KEMONO_CHAR_COUNT_DESC_2 = ["バディ", "ライバル", "カップル"]

# character_2 の定義ルール（追加設定ごとに条件分岐。クローンはクローン時のみ記載）
_KEMONO_CHARACTER2_RULES = {
    "none": "character_1 と character_2 の両方を必ず定義してください。character_2 の外見は character_1 と明確に区別できるものにしてください。",
    "clone": "character_1 と character_2 の両方を必ず定義してください。クローンによる自分同士の場合は character_2 の外見は character_1 と同一（区別のため小物・装飾のみ差異可）。",
    "dark_persona": "character_1 と character_2 の両方を必ず定義してください。もう一人の自分（character_2）の体色は黒っぽく変更してください。",
    "rival": "character_1 と character_2 の両方を必ず定義してください。character_2 は character_1 のライバルであり、外見は character_1 と明確に区別できるものにしてください。",
}

# クローン画像プロンプトルール（特約: extra_key == "clone" の時のみ注入）
_KEMONO_CLONE_RULE_TEXT = (
    "・【クローン画像プロンプトルール】\n"
    "  - character_1 と character_2 が一緒に登場する画像では、キャラクターIDの後のシーンキーワード部分に `clone` を含めてください（ヘッダーの image_prompt と本文の IMAGE_PROMPT の両方に適用）。\n"
    "  - 1人のキャラクターのみが登場する画像では `clone` を含めないでください（模型が2人生成するのを防ぐため）。"
)

# dark persona画像プロンプトルール（特約: extra_key == "dark_persona" の時のみ注入）
_KEMONO_DARK_PERSONA_RULE_TEXT = (
    "・【dark persona画像プロンプトルール】\n"
    "  - character_1 と character_2 が一緒に登場する画像では、キャラクターIDの後のシーンキーワード部分に `dark persona` と `clone` の両方を含めてください（ヘッダーの image_prompt と本文の IMAGE_PROMPT の両方に適用）。\n"
    "  - 1人のキャラクターのみが登場する画像では `dark persona` / `clone` を含めないでください（模型が2人生成するのを防ぐため）。"
)

# kemono_story 商品名の関連性判定トークン（固定リスト）
_KEMONO_CORE_TOKENS = ("ケモノ", "バケモノ", "獣人", "獣", "動物", "アニマル", "anthro", "beast")
_KEMONO_ANCHOR_KEYWORDS = ("ケモノ", "獣人", "動物")

_KEMONO_RELATIONSHIP_AFFILIATE = {
    "partnership": "バディ",
    "yaoi": "BL",
    "yuri": "百合",
    "hetero": "恋愛",
}

# --------------------------------------------------
# アフィリエイト
# --------------------------------------------------
# アフィリエイト不適格なコピーライト
_AF_EXCLUDE_CP_PATTERNS = ("mythology", "_mythology", "inktober")
_AF_EXCLUDE_CPS = {
    # 放送局
    "adult_swim", "cartoon_network", "british_broadcasting_corporation",
    # 食品・飲料・小売
    "monster_energy", "cup_noodles", "jack_in_the_box_(restaurant)",
    "cheetos", "frito-lay", "pepsico", "ikea",
    # ミーム
    "the_harkness_test_(meme)", "let_me_do_it_for_you", "casualties:_unknown",
    "gigachad", "low_tier_god", "no_thoughts_head_empty",
    "is_that_your_fucking_fursona?_that's_cringe",
    # プラットフォーム
    "e621", "scratch21", "gameoverse", "glitch_productions", "patreon", "bilibili",
    # 音楽
    "ac/dc", "doja_cat", "nirvana", "michael_jackson", "in_utero_(album)",
    # ライセンス
    "cc0", "creative_commons",
    # 政府機関
    "fbi",
    # 抽象・イベント
    "mood", "halloween", "father's_day",
    # 成人向け
    "takeshi_loves_sex",
}

# 無意味なキーワードのフィルタリスト（アフィリエイト検索に不適切な語）
_AFFILIATE_BAD_PREFIXES = (
    "a ", "an ", "the ", "how to", "what is", "why ", "best ",
    "top ", "new ", "latest", "review", "tutorial", "guide ",
    "e621", "github", "repo ", "repository", "source code",
    "open source", "free ", "download", "install", "setup ",
)

# キーワード改善辞書：一般的なタグ → 購買意欲の高い検索語
_KEYWORD_ENHANCEMENT = {
    "tech": "プログラミング 入門書",
    "ai": "AI 入門 書籍",
    "pokemon": "ポケモン 公式",
    "game": "ゲーム 周辺機器",
    "programming": "プログラミング 本",
    "web": "Web開発 書籍",
    "javascript": "JavaScript 本",
    "python": "Python 本",
    "rust": "Rust 本",
    "react": "React 書籍",
    "vue": "Vue.js 本",
    "next": "Next.js 書籍",
    "docker": "Docker 入門",
    "linux": "Linux 本",
    "css": "CSS 本",
    "html": "HTML 本",
}

__all__ = [
    # パス
    "PROJECT_DIR", "TOPICS_DIR", "TOPICS_JSON_PATH",
    "TREND_USAGE_DIR", "DRAFTS_DIR", "AFFILIATE_LINKS_DIR",
    "LOG_CLEANUP_DAYS", "LOG_CLEANUP_DIRS", "_LOG_TS_RE",
    "SLUG_REDIRECTS_FILE",
    "RAKUTEN_API_URL", "RAKUTEN_ORIGIN", "RAKUTEN_REFERER",
    "RAKUTEN_CACHE_FILE", "RAKUTEN_CACHE_TTL_DAYS", "_RAKUTEN_PHRASE_DELIMITERS",
    # 画像・モデル
    "HF_TOKEN", "IMAGE_PROVIDER", "MODELS_TO_TRY", "HF_SPACE_ID",
    "BASE_URL", "MAX_INLINE_IMAGES", "MIN_SCORE_THRESHOLD",
    "GENRE_SCORES_PATH", "GENRE_FILTER_MIN_SCORE",
    "BASE_QUALITY_PROMPT", "DEFAULT_ART_STYLE", "DEFAULT_SITUATION",
    "MIN_DESC_LEN", "MAX_DESC_LEN",
    "INLINE_IMAGE_PATTERN", "INLINE_AFFILIATE_PATTERN", "INLINE_AFF_PRODUCT_PATTERN",
    "ENABLE_CHAR_DEDUP",
    # kemono_story ランダム化
    "CHAR_TYPE_WEIGHTS", "WORLD_SETTING_WEIGHTS", "TRANSFORM_WEIGHTS",
    "RELATIONSHIP_WEIGHTS", "EXTRA_SETTING_WEIGHTS",
    "WORLD_SETTING_GENRE_MAP",
    "_KEMONO_WORLD_TAGS", "_KEMONO_WORLD_TEXT", "_KEMONO_TRANSFORM_TEXT",
    "_KEMONO_TRANSFORM_LABEL", "_KEMONO_TRANSFORM_TAGS",
    "_KEMONO_RELATIONSHIP_TEXT", "_KEMONO_EXTRA_TAGS",
    "_KEMONO_EXTRA_TEXT", "_KEMONO_CHAR_COUNT_DESC_2", "_KEMONO_CHARACTER2_RULES",
    "_KEMONO_CLONE_RULE_TEXT",
    "_KEMONO_DARK_PERSONA_RULE_TEXT",
    "_KEMONO_CORE_TOKENS", "_KEMONO_ANCHOR_KEYWORDS", "_KEMONO_RELATIONSHIP_AFFILIATE",
    # アフィリエイト
    "_AF_EXCLUDE_CP_PATTERNS", "_AF_EXCLUDE_CPS",
    "_AFFILIATE_BAD_PREFIXES", "_KEYWORD_ENHANCEMENT",
]
