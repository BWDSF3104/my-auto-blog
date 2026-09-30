import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fetch_topics import _is_nsfw_post


class TestIsNSFWPost:
    """_is_nsfw_post() のユニットテスト"""

    def test_nsfw_rating_explicit(self):
        """rating: 'e' (explicit) の場合はTrueを返す"""
        post = {
            "rating": "e",
            "tags": {"general": ["test", "safe"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_rating_questionable(self):
        """rating: 'q' (questionable) の場合はFalseを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "safe"]}
        }
        assert _is_nsfw_post(post) is False

    def test_nsfw_rating_safe(self):
        """rating: 's' (safe) の場合はFalseを返す"""
        post = {
            "rating": "s",
            "tags": {"general": ["test", "safe"]}
        }
        assert _is_nsfw_post(post) is False

    def test_nsfw_tag_in_general(self):
        """generalタグにNSFW用語が含まれる場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "sexual"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_tag_in_species(self):
        """speciesタグにNSFW用語が含まれる場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test"], "species": ["loli"]}
        }
        assert _is_nsfw_post(post) is True

    def test_nsfw_tag_in_copyright(self):
        """copyrightタグにNSFW用語が含まれる場合はTrueを返す"""
        post = {
            "rating": "q",
            "tags": {"general": ["test"], "copyright": ["penis"]}
        }
        assert _is_nsfw_post(post) is True

    def test_sfw_post(self):
        """SFWな投稿の場合はFalseを返す"""
        post = {
            "rating": "s",
            "tags": {"general": ["kemono", "dragon"], "species": ["dragon"]}
        }
        assert _is_nsfw_post(post) is False

    def test_empty_tags(self):
        """タグが空の場合はFalseを返す"""
        post = {
            "rating": "q",
            "tags": {}
        }
        assert _is_nsfw_post(post) is False

    def test_multiple_nsfw_tags(self):
        """複数のNSFWタグが含まれる場合はTrueを返す"""
        post = {
            "rating": "e",
            "tags": {"general": ["sexual", "breast_exposure"]}
        }
        assert _is_nsfw_post(post) is True

    def test_case_sensitive_nsfw(self):
        """NSFWタグは小文字でマッチする"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "sex"]}
        }
        assert _is_nsfw_post(post) is True

    def test_partial_word_no_match(self):
        """部分一致ではなく完全一致でマッチする"""
        post = {
            "rating": "q",
            "tags": {"general": ["test", "namespace"]}
        }
        assert _is_nsfw_post(post) is False

    def test_missing_keys(self):
        """必要なキーが不足している場合はFalseを返す"""
        post = {}
        assert _is_nsfw_post(post) is False

    def test_mixed_tags(self):
        """SFWとNSFWのタグが混在する場合はTrueを返す"""
        post = {
            "rating": "s",
            "tags": {"general": ["safe", "test", "vagina"]}
        }
        assert _is_nsfw_post(post) is True
