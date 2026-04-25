from __future__ import annotations
import io
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from ..config import settings

router = APIRouter(prefix="/api/radarr", tags=["radarr"])


# Whitelisted hosts for arbitrary URL proxying (TMDB image CDN, etc.)
_REMOTE_HOST_WHITELIST = {
    "image.tmdb.org",
    "www.themoviedb.org",
    "themoviedb.org",
    "artworks.thetvdb.com",
    "thetvdb.com",
    "fanart.tv",
    "assets.fanart.tv",
}


@router.get("/image")
async def proxy_radarr_image(
    path: str | None = Query(None, description="Radarr MediaCover path"),
    url: str | None = Query(None, description="Whitelisted remote image URL (TMDB/TVDB/FanArt)"),
    w: int | None = Query(None, ge=50, le=2000, description="Resize to this width (px)"),
):
    """Proxy & optionally resize an image from Radarr or a whitelisted remote host.
    Long-lived cache headers (30d) — Tizen WebKit honours these."""
    if not path and not url:
        raise HTTPException(status_code=400, detail="Either 'path' or 'url' is required")

    headers: dict[str, str] = {}
    auth = None
    target_url: str

    if url:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or parsed.hostname not in _REMOTE_HOST_WHITELIST:
            raise HTTPException(status_code=400, detail=f"Host '{parsed.hostname}' not whitelisted for remote proxy")
        target_url = url
    else:
        if not settings.RADARR_URL:
            raise HTTPException(status_code=503, detail="RADARR_URL not configured")
        radarr_base = settings.RADARR_URL.rstrip("/")
        target_url = radarr_base + (path or "")
        sep = "&" if "?" in target_url else "?"
        if "apikey=" not in target_url:
            target_url += f"{sep}apikey={settings.RADARR_API_KEY}"
        headers["X-Api-Key"] = settings.RADARR_API_KEY
        if settings.RADARR_USERNAME and settings.RADARR_PASSWORD:
            auth = (settings.RADARR_USERNAME, settings.RADARR_PASSWORD)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            res = await client.get(target_url, headers=headers, auth=auth)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach upstream: {e}")

    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="Upstream image request failed")

    content = res.content
    content_type = res.headers.get("content-type", "image/jpeg")

    # Resize server-side with Pillow when ?w= is requested
    if w and content_type.startswith("image/"):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            if img.width > w:
                new_h = max(1, round(img.height * w / img.width))
                img = img.resize((w, new_h), Image.LANCZOS)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=82, optimize=True)
                content = buf.getvalue()
                content_type = "image/jpeg"
        except Exception:
            pass  # Serve original on any error

    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=2592000"},  # 30 days
    )
