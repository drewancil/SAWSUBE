"""Pexels API source — photo search and single-photo fetch."""
from __future__ import annotations
import httpx
from ...config import settings

_BASE = "https://api.pexels.com/v1"


def _headers() -> dict[str, str]:
    return {"Authorization": settings.PEXELS_API_KEY}


def _normalise(p: dict) -> dict:
    src = p.get("src") or {}
    return {
        "id": str(p["id"]),
        "url": src.get("original") or src.get("large2x") or src.get("large"),
        "thumb": src.get("medium") or src.get("small"),
        "width": p.get("width"),
        "height": p.get("height"),
        "title": p.get("alt") or f"Pexels photo {p['id']}",
        "credit": p.get("photographer"),
        "credit_url": p.get("photographer_url"),
        "html": p.get("url"),
    }


async def search(query: str, per_page: int = 20) -> list[dict]:
    if not settings.PEXELS_API_KEY:
        return []
    params = {"query": query, "per_page": min(int(per_page), 80), "orientation": "landscape"}
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(f"{_BASE}/search", params=params, headers=_headers())
        r.raise_for_status()
        j = r.json()
    return [_normalise(p) for p in j.get("photos", [])]


async def get(photo_id: str) -> dict | None:
    if not settings.PEXELS_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(f"{_BASE}/photos/{photo_id}", headers=_headers())
        if r.status_code != 200:
            return None
    return _normalise(r.json())
