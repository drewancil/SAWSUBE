"""Shared fixtures: per-test temp dirs + isolated SQLite DB + httpx AsyncClient."""
from __future__ import annotations
import asyncio
import os
import sys
import tempfile
import importlib
from io import BytesIO
from pathlib import Path

import pytest
import pytest_asyncio
from PIL import Image as PILImage


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def tmp_workdir(tmp_path, monkeypatch):
    """Point all settings dirs at a per-test tmp dir before any backend module imports."""
    data = tmp_path / "data"
    (data / "images").mkdir(parents=True)
    (data / "tokens").mkdir(parents=True)
    (data / "cache").mkdir(parents=True)
    (data / "thumbnails").mkdir(parents=True)

    monkeypatch.setenv("IMAGE_FOLDER", str(data / "images"))
    monkeypatch.setenv("DB_PATH", str(data / "sawsube.db"))
    monkeypatch.setenv("TOKEN_DIR", str(data / "tokens"))
    monkeypatch.setenv("IMAGE_CACHE_DIR", str(data / "cache"))
    monkeypatch.setenv("THUMBNAIL_DIR", str(data / "thumbnails"))
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path / "no_dist"))  # disable SPA mount
    monkeypatch.setenv("POLL_INTERVAL_SECS", "9999")  # don't poll during tests

    # Reload backend modules so they pick up new env
    to_drop = [m for m in list(sys.modules) if m.startswith("backend")]
    for m in to_drop:
        del sys.modules[m]

    yield tmp_path

    to_drop = [m for m in list(sys.modules) if m.startswith("backend")]
    for m in to_drop:
        del sys.modules[m]


@pytest_asyncio.fixture()
async def app_client(tmp_workdir):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.database import init_db

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def make_jpeg(tmp_path):
    """Factory: write a real JPEG file (default 100x60) and return path."""
    def _factory(name: str = "img.jpg", size=(100, 60), color=(120, 80, 40)) -> str:
        p = tmp_path / name
        img = PILImage.new("RGB", size, color)
        img.save(p, "JPEG", quality=80)
        return str(p)
    return _factory


@pytest.fixture()
def jpeg_bytes():
    def _factory(size=(100, 60), color=(50, 100, 150)) -> bytes:
        buf = BytesIO()
        PILImage.new("RGB", size, color).save(buf, "JPEG", quality=80)
        return buf.getvalue()
    return _factory
