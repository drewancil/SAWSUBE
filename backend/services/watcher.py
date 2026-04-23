from __future__ import annotations
import asyncio
import logging
import os
from pathlib import Path
from sqlalchemy import select
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from ..database import SessionLocal
from ..models.folder import WatchFolder
from ..models.image import Image
from .image_processor import is_supported, sha256_file, process_image, make_thumbnail
from .ws_manager import ws_manager

log = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, folder_id: int) -> None:
        self.loop = loop
        self.folder_id = folder_id
        # Map path -> pending asyncio.Task; cancel & replace on each new event
        self._pending: dict[str, asyncio.Task] = {}

    def _enqueue(self, path: str) -> None:
        if not is_supported(path):
            return
        # Schedule on loop and track for debounce
        def _schedule():
            existing = self._pending.get(path)
            if existing and not existing.done():
                existing.cancel()
            self._pending[path] = asyncio.ensure_future(self._handle(path))
        try:
            self.loop.call_soon_threadsafe(_schedule)
        except RuntimeError:
            # Loop closed during shutdown
            pass

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)

    async def _handle(self, path: str) -> None:
        try:
            await asyncio.sleep(2)  # debounce mid-write
        except asyncio.CancelledError:
            return
        if not os.path.exists(path):
            return
        # Wait until file size stabilises (Windows lock workaround)
        try:
            prev = -1
            for _ in range(5):
                size = os.path.getsize(path)
                if size == prev and size > 0:
                    break
                prev = size
                await asyncio.sleep(0.5)
        except OSError:
            return
        try:
            digest = await asyncio.to_thread(sha256_file, path)
        except Exception as e:
            log.warning("hash failed %s: %s", path, e)
            return
        async with SessionLocal() as s:
            existing = (await s.execute(select(Image).where(Image.file_hash == digest))).scalar_one_or_none()
            if existing:
                return
            try:
                processed_path, w, h = await process_image(path, digest)
                thumb = await make_thumbnail(path, digest)
            except Exception as e:
                log.warning("process failed %s: %s", path, e)
                return
            img = Image(
                local_path=path, filename=os.path.basename(path),
                file_hash=digest, file_size=os.path.getsize(path),
                width=w, height=h, source="local",
                processed_path=processed_path, thumbnail_path=thumb,
            )
            s.add(img)
            await s.commit()
            await ws_manager.broadcast({"type": "image_added", "image_id": img.id, "filename": img.filename})


class FolderWatcher:
    def __init__(self) -> None:
        self.observer = Observer()
        self.handlers: dict[int, tuple] = {}
        self.started = False

    def start(self) -> None:
        if not self.started:
            self.observer.start()
            self.started = True

    def stop(self) -> None:
        if self.started:
            self.observer.stop()
            self.observer.join(timeout=3)
            self.started = False

    def add(self, folder_id: int, path: str, loop: asyncio.AbstractEventLoop) -> None:
        if folder_id in self.handlers or not os.path.isdir(path):
            return
        h = _Handler(loop, folder_id)
        watch = self.observer.schedule(h, path, recursive=True)
        self.handlers[folder_id] = (watch, h)

    def remove(self, folder_id: int) -> None:
        item = self.handlers.pop(folder_id, None)
        if item:
            self.observer.unschedule(item[0])

    async def reload(self, loop: asyncio.AbstractEventLoop) -> None:
        # Remove all
        for fid in list(self.handlers.keys()):
            self.remove(fid)
        async with SessionLocal() as s:
            rows = (await s.execute(select(WatchFolder).where(WatchFolder.is_active.is_(True)))).scalars().all()
            for f in rows:
                self.add(f.id, f.path, loop)


watcher = FolderWatcher()


async def scan_folder_now(path: str) -> int:
    """Sync-ingest all images in a folder; return count added."""
    added = 0
    if not os.path.isdir(path):
        return 0
    for root, _, files in os.walk(path):
        for fn in files:
            if not is_supported(fn):
                continue
            full = os.path.join(root, fn)
            try:
                digest = await asyncio.to_thread(sha256_file, full)
            except Exception:
                continue
            async with SessionLocal() as s:
                existing = (await s.execute(select(Image).where(Image.file_hash == digest))).scalar_one_or_none()
                if existing:
                    continue
                try:
                    processed_path, w, h = await process_image(full, digest)
                    thumb = await make_thumbnail(full, digest)
                except Exception as e:
                    log.warning("process failed %s: %s", full, e)
                    continue
                img = Image(
                    local_path=full, filename=fn, file_hash=digest,
                    file_size=os.path.getsize(full), width=w, height=h, source="local",
                    processed_path=processed_path, thumbnail_path=thumb,
                )
                s.add(img)
                await s.commit()
                added += 1
    return added
