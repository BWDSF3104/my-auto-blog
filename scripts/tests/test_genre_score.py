"""
test_genre_score.py — genre_score.py の単体テスト

全 HTTP 呼び出しを unittest.mock でモックする（実 API を呼び出さない・無料枠を消費しない）。
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

import genre_score
from genre_score import (
    APIError,
    ConfigError,
    ScoreValidationError,
    build_questions,
    main,
    parse_response,
    score_text,
    validate_raw_score,
)

ENV_CREDS = {
    "CLOUDFLARE_ACCOUNT_ID": "test-account-id",
    "CLOUDFLARE_API_TOKEN": "test-api-token",
}


def _api_response(scores: dict, success: bool = True) -> dict:
    """clef-flash API のレスポンス（REST envelope）を構築する。"""
    answers = {}
    for genre, raw in scores.items():
        answers[genre] = {
            "type": "score",
            "score": raw,
            "legend": {str(i): c for i, c in enumerate(genre_score.SCORE_CRITERIA)},
            "probabilities": {"0": 0.2, "1": 0.2, "2": 0.2, "3": 0.2, "4": 0.2},
            "confidence": 0.9,
        }
    return {
        "result": {
            "model": "clef-flash",
            "answers": answers,
            "usage": {"input_tokens": 120, "output_tokens": 8},
        },
        "success": success,
        "errors": [] if success else [{"code": 10000, "message": "test error"}],
        "messages": [],
    }


def _mock_post(payload: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = payload
    return mock_resp


class TestBuildQuestions:
    def test_default_genres(self):
        questions = build_questions(genre_score.DEFAULT_GENRES)
        assert set(questions) == {"sf", "fantasy", "cyberpunk", "action"}
        for q in questions.values():
            assert q["type"] == "score"
            assert q["criteria"] == list(genre_score.SCORE_CRITERIA)
            assert q["instructions"]

    def test_criteria_order_low_to_high(self):
        questions = build_questions(["sf"])
        assert questions["sf"]["criteria"][0] == "ほぼ該当しない"
        assert questions["sf"]["criteria"][-1] == "中心的・代表的なジャンル"

    def test_unknown_genre_fallback(self):
        questions = build_questions(["horror"])
        assert "horror" in questions["horror"]["instructions"]

    def test_empty_raises(self):
        with pytest.raises(ConfigError):
            build_questions([])

    def test_over_max_questions_raises(self):
        genres = [f"g{i}" for i in range(65)]
        with pytest.raises(ConfigError):
            build_questions(genres)

    def test_invalid_id_raises(self):
        with pytest.raises(ConfigError):
            build_questions(["bad id!"])


class TestValidateRawScore:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (0, 0),
            (1, 25),
            (2, 50),
            (3, 75),
            (4, 100),
            (2.7, 68),   # round(67.5) = 68
            (0.5, 12),   # round(12.5) = 12（banker's rounding）
            (0.3, 8),    # round(7.5) = 8
        ],
    )
    def test_conversion(self, raw, expected):
        assert validate_raw_score(raw) == expected

    def test_missing_raises(self):
        with pytest.raises(ScoreValidationError):
            validate_raw_score(None)

    def test_non_numeric_raises(self):
        with pytest.raises(ScoreValidationError):
            validate_raw_score("high")

    def test_bool_raises(self):
        with pytest.raises(ScoreValidationError):
            validate_raw_score(True)

    def test_out_of_range_raises(self):
        with pytest.raises(ScoreValidationError):
            validate_raw_score(4.5)
        with pytest.raises(ScoreValidationError):
            validate_raw_score(-0.1)


class TestParseResponse:
    def test_scores_extracted_independently(self):
        payload = _api_response({"sf": 4.0, "fantasy": 0.3, "action": 2.0})
        parsed = parse_response(payload, ["sf", "fantasy", "action"])
        assert parsed["scores"] == {"sf": 100, "fantasy": 8, "action": 50}

    def test_probabilities_and_usage_held(self):
        payload = _api_response({"sf": 2.0})
        parsed = parse_response(payload, ["sf"])
        assert set(parsed["probabilities"]["sf"]) == {"0", "1", "2", "3", "4"}
        assert parsed["usage"]["input_tokens"] == 120

    def test_missing_answer_raises(self):
        payload = _api_response({"sf": 2.0})
        with pytest.raises(ScoreValidationError):
            parse_response(payload, ["sf", "fantasy"])

    def test_api_error_response_raises(self):
        payload = _api_response({"sf": 2.0}, success=False)
        with pytest.raises(APIError, match="test error"):
            parse_response(payload, ["sf"])

    def test_missing_result_raises(self):
        with pytest.raises(APIError):
            parse_response({"success": True}, ["sf"])

    def test_non_numeric_score_raises(self):
        payload = _api_response({"sf": "high"})
        with pytest.raises(ScoreValidationError):
            parse_response(payload, ["sf"])

    def test_out_of_range_score_raises(self):
        payload = _api_response({"sf": 7.5})
        with pytest.raises(ScoreValidationError):
            parse_response(payload, ["sf"])


class TestCallApi:
    def test_success(self):
        with patch("requests.post", return_value=_mock_post(_api_response({"sf": 2.0}))) as mock_post:
            payload = genre_score.call_api("テスト文字列", ["sf"], "acct", "token")
        assert payload["success"] is True
        assert mock_post.call_count == 1
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        assert kwargs["json"]["model"] == "clef-flash"
        assert kwargs["json"]["state"] == "テスト文字列"

    def test_url_contains_account_and_model(self):
        with patch("requests.post", return_value=_mock_post(_api_response({"sf": 2.0}))) as mock_post:
            genre_score.call_api("t", ["sf"], "acct-123", "tok")
        url = mock_post.call_args[0][0]
        assert url == "https://api.cloudflare.com/client/v4/accounts/acct-123/ai/run/@cf/cloudflare/clef-flash"

    def test_missing_account_id_raises(self):
        with pytest.raises(ConfigError, match="CLOUDFLARE_ACCOUNT_ID"):
            genre_score.call_api("t", ["sf"], "", "tok")

    def test_missing_token_raises(self):
        with pytest.raises(ConfigError, match="CLOUDFLARE_API_TOKEN"):
            genre_score.call_api("t", ["sf"], "acct", "")

    def test_429_no_retry(self):
        with patch("requests.post", return_value=_mock_post({}, status_code=429)) as mock_post:
            with pytest.raises(APIError):
                genre_score.call_api("t", ["sf"], "acct", "tok")
        assert mock_post.call_count == 1

    def test_403_no_retry(self):
        with patch("requests.post", return_value=_mock_post({}, status_code=403)) as mock_post:
            with pytest.raises(APIError):
                genre_score.call_api("t", ["sf"], "acct", "tok")
        assert mock_post.call_count == 1

    def test_500_retried_then_success(self):
        ok = _mock_post(_api_response({"sf": 2.0}))
        bad = _mock_post({}, status_code=500)
        with patch("requests.post", side_effect=[bad, ok]) as mock_post, \
             patch("genre_score.time.sleep"):
            payload = genre_score.call_api("t", ["sf"], "acct", "tok")
        assert payload["success"] is True
        assert mock_post.call_count == 2

    def test_500_retries_exhausted(self):
        bad = _mock_post({}, status_code=500)
        with patch("requests.post", return_value=bad) as mock_post, \
             patch("genre_score.time.sleep"):
            with pytest.raises(APIError):
                genre_score.call_api("t", ["sf"], "acct", "tok")
        assert mock_post.call_count == 3

    def test_timeout_retried_then_success(self):
        import requests as req
        ok = _mock_post(_api_response({"sf": 2.0}))
        with patch("requests.post", side_effect=[req.exceptions.Timeout(), ok]) as mock_post, \
             patch("genre_score.time.sleep"):
            payload = genre_score.call_api("t", ["sf"], "acct", "tok")
        assert payload["success"] is True
        assert mock_post.call_count == 2

    def test_invalid_json_raises(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("bad json")
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(APIError):
                genre_score.call_api("t", ["sf"], "acct", "tok")


class TestScoreText:
    def test_result_structure(self):
        payload = _api_response({"sf": 4.0, "action": 1.0})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            result = score_text("攻殻機動隊", ["sf", "action"])
        assert result == {
            "input": "攻殻機動隊",
            "model": "@cf/cloudflare/clef-flash",
            "scores": {"sf": 100, "action": 25},
        }

    def test_debug_fields(self):
        payload = _api_response({"sf": 2.0})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            result = score_text("t", ["sf"], include_debug=True)
        assert result["raw_scores"] == {"sf": 2.0}
        assert "4" in result["probabilities"]["sf"]
        assert result["usage"]["input_tokens"] == 120

    def test_default_genres(self):
        payload = _api_response({g: 2.0 for g in genre_score.DEFAULT_GENRES})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            result = score_text("t")
        assert set(result["scores"]) == set(genre_score.DEFAULT_GENRES)

    def test_empty_text_raises(self):
        with pytest.raises(ConfigError):
            score_text("", ["sf"])

    def test_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        with patch("requests.post") as mock_post:
            with pytest.raises(ConfigError):
                score_text("t", ["sf"])
        assert mock_post.call_count == 0


class TestMain:
    def test_cli_outputs_json(self, capsys):
        payload = _api_response({"sf": 3.0, "fantasy": 0.0})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            exit_code = main(["--text", "攻殻機動隊", "--genres", "sf,fantasy"])
        out = capsys.readouterr().out
        assert exit_code == 0
        data = json.loads(out)
        assert data["input"] == "攻殻機動隊"
        assert data["scores"] == {"sf": 75, "fantasy": 0}
        # 日本語はエスケープされない
        assert "攻殻機動隊" in out

    def test_cli_writes_output_file(self, tmp_path):
        payload = _api_response({"sf": 2.0})
        out_file = tmp_path / "result.json"
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            exit_code = main(["--text", "テスト", "--genres", "sf", "--output", str(out_file)])
        assert exit_code == 0
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["scores"]["sf"] == 50

    def test_cli_error_exit_code(self, capsys, monkeypatch):
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        exit_code = main(["--text", "t"])
        err = capsys.readouterr().err
        assert exit_code == 1
        assert "CLOUDFLARE_ACCOUNT_ID" in err

    def test_token_not_in_output(self, capsys):
        payload = _api_response({"sf": 2.0})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            main(["--text", "t", "--genres", "sf", "--debug"])
        out = capsys.readouterr().out + capsys.readouterr().err
        assert "test-api-token" not in out


class TestCacheKey:
    def test_deterministic(self):
        key1 = genre_score._compute_cache_key("攻殻機動隊", ["sf", "action"])
        key2 = genre_score._compute_cache_key("攻殻機動隊", ["sf", "action"])
        assert key1 == key2

    def test_different_text_different_key(self):
        key1 = genre_score._compute_cache_key("攻殻機動隊", ["sf"])
        key2 = genre_score._compute_cache_key("マトリックス", ["sf"])
        assert key1 != key2

    def test_genre_order_independent(self):
        key1 = genre_score._compute_cache_key("t", ["sf", "action"])
        key2 = genre_score._compute_cache_key("t", ["action", "sf"])
        assert key1 == key2

    def test_whitespace_normalized(self):
        key1 = genre_score._compute_cache_key("  t  ", ["sf"])
        key2 = genre_score._compute_cache_key("t", ["sf"])
        assert key1 == key2


class TestCacheFunctions:
    def test_load_cache_missing_file(self, tmp_path):
        assert genre_score._load_cache(str(tmp_path / "nonexistent.json")) == {}

    def test_load_cache_corrupt_file(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        assert genre_score._load_cache(str(bad)) == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        path = str(tmp_path / "cache.json")
        entry = {"input": "t", "scores": {"sf": 50}}
        genre_score._save_cache_entry(path, "abc123", entry)
        cache = genre_score._load_cache(path)
        assert cache["abc123"] == entry

    def test_save_multiple_entries(self, tmp_path):
        path = str(tmp_path / "cache.json")
        genre_score._save_cache_entry(path, "k1", {"scores": {"sf": 10}})
        genre_score._save_cache_entry(path, "k2", {"scores": {"sf": 20}})
        cache = genre_score._load_cache(path)
        assert "k1" in cache and "k2" in cache

    def test_save_creates_directory(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "cache.json")
        genre_score._save_cache_entry(path, "k", {"scores": {}})
        assert os.path.exists(path)


class TestScoreTextWithCache:
    def test_cache_miss_then_hit(self, tmp_path):
        cache_path = str(tmp_path / "cache.json")
        payload = _api_response({"sf": 4.0, "action": 1.0})
        with patch("requests.post", return_value=_mock_post(payload)) as mock_post, \
             patch.dict(os.environ, ENV_CREDS):
            result1 = score_text("攻殻機動隊", ["sf", "action"], cache_path=cache_path)
            assert result1["cache_hit"] is False
            assert mock_post.call_count == 1
            result2 = score_text("攻殻機動隊", ["sf", "action"], cache_path=cache_path)
            assert result2["cache_hit"] is True
            assert mock_post.call_count == 1

    def test_cache_hit_returns_same_scores(self, tmp_path):
        cache_path = str(tmp_path / "cache.json")
        payload = _api_response({"sf": 3.0, "fantasy": 0.0})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            result1 = score_text("t", ["sf", "fantasy"], cache_path=cache_path)
            result2 = score_text("t", ["sf", "fantasy"], cache_path=cache_path)
        assert result1["scores"] == result2["scores"]
        assert result2["cache_hit"] is True

    def test_cache_debug_fields(self, tmp_path):
        cache_path = str(tmp_path / "cache.json")
        payload = _api_response({"sf": 2.0})
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS):
            result = score_text("t", ["sf"], include_debug=True, cache_path=cache_path)
        assert result["cache_hit"] is False
        assert result["raw_scores"] == {"sf": 2.0}
        result2 = score_text("t", ["sf"], include_debug=True, cache_path=cache_path)
        assert result2["cache_hit"] is True
        assert result2["raw_scores"] == {"sf": 2.0}
        assert result2["usage"]["input_tokens"] == 120
        assert "timestamp" in result2

    def test_no_cache_path_no_caching(self):
        payload = _api_response({"sf": 2.0})
        with patch("requests.post", return_value=_mock_post(payload)) as mock_post, \
             patch.dict(os.environ, ENV_CREDS):
            score_text("t", ["sf"], cache_path=None)
            score_text("t", ["sf"], cache_path=None)
        assert mock_post.call_count == 2

    def test_different_genres_different_cache(self, tmp_path):
        cache_path = str(tmp_path / "cache.json")
        payload = _api_response({"sf": 2.0, "horror": 3.0})
        with patch("requests.post", return_value=_mock_post(payload)) as mock_post, \
             patch.dict(os.environ, ENV_CREDS):
            score_text("t", ["sf", "horror"], cache_path=cache_path)
            score_text("t", ["sf"], cache_path=cache_path)
        assert mock_post.call_count == 2


class TestMainCache:
    def test_cli_no_cache_flag(self, tmp_path, capsys):
        payload = _api_response({"sf": 3.0})
        tmp_cache = str(tmp_path / "cache.json")
        with patch("requests.post", return_value=_mock_post(payload)) as mock_post, \
             patch.dict(os.environ, ENV_CREDS), \
             patch.object(genre_score, "DEFAULT_CACHE_PATH", tmp_cache):
            main(["--text", "t", "--genres", "sf"])
            assert mock_post.call_count == 1
            main(["--text", "t", "--genres", "sf", "--no-cache"])
            assert mock_post.call_count == 2

    def test_cli_cache_hit_message(self, tmp_path, capsys):
        payload = _api_response({"sf": 3.0})
        tmp_cache = str(tmp_path / "cache.json")
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS), \
             patch.object(genre_score, "DEFAULT_CACHE_PATH", tmp_cache):
            main(["--text", "t", "--genres", "sf"])
            capsys.readouterr()
            main(["--text", "t", "--genres", "sf"])
        err = capsys.readouterr().err
        assert "キャッシュヒット" in err

    def test_cli_cache_hit_in_output(self, tmp_path, capsys):
        payload = _api_response({"sf": 3.0})
        tmp_cache = str(tmp_path / "cache.json")
        with patch("requests.post", return_value=_mock_post(payload)), \
             patch.dict(os.environ, ENV_CREDS), \
             patch.object(genre_score, "DEFAULT_CACHE_PATH", tmp_cache):
            main(["--text", "t", "--genres", "sf"])
            capsys.readouterr()
            exit_code = main(["--text", "t", "--genres", "sf"])
        out = capsys.readouterr().out
        assert exit_code == 0
        data = json.loads(out)
        assert data["cache_hit"] is True
