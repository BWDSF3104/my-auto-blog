"""
genre_score.py — Cloudflare Workers AI (clef-flash) ジャンルスコアリング

文字列を判断特化モデル `@cf/cloudflare/clef-flash` へ渡し、
複数ジャンルへの関連度を 0-100 の整数スコアで取得する。

- 各ジャンルは独立して採点する（合計を100に正規化しない）
- 5段階 criteria（低→高）: 0=ほぼ該当しない … 4=中心的・代表的なジャンル
- 生スコアは浮動小数（probability-weighted level, 0-4）を round(raw/4*100) で 0-100 へ変換
- 無料枠 10,000 neurons/日。超過（4xx: 401/403/429 等）は再試行せず明確なエラー
- 一時的なエラー（5xx・タイムアウト・接続エラー）のみ最大3回まで退避して再試行
- API トークンはログ・出力に出さない
- 判定結果は `data/genre_scores/cache.json` にキャッシュ（SHA256キー）。`--no-cache` で無効化

環境変数:
  CLOUDFLARE_ACCOUNT_ID : Cloudflare Account ID
  CLOUDFLARE_API_TOKEN  : Workers AI API トークン

Usage:
  python scripts/genre_score.py --text "攻殻機動隊"
  python scripts/genre_score.py --text "..." --genres sf,fantasy --output data/genre_score.json --debug
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# Windows コンソールで cp932 → UTF-8 変換エラーを防ぐ
# （PYTHONIOENCODING は起動時のみ参照されるため実行時設定は無効。パイプ時はstdioがcp932にフォールバックする）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# --------------------------------------------------
# 定数
# --------------------------------------------------
MODEL_ID = "@cf/cloudflare/clef-flash"
MODEL_NAME = "clef-flash"
API_BASE = "https://api.cloudflare.com/client/v4/accounts"
MAX_QUESTIONS = 64  # API の質問数上限
RAW_SCORE_MAX = 4   # 5段階 criteria → 生スコア 0..4
REQUEST_TIMEOUT = 60
MAX_ATTEMPTS = 3
RETRY_BACKOFFS = [2.0, 5.0]  # 秒（再試行間の退避）

# 5段階の採点基準（低評価 → 高評価順）
SCORE_CRITERIA = [
    "ほぼ該当しない",
    "弱い関連要素がある",
    "関連要素があるが主要ではない",
    "主要ジャンルの一つ",
    "中心的・代表的なジャンル",
]

# 初期ジャンル定義: question id -> 採点条件（日本語）
GENRE_INSTRUCTIONS = {
    "sf": "入力された作品がSFジャンルにどの程度該当するかを評価してください。作品の主要な設定、主題、特徴を考慮してください。",
    "fantasy": "入力された作品がファンタジージャンルにどの程度該当するかを評価してください。作品の主要な設定、主題、特徴を考慮してください。",
    "cyberpunk": "入力された作品がサイバーパンクジャンルにどの程度該当するかを評価してください。作品の主要な設定、主題、特徴を考慮してください。",
    "action": "入力された作品がアクションジャンルにどの程度該当するかを評価してください。作品の主要な設定、主題、特徴を考慮してください。",
    "slice_of_life": "入力された作品が日常物（スライス・オブ・ライフ）ジャンルにどの程度該当するかを評価してください。派手な世界観設定や大規模な衝突よりも、日常生活・人間関係・静かな情景が中心であるほど高評価です。",
    "mystery": "入力された作品がミステリー・サスペンスジャンルにどの程度該当するかを評価してください。謎解き・探偵・陰謀・心理的緊張が中心であるほど高評価です。",
    "historical": "入力された作品が歴史物ジャンルにどの程度該当するかを評価してください。時代劇・史前・古代・歴史的時代を舞台にしている、または歴史・時代要素が中心であるほど高評価です。",
}

DEFAULT_GENRES = ["sf", "fantasy", "cyberpunk", "action", "slice_of_life", "mystery", "historical"]

_GENERIC_INSTRUCTIONS = (
    "入力された作品が{genre}ジャンルにどの程度該当するかを評価してください。"
    "作品の主要な設定、主題、特徴を考慮してください。"
)

# API の question id 制約: 英数字・_・.・-（最大100文字）
_QUESTION_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,100}$")

# 再試行しない恒久エラー（認証・権限・無料枠超過・リクエスト不正）
PERMANENT_HTTP_ERRORS = {400, 401, 403, 404, 422, 429}

# キャッシュ TTL
CACHE_TTL_DAYS = 7
PROTECTED_SOURCES = {"e621"}

# キャッシュ
CACHE_DIR = "data/genre_scores"
CACHE_FILE_NAME = "cache.json"
DEFAULT_CACHE_PATH = os.path.join(CACHE_DIR, CACHE_FILE_NAME)


# --------------------------------------------------
# エラー
# --------------------------------------------------
class GenreScoreError(Exception):
    """ジャンルスコアリングのエラーベースクラス。"""


class ConfigError(GenreScoreError):
    """設定エラー（環境変数未設定、ジャンルリスト不正）。"""


class APIError(GenreScoreError):
    """API呼び出しエラー（HTTPエラー、API応答エラー）。"""


class ScoreValidationError(GenreScoreError):
    """生スコア検証失敗（欠落、非数値、範囲外）。"""


# --------------------------------------------------
# 質問構築
# --------------------------------------------------
def _genre_instructions(genre: str) -> str:
    return GENRE_INSTRUCTIONS.get(genre, _GENERIC_INSTRUCTIONS.format(genre=genre))


def build_questions(genres: list[str]) -> dict:
    """各ジャンルについて score 型の questions dict を構築する。

    genres が空、64個超過、id 制約違反の場合は ConfigError を送出する。
    未知の genre id は汎用 instruction テンプレートにフォールバックする。
    """
    if not genres:
        raise ConfigError("ジャンルリストが空です")
    if len(genres) > MAX_QUESTIONS:
        raise ConfigError(f"ジャンル数は {MAX_QUESTIONS} 個までです（実際: {len(genres)}）")
    questions = {}
    for genre in genres:
        if not _QUESTION_ID_RE.match(genre):
            raise ConfigError(f"無効なジャンル id: {genre!r}（英数字・_・.・- のみ、最大100文字）")
        questions[genre] = {
            "type": "score",
            "instructions": _genre_instructions(genre),
            "criteria": list(SCORE_CRITERIA),
        }
    return questions


# --------------------------------------------------
# スコア変換・レスポンス解析
# --------------------------------------------------
def validate_raw_score(raw, max_level: int = RAW_SCORE_MAX) -> int:
    """生スコア（0..max_level の浮動小数）を検証し 0-100 の整数へ変換する。

    欠落・非数値・範囲外の場合は ScoreValidationError を送出する（0点でごまかさない）。
    """
    if raw is None:
        raise ScoreValidationError("生スコアが欠落しています")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ScoreValidationError(f"生スコアが数値ではありません: {raw!r}")
    value = float(raw)
    if not (0 <= value <= max_level):
        raise ScoreValidationError(f"生スコアが範囲外です: {value}（0-{max_level} を想定）")
    return int(round(value / max_level * 100))


def parse_response(payload: dict, genres: list[str]) -> dict:
    """API レスポンス（REST envelope）から各ジャンルのスコアを検証・抽出する。

    戻り値:
        {
            "scores": {genre: int(0-100)},
            "raw": {genre: 生スコア},
            "probabilities": {genre: {段階: 確率}},
            "usage": {"input_tokens": int, "output_tokens": int},
        }
    """
    if not isinstance(payload, dict):
        raise APIError("API レスポンスが不正な形式です（dict ではありません）")
    if payload.get("success") is False:
        errors = payload.get("errors") or []
        detail = "; ".join(
            e.get("message", "") for e in errors if isinstance(e, dict)
        ) or "不明なエラー"
        raise APIError(f"API エラー: {detail}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise APIError("API レスポンスに result フィールドがありません")
    answers = result.get("answers")
    if not isinstance(answers, dict):
        raise APIError("API レスポンスに answers フィールドがありません")

    scores = {}
    raw_scores = {}
    probabilities = {}
    for genre in genres:
        answer = answers.get(genre)
        if not isinstance(answer, dict) or answer.get("type") != "score":
            raise ScoreValidationError(f"ジャンル '{genre}' の回答が欠落しています")
        raw_scores[genre] = answer.get("score")
        probabilities[genre] = answer.get("probabilities") or {}
        scores[genre] = validate_raw_score(answer.get("score"))

    return {
        "scores": scores,
        "raw": raw_scores,
        "probabilities": probabilities,
        "usage": result.get("usage") or {},
    }


# --------------------------------------------------
# API 呼び出し
# --------------------------------------------------
def _describe_http_error(status_code: int) -> str:
    if status_code in (401, 403):
        return f"HTTP {status_code}: 認証・権限エラー、または無料枠（10,000 neurons/日）超過の可能性があります"
    if status_code == 429:
        return "HTTP 429: レート制限、または無料枠（10,000 neurons/日）超過の可能性があります"
    return f"HTTP {status_code}: リクエストエラー"


def call_api(
    text: str,
    genres: list[str],
    account_id: str,
    api_token: str,
    timeout: int = REQUEST_TIMEOUT,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict:
    """clef-flash API を呼び出し、成功時の payload (dict) を返す。

    - 5xx・タイムアウト・接続エラー: 退避を挟み最大 max_attempts 回まで再試行
    - 4xx（401/403/429 等）: 再試行せず APIError を送出（無料枠超過は恒久エラー扱い）
    """
    if not account_id:
        raise ConfigError("CLOUDFLARE_ACCOUNT_ID が設定されていません")
    if not api_token:
        raise ConfigError("CLOUDFLARE_API_TOKEN が設定されていません")

    url = f"{API_BASE}/{account_id}/ai/run/{MODEL_ID}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL_NAME,
        "state": text,
        "questions": build_questions(genres),
    }

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < max_attempts:
                backoff = RETRY_BACKOFFS[min(attempt - 1, len(RETRY_BACKOFFS) - 1)]
                print(
                    f"[WARN] リクエスト失敗（試行 {attempt}/{max_attempts}）: "
                    f"{e.__class__.__name__}。{backoff:.0f}秒後に再試行",
                    file=sys.stderr,
                )
                time.sleep(backoff)
                continue
            raise APIError(
                f"API リクエストが {max_attempts} 回試行しても失敗しました: {e.__class__.__name__}"
            ) from e

        if resp.status_code in (200, 201, 202):
            try:
                return resp.json()
            except ValueError as e:
                raise APIError("API レスポンスが有効な JSON ではありません") from e

        if resp.status_code in PERMANENT_HTTP_ERRORS:
            raise APIError(_describe_http_error(resp.status_code))

        last_error = APIError(f"HTTP {resp.status_code}")
        if attempt < max_attempts:
            backoff = RETRY_BACKOFFS[min(attempt - 1, len(RETRY_BACKOFFS) - 1)]
            print(
                f"[WARN] HTTP {resp.status_code}（試行 {attempt}/{max_attempts}）。"
                f"{backoff:.0f}秒後に再試行",
                file=sys.stderr,
            )
            time.sleep(backoff)
            continue
        raise APIError(
            f"API リクエストが {max_attempts} 回試行しても失敗しました（HTTP {resp.status_code}）"
        )

    raise APIError(f"API リクエストが {max_attempts} 回試行しても失敗しました: {last_error}")


# --------------------------------------------------
# キャッシュ
# --------------------------------------------------
def _compute_cache_key(text: str, genres: list[str]) -> str:
    """テキストとジャンルリストから SHA256 キャッシュキーを生成する。"""
    normalized = text.strip()
    genres_key = ",".join(sorted(genres))
    return hashlib.sha256(f"{normalized}|{genres_key}".encode("utf-8")).hexdigest()


def _load_cache(cache_path: str) -> dict:
    """キャッシュファイルを読み込む。存在しない・破損時は空 dict を返す。

    CACHE_TTL_DAYS を超過したエントリを破棄する（PROTECTED_SOURCES は除外）。
    """
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        cutoff = (datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)).isoformat()
        expired = [
            k for k, v in data.items()
            if isinstance(v, dict)
            and v.get("source") not in PROTECTED_SOURCES
            and v.get("timestamp")
            and v["timestamp"] < cutoff
        ]
        if expired:
            for k in expired:
                del data[k]
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache_entry(cache_path: str, cache_key: str, entry: dict) -> None:
    """キャッシュに 1 エントリを追加・更新する。"""
    cache = _load_cache(cache_path)
    cache[cache_key] = entry
    cache_dir = os.path.dirname(cache_path)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
        f.write("\n")


# --------------------------------------------------
# オーケストレーション
# --------------------------------------------------
def score_text(
    text: str,
    genres: list[str] | None = None,
    include_debug: bool = False,
    cache_path: str | None = None,
    source: str = "unknown",
    **call_kwargs,
) -> dict:
    """文字列のジャンルスコアリングを実行し、結果 dict を返す。

    cache_path が指定された場合、結果を JSON キャッシュに保存・再利用する。
    cache_hit: True ならキャッシュから取得（API 未呼び出し）。

    戻り値:
        {"input": 入力文字列, "model": モデルID, "scores": {genre: int(0-100)}}
        cache_path 指定時: + {"cache_hit": bool}
        include_debug=True の場合: + {"raw_scores", "probabilities", "usage"}
    """
    if not text:
        raise ConfigError("入力文字列が空です")
    if genres is None:
        genres = list(DEFAULT_GENRES)

    if cache_path:
        cache_key = _compute_cache_key(text, genres)
        cache = _load_cache(cache_path)
        if cache_key in cache:
            cached = cache[cache_key]
            result = {
                "input": cached["input"],
                "model": MODEL_ID,
                "scores": cached["scores"],
                "cache_hit": True,
            }
            if include_debug:
                result["raw_scores"] = cached.get("raw_scores", {})
                result["probabilities"] = cached.get("probabilities", {})
                result["usage"] = cached.get("usage", {})
                result["timestamp"] = cached.get("timestamp")
            return result

    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")

    payload = call_api(text, genres, account_id, api_token, **call_kwargs)
    parsed = parse_response(payload, genres)

    result = {
        "input": text,
        "model": MODEL_ID,
        "scores": parsed["scores"],
    }
    if cache_path:
        result["cache_hit"] = False
    if include_debug:
        result["raw_scores"] = parsed["raw"]
        result["probabilities"] = parsed["probabilities"]
        result["usage"] = parsed["usage"]

    if cache_path:
        cache_entry = {
            "input": text,
            "genres": sorted(genres),
            "scores": parsed["scores"],
            "raw_scores": parsed["raw"],
            "probabilities": parsed["probabilities"],
            "usage": parsed["usage"],
            "model": MODEL_ID,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _save_cache_entry(cache_path, _compute_cache_key(text, genres), cache_entry)

    return result


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _parse_genres(raw: str) -> list[str]:
    return [g.strip() for g in raw.split(",") if g.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cloudflare Workers AI (clef-flash) で文字列のジャンルスコアリングを行う"
    )
    parser.add_argument("--text", required=True, help="採点対象の文字列")
    parser.add_argument(
        "--genres",
        default=None,
        help=f"カンマ区切りのジャンルリスト（既定: {','.join(DEFAULT_GENRES)}）",
    )
    parser.add_argument("--output", default=None, help="出力ファイルパス（JSON）")
    parser.add_argument(
        "--debug", action="store_true", help="生スコア・確率・トークン使用量を含めて出力"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="キャッシュを使用しない（API を毎回呼び出し、キャッシュも保存しない）",
    )
    args = parser.parse_args(argv)

    genres = _parse_genres(args.genres) if args.genres else list(DEFAULT_GENRES)
    cache_path = None if args.no_cache else DEFAULT_CACHE_PATH

    try:
        result = score_text(args.text, genres, include_debug=args.debug, cache_path=cache_path)
    except GenreScoreError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if result.get("cache_hit"):
        print("[INFO] キャッシュヒット（API 未呼び出し）", file=sys.stderr)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"[INFO] 出力: {args.output}", file=sys.stderr)
    print(output)
    return 0


# --------------------------------------------------
# トレンド・版権の事前スコアリング
# --------------------------------------------------
TOPICS_FILE = os.path.join("data", "topics", "latest.json")
COPYRIGHTS_FILE = os.path.join("data", "character_features.json")
TOPICS_OUTPUT = os.path.join(CACHE_DIR, "topics.json")


def score_topics(
    topics_path: str = TOPICS_FILE,
    copyrights_path: str = COPYRIGHTS_FILE,
    output_path: str = TOPICS_OUTPUT,
    genres: list[str] | None = None,
    cache_path: str | None = None,
) -> dict:
    """latest.json の全トレンドと character_features.json の版権を
    Clef-flash で事前スコアリングし、結果を JSON に保存する。

    戻り値:
        {"scored_at": ..., "topics": [...], "copyrights": [...],
         "api_calls": int, "cache_hits": int}
    """
    if genres is None:
        genres = list(DEFAULT_GENRES)
    if cache_path is None:
        cache_path = DEFAULT_CACHE_PATH

    with open(topics_path, "r", encoding="utf-8") as f:
        topics_data = json.load(f)

    api_calls = 0
    cache_hits = 0
    topic_results = []

    for item in topics_data.get("all", []):
        title = item.get("title", "").strip()
        if not title:
            continue
        source = item.get("source", "unknown")
        # description があればスコアリング入力に含める（ジャンル判断の精度向上）
        desc = (item.get("description") or "").strip()
        text = f"{title}\n{desc[:200]}" if desc else title
        try:
            result = score_text(text, genres, cache_path=cache_path, source=source)
            if result.get("cache_hit"):
                cache_hits += 1
            else:
                api_calls += 1
            topic_results.append({
                "key": item.get("url", title),
                "title": title,
                "source": source,
                "category": item.get("category", ""),
                "scores": result["scores"],
            })
        except GenreScoreError:
            topic_results.append({
                "key": item.get("url", title),
                "title": title,
                "source": source,
                "category": item.get("category", ""),
                "scores": None,
            })

    copyright_results = []
    if os.path.exists(copyrights_path):
        with open(copyrights_path, "r", encoding="utf-8") as f:
            cf_data = json.load(f)
        copyrights = cf_data.get("aggregates", {}).get("copyrights", {})
        for name in sorted(copyrights.keys()):
            try:
                result = score_text(name, genres, cache_path=cache_path, source="e621")
                if result.get("cache_hit"):
                    cache_hits += 1
                else:
                    api_calls += 1
                copyright_results.append({
                    "name": name,
                    "scores": result["scores"],
                })
            except GenreScoreError:
                copyright_results.append({
                    "name": name,
                    "scores": None,
                })

    output = {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "topics": topic_results,
        "copyrights": copyright_results,
        "api_calls": api_calls,
        "cache_hits": cache_hits,
    }

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return output


if __name__ == "__main__":
    sys.exit(main())
