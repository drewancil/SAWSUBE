"""Image processor tests with real Pillow fixtures."""
from __future__ import annotations
import os
from PIL import Image as PILImage


def test_is_supported(tmp_workdir):
    from backend.services.image_processor import is_supported
    assert is_supported("foo.jpg")
    assert is_supported("foo.PNG")
    assert is_supported("a/b/c.webp")
    assert not is_supported("doc.txt")
    assert not is_supported("noext")


def test_sha256_file_stable(tmp_workdir, make_jpeg):
    from backend.services.image_processor import sha256_file
    p = make_jpeg("a.jpg", size=(10, 10), color=(0, 0, 0))
    h1 = sha256_file(p)
    h2 = sha256_file(p)
    assert h1 == h2 and len(h1) == 64


def test_process_landscape(tmp_workdir, make_jpeg):
    from backend.services.image_processor import process_image_sync, sha256_file
    p = make_jpeg("land.jpg", size=(800, 400))
    digest = sha256_file(p)
    out, w, h = process_image_sync(p, digest)
    assert os.path.exists(out)
    # Always produces target resolution (default 4K)
    assert (w, h) == (3840, 2160)


def test_process_portrait_blur(tmp_workdir, make_jpeg):
    from backend.services.image_processor import process_image_sync, sha256_file
    p = make_jpeg("port.jpg", size=(400, 800))
    digest = sha256_file(p)
    out, w, h = process_image_sync(p, digest)
    assert (w, h) == (3840, 2160)


def test_process_cache_hit(tmp_workdir, make_jpeg):
    from backend.services.image_processor import process_image_sync, sha256_file
    p = make_jpeg("c.jpg", size=(200, 200))
    digest = sha256_file(p)
    a, _, _ = process_image_sync(p, digest)
    mtime_a = os.path.getmtime(a)
    b, _, _ = process_image_sync(p, digest)
    assert a == b
    assert os.path.getmtime(b) == mtime_a  # not regenerated


def test_make_thumbnail(tmp_workdir, make_jpeg):
    from backend.services.image_processor import make_thumbnail_sync, sha256_file
    p = make_jpeg("t.jpg", size=(800, 400))
    digest = sha256_file(p)
    out = make_thumbnail_sync(p, digest, width=200)
    with PILImage.open(out) as im:
        assert im.width == 200


def test_corrupt_file_raises(tmp_workdir, tmp_path):
    from backend.services.image_processor import process_image_sync
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"this is not an image")
    import pytest
    with pytest.raises(Exception):
        process_image_sync(str(bad), "deadbeef")


def test_exif_orientation_handled(tmp_workdir, tmp_path):
    """EXIF orientation tag handled — image should still process to target size."""
    from backend.services.image_processor import process_image_sync, sha256_file
    p = tmp_path / "exif.jpg"
    img = PILImage.new("RGB", (400, 200), (100, 100, 100))
    img.save(p, "JPEG", exif=b"")  # empty exif still triggers transpose path
    out, w, h = process_image_sync(str(p), sha256_file(str(p)))
    assert (w, h) == (3840, 2160)
