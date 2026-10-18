"""
test_gsc_index.py — gsc_index.py の単体テスト

全 Google API 呼び出しを unittest.mock でモックする（実 API を呼び出さない・クォータを消費しない）。
"""

import json
from unittest.mock import MagicMock, patch

import pytest

import gsc_index


SAMPLE_SA_INFO = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def _mock_session(status_code: int = 200) -> MagicMock:
    """AuthorizedSession を模したモック（post のレスポンスを固定）。"""
    session = MagicMock(name="AuthorizedSession")
    resp = MagicMock(name="resp")
    resp.status_code = status_code
    resp.text = "ok" if status_code == 200 else "error body"
    session.post.return_value = resp
    return session


class TestGetLatestUrls:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert gsc_index.get_latest_urls("2026-10-18") == []

    def test_reads_and_strips_urls(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        url_dir = tmp_path / "data" / "new_urls"
        url_dir.mkdir(parents=True)
        (url_dir / "2026-10-18.txt").write_text(
            "https://example.com/a\n\n  https://example.com/b  \n", encoding="utf-8"
        )
        urls = gsc_index.get_latest_urls("2026-10-18")
        assert urls == ["https://example.com/a", "https://example.com/b"]


class TestLoadCredentials:
    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv("GSC_SA_JSON", raising=False)
        with pytest.raises(RuntimeError, match="GSC_SA_JSON"):
            gsc_index.load_credentials()

    @patch.object(gsc_index.service_account.Credentials, "from_service_account_info")
    def test_loads_with_webmasters_scope(self, mock_from_info, monkeypatch):
        fake_creds = MagicMock(name="creds")
        mock_from_info.return_value = fake_creds
        monkeypatch.setenv("GSC_SA_JSON", json.dumps(SAMPLE_SA_INFO))

        creds = gsc_index.load_credentials()

        assert creds is fake_creds
        mock_from_info.assert_called_once_with(
            SAMPLE_SA_INFO,
            scopes=["https://www.googleapis.com/auth/webmasters"],
        )


class TestRequestIndexing:
    def test_success_returns_true(self):
        session = _mock_session(200)
        assert gsc_index.request_indexing(session, "https://example.com/a") is True

    def test_posts_inspect_payload(self):
        session = _mock_session(200)
        gsc_index.request_indexing(session, "https://example.com/a")
        session.post.assert_called_once_with(
            gsc_index.API_URL,
            json={
                "inspectionUrl": "https://example.com/a",
                "siteUrl": gsc_index.SITE_URL,
            },
            timeout=30,
        )

    def test_failure_returns_false(self):
        session = _mock_session(404)
        assert gsc_index.request_indexing(session, "https://example.com/a") is False


class TestMain:
    def test_skips_when_no_urls(self):
        with (
            patch.object(gsc_index, "get_latest_urls", return_value=[]),
            patch.object(gsc_index, "load_credentials") as mock_load,
        ):
            gsc_index.main()
        mock_load.assert_not_called()

    def test_success_no_exit(self):
        session = _mock_session(200)
        fake_creds = MagicMock(name="creds")
        with (
            patch.object(
                gsc_index,
                "get_latest_urls",
                return_value=["https://example.com/a", "https://example.com/b"],
            ),
            patch.object(gsc_index, "load_credentials", return_value=fake_creds),
            patch.object(gsc_index, "AuthorizedSession", return_value=session) as mock_session_cls,
        ):
            gsc_index.main()
        mock_session_cls.assert_called_once_with(fake_creds)
        assert session.post.call_count == 2

    def test_partial_failure_exits_1(self):
        session = MagicMock(name="AuthorizedSession")
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        fail_resp = MagicMock()
        fail_resp.status_code = 400
        fail_resp.text = "bad request"
        session.post.side_effect = [ok_resp, fail_resp]
        with (
            patch.object(
                gsc_index,
                "get_latest_urls",
                return_value=["https://example.com/a", "https://example.com/b"],
            ),
            patch.object(gsc_index, "load_credentials", return_value=MagicMock(name="creds")),
            patch.object(gsc_index, "AuthorizedSession", return_value=session),
        ):
            with pytest.raises(SystemExit) as excinfo:
                gsc_index.main()
        assert excinfo.value.code == 1
