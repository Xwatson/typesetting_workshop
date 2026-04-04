from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from typesetting_workshop.models import AppSettings, CropState, PhotoRecord, PlacedPhoto


class QueueRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = db_path
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            db_target = str(self.db_path)
        else:
            db_target = self.db_path
        self.connection = sqlite3.connect(db_target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = MEMORY")
        self.connection.execute("PRAGMA temp_store = MEMORY")
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    managed_path TEXT NOT NULL,
                    md5 TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'printed')),
                    discovered_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS crop_states (
                    photo_md5 TEXT PRIMARY KEY,
                    zoom REAL NOT NULL,
                    offset_x REAL NOT NULL,
                    offset_y REAL NOT NULL,
                    FOREIGN KEY(photo_md5) REFERENCES photos(md5) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_photos_status_discovered
                ON photos(status, discovered_at);
                """
            )

    def load_settings(self) -> AppSettings:
        with self._connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        values = {row["key"]: row["value"] for row in rows}
        printer_name = values.get("printer_name") or None
        export_dpi = int(values.get("export_dpi", "300"))
        return AppSettings(
            watch_folder=values.get("watch_folder", ""),
            printer_name=printer_name,
            export_dpi=export_dpi,
        )

    def save_settings(self, settings: AppSettings) -> None:
        items = {
            "watch_folder": settings.watch_folder,
            "printer_name": settings.printer_name or "",
            "export_dpi": str(settings.export_dpi),
        }
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO settings(key, value)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                items.items(),
            )

    def register_photo(self, source_path: str, managed_path: str, md5: str) -> bool:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT md5 FROM photos WHERE md5 = ?",
                (md5,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE photos
                    SET source_path = ?, last_seen_at = ?
                    WHERE md5 = ?
                    """,
                    (source_path, now, md5),
                )
                return False

            connection.execute(
                """
                INSERT INTO photos(source_path, managed_path, md5, status, discovered_at, last_seen_at)
                VALUES(?, ?, ?, 'pending', ?, ?)
                """,
                (source_path, managed_path, md5, now, now),
            )
            connection.execute(
                """
                INSERT INTO crop_states(photo_md5, zoom, offset_x, offset_y)
                VALUES(?, 1.0, 0.0, 0.0)
                """,
                (md5,),
            )
            return True

    def get_current_batch(self, limit: int = 6) -> list[PlacedPhoto]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.source_path,
                    p.managed_path,
                    p.md5,
                    p.status,
                    p.discovered_at,
                    p.last_seen_at,
                    c.zoom,
                    c.offset_x,
                    c.offset_y
                FROM photos p
                INNER JOIN crop_states c ON c.photo_md5 = p.md5
                WHERE p.status = 'pending'
                ORDER BY p.discovered_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        placed: list[PlacedPhoto] = []
        for index, row in enumerate(rows):
            placed.append(
                PlacedPhoto(
                    slot_index=index,
                    record=PhotoRecord(
                        id=row["id"],
                        source_path=row["source_path"],
                        managed_path=row["managed_path"],
                        md5=row["md5"],
                        status=row["status"],
                        discovered_at=datetime.fromisoformat(row["discovered_at"]),
                        last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
                    ),
                    crop_state=CropState(
                        zoom=row["zoom"],
                        offset_x=row["offset_x"],
                        offset_y=row["offset_y"],
                    ),
                )
            )
        return placed

    def count_pending(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM photos WHERE status = 'pending'"
            ).fetchone()
        return int(row["count"])

    def save_crop_state(self, md5: str, crop_state: CropState) -> None:
        normalized = crop_state.clamped()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE crop_states
                SET zoom = ?, offset_x = ?, offset_y = ?
                WHERE photo_md5 = ?
                """,
                (normalized.zoom, normalized.offset_x, normalized.offset_y, md5),
            )

    def mark_printed(self, md5_values: list[str]) -> None:
        if not md5_values:
            return
        placeholders = ",".join("?" for _ in md5_values)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE photos SET status = 'printed' WHERE md5 IN ({placeholders})",
                md5_values,
            )

    def close(self) -> None:
        self.connection.close()
