"""Reddit source validation tests (SSRF guards, whitelist enforcement)."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch


async def test_invalid_subreddit_returns_empty(tmp_workdir):
    from backend.services.sources import reddit
    assert await reddit.fetch("../../etc/passwd") == []
    assert await reddit.fetch("has spaces") == []
    assert await reddit.fetch("") == []
    assert await reddit.fetch("a" * 100) == []


async def test_valid_subreddit_normalises_sort_and_t(tmp_workdir):
    from backend.services.sources import reddit
    captured = {}

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"data": {"children": []}}

    class FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    with patch("backend.services.sources.reddit.httpx.AsyncClient", FakeClient):
        out = await reddit.fetch("earthporn", sort="evilsort", t="evilt", limit=999)
    assert out == []
    assert "earthporn" in captured["url"]
    # invalid sort defaulted in URL "/top.json"
    assert "/top.json" in captured["url"]
    assert captured["params"]["t"] == "week"
    assert captured["params"]["limit"] == 100  # clamped from 999


async def test_limit_clamped_low(tmp_workdir):
    """limit < 1 clamps to 1."""
    from backend.services.sources import reddit
    captured = {}

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"data": {"children": []}}

    class FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, params=None):
            captured["params"] = params
            return FakeResponse()

    with patch("backend.services.sources.reddit.httpx.AsyncClient", FakeClient):
        await reddit.fetch("aww", limit=-5)
    assert captured["params"]["limit"] == 1
