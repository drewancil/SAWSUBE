from __future__ import annotations
import io
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from ..config import settings

router = APIRouter(prefix="/api/radarr", tags=["radarr"])


@router.get("/image")
async def proxy_radarr_image(
    path: str = Query(..., description="Radarr MediaCover path, e.g. /MediaCover/123/poster.jpg?lastWrite=..."),
    w: int | None = Query(None, ge=50, le=2000, description="Resize to this width (px) server-side"),
):
    """Proxy a Radarr MediaCover image. Supports ?w=N for server-side resize + long-lived cache headers."""
    if not settings.RADARR_URL:
        raise HTTPException(status_code=503, detail="RADARR_URL not configured")

    radarr_base = settings.RADARR_URL.rstrip("/")
    url = radarr_base + path
    # Append apikey if not already present
    sep = "&" if "?" in url else "?"
    if "apikey=" not in url:
        url += f"{sep}apikey={settings.RADARR_API_KEY}"

    headers = {"X-Api-Key": settings.RADARR_API_KEY}
    auth = None
    if settings.RADARR_USERNAME and settings.RADARR_PASSWORD:
        auth = (settings.RADARR_USERNAME, settings.RADARR_PASSWORD)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            res = await client.get(url, headers=headers, auth=auth)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Radarr: {e}")

    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="Radarr image request failed")

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
