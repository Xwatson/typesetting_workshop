from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from typesetting_workshop.services.repository import QueueRepository

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


class PhotoImportService:
    def __init__(self, repository: QueueRepository, images_dir: Path) -> None:
        self.repository = repository
        self.images_dir = images_dir
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def scan_folder(self, folder: Path) -> int:
        if not folder.exists() or not folder.is_dir():
            return 0

        imported = 0
        for file_path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if self.import_path(file_path):
                imported += 1
        return imported

    def import_path(self, path: Path) -> bool:
        if not self.is_supported_image(path):
            return False
        try:
            md5 = self.compute_md5(path)
            target = self.images_dir / f"{md5}{path.suffix.lower()}"
            if not target.exists():
                shutil.copy2(path, target)
            return self.repository.register_photo(str(path), str(target), md5)
        except OSError:
            return False

    @staticmethod
    def is_supported_image(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS

    @staticmethod
    def compute_md5(path: Path) -> str:
        digest = hashlib.md5()
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
