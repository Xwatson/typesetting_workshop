from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from typesetting_workshop.services.importer import PhotoImportService


class _WatchHandler(FileSystemEventHandler):
    def __init__(self, service: "FolderWatchService") -> None:
        super().__init__()
        self.service = service

    def on_created(self, event: FileSystemEvent) -> None:
        self._dispatch(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._dispatch(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.service.pathDetected.emit(getattr(event, "dest_path", event.src_path))

    def _dispatch(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.service.pathDetected.emit(event.src_path)


class FolderWatchService(QObject):
    photosChanged = Signal()
    errorOccurred = Signal(str)
    pathDetected = Signal(str)

    def __init__(self, importer: PhotoImportService) -> None:
        super().__init__()
        self.importer = importer
        self.observer: Observer | None = None
        self.current_folder = Path()
        self.pathDetected.connect(self._process_path)

    def start(self, folder: str) -> None:
        self.stop()
        if not folder:
            self.current_folder = Path()
            self.photosChanged.emit()
            return

        self.current_folder = Path(folder)
        if not self.current_folder.exists():
            self.errorOccurred.emit("监听文件夹不存在。")
            self.photosChanged.emit()
            return

        self.importer.scan_folder(self.current_folder)
        self.photosChanged.emit()

        self.observer = Observer()
        handler = _WatchHandler(self)
        self.observer.schedule(handler, str(self.current_folder), recursive=False)
        self.observer.start()

    def stop(self) -> None:
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2)
            self.observer = None

    def _process_path(self, path_text: str) -> None:
        if self.importer.import_path(Path(path_text)):
            self.photosChanged.emit()
