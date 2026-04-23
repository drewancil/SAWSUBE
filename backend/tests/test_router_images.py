"""Images router tests."""
from __future__ import annotations
import os
import io


async def test_upload_and_list(app_client, jpeg_bytes):
    files = {"files": ("hello.jpg", jpeg_bytes(), "image/jpeg")}
    r = await app_client.post("/api/images/upload", files=files)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["filename"].endswith(".jpg")
    assert body[0]["width"] == 3840
    assert body[0]["height"] == 2160

    r2 = await app_client.get("/api/images")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


async def test_upload_rejects_non_image(app_client):
    files = {"files": ("notimg.jpg", b"this is plain text not jpeg", "image/jpeg")}
    r = await app_client.post("/api/images/upload", files=files)
    assert r.status_code == 400


async def test_upload_skips_unsupported_extension(app_client, jpeg_bytes):
    files = {"files": ("doc.txt", jpeg_bytes(), "text/plain")}
    r = await app_client.post("/api/images/upload", files=files)
    assert r.status_code == 200
    assert r.json() == []


async def test_upload_dedupes_by_hash(app_client, jpeg_bytes):
    payload = jpeg_bytes(size=(100, 60), color=(0, 0, 0))
    r1 = await app_client.post("/api/images/upload",
                               files={"files": ("a.jpg", payload, "image/jpeg")})
    r2 = await app_client.post("/api/images/upload",
                               files={"files": ("b.jpg", payload, "image/jpeg")})
    assert r1.json()[0]["id"] == r2.json()[0]["id"]


async def test_upload_sanitises_filename(app_client, jpeg_bytes):
    files = {"files": ("../../../etc/evil name!.jpg", jpeg_bytes(), "image/jpeg")}
    r = await app_client.post("/api/images/upload", files=files)
    assert r.status_code == 200
    fn = r.json()[0]["filename"]
    assert ".." not in fn
    assert "/" not in fn and "\\" not in fn


async def test_filter_by_tag(app_client, jpeg_bytes):
    r = await app_client.post("/api/images/upload",
                              files={"files": ("t.jpg", jpeg_bytes(), "image/jpeg")})
    iid = r.json()[0]["id"]
    await app_client.put(f"/api/images/{iid}/tags", json={"tags": "sunset,beach"})
    r2 = await app_client.get("/api/images?tag=beach")
    assert len(r2.json()) == 1
    r3 = await app_client.get("/api/images?tag=mountain")
    assert len(r3.json()) == 0


async def test_favourite_toggle(app_client, jpeg_bytes):
    r = await app_client.post("/api/images/upload",
                              files={"files": ("f.jpg", jpeg_bytes(), "image/jpeg")})
    iid = r.json()[0]["id"]
    r1 = await app_client.post(f"/api/images/{iid}/favourite")
    assert r1.json()["is_favourite"] is True
    r2 = await app_client.post(f"/api/images/{iid}/favourite")
    assert r2.json()["is_favourite"] is False


async def test_delete_removes_files(app_client, jpeg_bytes):
    r = await app_client.post("/api/images/upload",
                              files={"files": ("d.jpg", jpeg_bytes(), "image/jpeg")})
    body = r.json()[0]
    iid = body["id"]
    # File should exist
    from backend.database import SessionLocal
    from backend.models.image import Image
    async with SessionLocal() as s:
        img = await s.get(Image, iid)
        assert os.path.exists(img.local_path)
        local = img.local_path
    r2 = await app_client.delete(f"/api/images/{iid}")
    assert r2.status_code == 200
    assert not os.path.exists(local)
    r3 = await app_client.get("/api/images")
    assert r3.json() == []


async def test_delete_404(app_client):
    r = await app_client.delete("/api/images/9999")
    assert r.status_code == 404


async def test_thumbnail_endpoint(app_client, jpeg_bytes):
    r = await app_client.post("/api/images/upload",
                              files={"files": ("th.jpg", jpeg_bytes(), "image/jpeg")})
    iid = r.json()[0]["id"]
    r2 = await app_client.get(f"/api/images/{iid}/thumbnail")
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "image/jpeg"
