from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class AppSettings:
    watch_folder: str = ""
    printer_name: str | None = None
    export_dpi: int = 300


@dataclass(slots=True)
class CropState:
    zoom: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def clamped(self) -> "CropState":
        return CropState(
            zoom=min(max(self.zoom, 1.0), 4.0),
            offset_x=min(max(self.offset_x, -1.0), 1.0),
            offset_y=min(max(self.offset_y, -1.0), 1.0),
        )


@dataclass(slots=True)
class PhotoRecord:
    id: int
    source_path: str
    managed_path: str
    md5: str
    status: str
    discovered_at: datetime
    last_seen_at: datetime


@dataclass(slots=True)
class PlacedPhoto:
    slot_index: int
    record: PhotoRecord
    crop_state: CropState = field(default_factory=CropState)
