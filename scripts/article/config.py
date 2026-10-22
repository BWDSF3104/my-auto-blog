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
SITE_ORIGIN = os.environ.get("SITE_ORIGIN") or "https://BWDSF3104.github.io"
MAX_INLINE_IMAGES = int(os.environ.get("MAX_INLINE_IMAGES", "7"))
MIN_SCORE_THRESHOLD = int(os.environ.get("MIN_SCORE_THRESHOLD", "0"))
GENRE_SCORES_PATH = os.path.join("data", "genre_scores", "topics.json")
GENRE_FILTER_MIN_SCORE = int(os.environ.get("GENRE_FILTER_MIN_SCORE", "30"))
# 人気作品の注注入件数上限（参考投稿の作品、またはフォールバック時の集計上位）
POPULAR_CPS_LIMIT = int(os.environ.get("POPULAR_CPS_LIMIT", "2"))
# 人気artist の注注入件数上限（投稿数上位）
POPULAR_ARTIST_LIMIT = int(os.environ.get("POPULAR_ARTIST_LIMIT", "1"))

# 画像プロンプトの固定ベース・フォールバック指定 (Nova-Furry-XL向け)
# SFWタグを常に付与して安全な画像生成を強制
# アートスタイルは記事ごとにFrontmatterのart_styleで決定（BASE_QUALITY_PROMPTには含めない）
BASE_QUALITY_PROMPT = "masterpiece, best quality, very aesthetic, ultra-detailed, furry, no human, safe for work"
DEFAULT_ART_STYLE = "anime style, illustration, cel shading"
DEFAULT_SITUATION = "dragon, blueeyes, white scale, sitting at desk with laptop, tech room"
# カウントタグ（1girl, 2girls等）の強調重み。space側の強調構文で人間寄りへの引きを減衰（1.0=減衰なし）
COUNT_TAG_WEIGHT = 0.6

# ZeroGPU quota 確認（HF Space → Pollinations.ai へのフォールバック判定）
ZERO_GPU_QUOTA_URL = "https://huggingface.co/api/spaces/zero-gpu/quota"
# 残量（GPU 秒）がこの閾値未満の時は画像生成を Pollinations.ai に切り替え（HF 未接続）。
# 1呼び出し=最大20秒 × 2 枚分の余裕。
ZERO_GPU_QUOTA_THRESHOLD_SECONDS = int(os.environ.get("ZERO_GPU_QUOTA_THRESHOLD_SECONDS", "40"))
# quota 取得の試行回数
ZERO_GPU_QUOTA_CHECK_ATTEMPTS = int(os.environ.get("ZERO_GPU_QUOTA_CHECK_ATTEMPTS", "3"))
# 1試行のタイムアウト（秒）
ZERO_GPU_QUOTA_CHECK_TIMEOUT_SECONDS = int(os.environ.get("ZERO_GPU_QUOTA_CHECK_TIMEOUT_SECONDS", "5"))
# リトライ間隔（秒）
ZERO_GPU_QUOTA_CHECK_DELAY_SECONDS = int(os.environ.get("ZERO_GPU_QUOTA_CHECK_DELAY_SECONDS", "5"))

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
# 物語系プロンプトの被り防止セクション（【直近の執筆作品】+【キャラクター・テーマ被り防止】）の出力トグル（デフォルトOFF）
# キャラクター・テーマのランダム化がPython側（_randomize_kemono_params）で実装済みのため、
# 既定では不要。環境変数 ENABLE_CHAR_DEDUP=1 で有効化（非物語系の【重要：重複の禁止】は対象外・常時ON）
ENABLE_CHAR_DEDUP = os.environ.get("ENABLE_CHAR_DEDUP", "0") == "1"

# --------------------------------------------------
# アフィリエイトのトグル
# --------------------------------------------------
# 末尾セクションのタグ由来検索リンク行（「Amazon / 楽天市場で検索」）の生成トグル（デフォルトOFF）
# OFF時は楽天API商品カードのみ維持（カードも無ければ末尾セクション全体をスキップ）。
# 環境変数 ENABLE_TAG_AFFILIATE=1 で有効化（比較表・product_recommendations カードは対象外・常時ON）
ENABLE_TAG_AFFILIATE = os.environ.get("ENABLE_TAG_AFFILIATE", "0") == "1"

# --------------------------------------------------
# kemono_story プロンプトのPython側ランダム化設定
# --------------------------------------------------
# 各項目の重み付き選択でテーマの多様性を確保
# 値は体型タグのリスト（個別タグとしてそのまま使用）。
# プロンプト表示文字列は " / " 結合（char_type）で生成する
CHAR_TYPE_WEIGHTS = [
    (["chibi"], 25),
    (["動物"], 25),
    (["二足歩行の動物"], 25),
    (["獣人"], 10),
    (["獣人", "二足歩行の動物"], 5),
    (["獣人", "動物"], 5),
    (["二足歩行の動物", "動物"], 5),
]

# char_type (日本語) 各要素 → 画像プロンプト用の体型タグ（Danbooru 英語タグ）。
# 冒頭注入時の提示に使用（例: 動物(feral)）。CHAR_TYPE_WEIGHTS の各要素と対応。
CHAR_TYPE_BODY_TAG = {
    "chibi": "chibi",
    "動物": "feral",
    "二足歩行の動物": "semi-anthro, [feral]",
    "獣人": "anthro",
}

WORLD_SETTING_WEIGHTS = [
    ("fantasy", 13),
    ("isekai", 10),
    ("modern", 10),
    ("slice_of_life", 10),
    ("sf", 8),
    ("pokemon", 8),
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
    "pokemon": ["action"],
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
    "pokemon": ["ポケモン"],
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

# 叙述視点の選択肢（毎回均一ランダム選択。表の上3種のみ）
# key → プロンプト注入用の指示文（kemono_story.txt / refine_story.txt で【視点】に使用）
_KEMONO_NARRATION_OPTIONS = {
    "first_person": (
        "一人称で執筆せよ。全描写は主人公の視点・感覚に基づく。"
        "他のキャラクターの思考・感情・意図を直接記述しないこと"
        "（対話・表情・行動・反応から伝わせて示せ）。"
    ),
    "third_person_limited": (
        "第3人称限定的で執筆せよ。全文を通じて主人公を視点の中心にし、"
        "他のキャラクターの思考・感情・意図を直接記述しないこと"
        "（対話・表情・行動・反応から伝わせて示せ）。"
    ),
    "third_person_omniscient": (
        "第3人称全知的で執筆せよ。全キャラクターの思考・感情を知る視点から記述し、"
        "場面に応じて各キャラクターの視点に切り替えられる。"
    ),
}
# 生成情報セクション表示用の視点ラベル
_KEMONO_NARRATION_LABEL = {
    "first_person": "一人称",
    "third_person_limited": "第3人称限定的（主人公視点）",
    "third_person_omniscient": "第3人称全知（俯瞰）",
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

# クローン系（clone / dark_persona）の画像プロンプトルールはスクリプト側の強制注入で対応する
# （compose_image_prompt の scene_injection 参照）。Gemini への指示は廃止した。

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
    "BASE_URL", "SITE_ORIGIN", "MAX_INLINE_IMAGES", "MIN_SCORE_THRESHOLD",
    "GENRE_SCORES_PATH", "GENRE_FILTER_MIN_SCORE",
    "POPULAR_CPS_LIMIT", "POPULAR_ARTIST_LIMIT",
    "BASE_QUALITY_PROMPT", "DEFAULT_ART_STYLE", "DEFAULT_SITUATION", "COUNT_TAG_WEIGHT",
    "ZERO_GPU_QUOTA_URL", "ZERO_GPU_QUOTA_THRESHOLD_SECONDS",
    "ZERO_GPU_QUOTA_CHECK_ATTEMPTS", "ZERO_GPU_QUOTA_CHECK_TIMEOUT_SECONDS", "ZERO_GPU_QUOTA_CHECK_DELAY_SECONDS",
    "MIN_DESC_LEN", "MAX_DESC_LEN",
    "INLINE_IMAGE_PATTERN", "INLINE_AFFILIATE_PATTERN", "INLINE_AFF_PRODUCT_PATTERN",
    "ENABLE_CHAR_DEDUP", "ENABLE_TAG_AFFILIATE",
    # kemono_story ランダム化
    "CHAR_TYPE_WEIGHTS", "WORLD_SETTING_WEIGHTS", "TRANSFORM_WEIGHTS",
    "RELATIONSHIP_WEIGHTS", "EXTRA_SETTING_WEIGHTS",
    "CHAR_TYPE_BODY_TAG",
    "WORLD_SETTING_GENRE_MAP",
    "_KEMONO_WORLD_TAGS", "_KEMONO_WORLD_TEXT", "_KEMONO_TRANSFORM_TEXT",
    "_KEMONO_TRANSFORM_LABEL", "_KEMONO_TRANSFORM_TAGS",
    "_KEMONO_RELATIONSHIP_TEXT", "_KEMONO_EXTRA_TAGS",
    "_KEMONO_EXTRA_TEXT",
    "_KEMONO_NARRATION_OPTIONS", "_KEMONO_NARRATION_LABEL",
    "_KEMONO_CHAR_COUNT_DESC_2", "_KEMONO_CHARACTER2_RULES",
    "_KEMONO_CORE_TOKENS", "_KEMONO_ANCHOR_KEYWORDS", "_KEMONO_RELATIONSHIP_AFFILIATE",
    # アフィリエイト
    "_AF_EXCLUDE_CP_PATTERNS", "_AF_EXCLUDE_CPS",
    "_AFFILIATE_BAD_PREFIXES", "_KEYWORD_ENHANCEMENT",
]
