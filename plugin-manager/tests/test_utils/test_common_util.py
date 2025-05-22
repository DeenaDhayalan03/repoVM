import gzip
import json
from base64 import b64encode

import pytest
from unittest.mock import patch, MagicMock
from fastapi import Response
from scripts.utils.common_util import (
    timed_lru_cache,
    get_unique_id,
    hit_external_service,
    unzip_and_decode_content,
    remove_captcha_cookies,
)
from scripts.errors import AuthenticationError

example_url = "https://example.com"
httpx_post = "httpx.Client.post"


@pytest.fixture
def sample_function():
    @timed_lru_cache(seconds=1)
    def func(x):
        return x * 2

    return func


def test_caches_function_results(sample_function):
    result1 = sample_function(2)
    result2 = sample_function(2)
    assert result1 == result2


def test_generates_unique_id():
    unique_id1 = get_unique_id()
    unique_id2 = get_unique_id()
    assert unique_id1 != unique_id2


def test_hits_external_service_successfully():
    api_url = example_url
    payload = {"key": "value"}
    with patch(httpx_post, return_value=MagicMock(status_code=200, json=lambda: {"response": "success"})) as mock_post:
        result = hit_external_service(api_url, payload=payload)
        assert result == {"response": "success"}
        mock_post.assert_called_once()


def test_handles_404_error():
    api_url = example_url
    with patch(httpx_post, return_value=MagicMock(status_code=404)) as mock_post:
        with pytest.raises(ModuleNotFoundError):
            hit_external_service(api_url)
        mock_post.assert_called_once()


def test_handles_401_error():
    api_url = example_url
    with patch(httpx_post, return_value=MagicMock(status_code=401)) as mock_post:
        with pytest.raises(AuthenticationError):
            hit_external_service(api_url)
        mock_post.assert_called_once()


def test_unzips_and_decodes_content_successfully():
    data = gzip.compress(b64encode(json.dumps({"key": "value"}).encode()))
    result = unzip_and_decode_content(data)
    assert result == {"key": "value"}


def test_handles_invalid_data_in_unzip_and_decode():
    data = b"invalid data"
    with pytest.raises(ValueError):
        unzip_and_decode_content(data)


def test_removes_captcha_cookies_successfully():
    response = Response()
    remove_captcha_cookies(response)
    cookies = response.headers.getlist("set-cookie")
    assert cookies
