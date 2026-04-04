from __future__ import annotations

from dataclasses import dataclass

A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
SLOT_SIZE_MM = 74.0
COLUMN_GAP_MM = 10.0
ROW_GAP_MM = 10.0
COLUMN_COUNT = 2
ROW_COUNT = 3
PAGE_CAPACITY = COLUMN_COUNT * ROW_COUNT

CONTENT_WIDTH_MM = COLUMN_COUNT * SLOT_SIZE_MM + (COLUMN_COUNT - 1) * COLUMN_GAP_MM
CONTENT_HEIGHT_MM = ROW_COUNT * SLOT_SIZE_MM + (ROW_COUNT - 1) * ROW_GAP_MM
MARGIN_X_MM = (A4_WIDTH_MM - CONTENT_WIDTH_MM) / 2.0
MARGIN_Y_MM = (A4_HEIGHT_MM - CONTENT_HEIGHT_MM) / 2.0


@dataclass(frozen=True, slots=True)
class LayoutSlot:
    slot_index: int
    row: int
    column: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


def mm_to_pixels(value_mm: float, dpi: int) -> int:
    return round((value_mm / 25.4) * dpi)


def page_size_pixels(dpi: int) -> tuple[int, int]:
    return mm_to_pixels(A4_WIDTH_MM, dpi), mm_to_pixels(A4_HEIGHT_MM, dpi)


def build_slots() -> list[LayoutSlot]:
    slots: list[LayoutSlot] = []
    for row in range(ROW_COUNT):
        for column in range(COLUMN_COUNT):
            slot_index = row * COLUMN_COUNT + column
            x_mm = MARGIN_X_MM + column * (SLOT_SIZE_MM + COLUMN_GAP_MM)
            y_mm = MARGIN_Y_MM + row * (SLOT_SIZE_MM + ROW_GAP_MM)
            slots.append(
                LayoutSlot(
                    slot_index=slot_index,
                    row=row,
                    column=column,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    width_mm=SLOT_SIZE_MM,
                    height_mm=SLOT_SIZE_MM,
                )
            )
    return slots


SLOTS = build_slots()
