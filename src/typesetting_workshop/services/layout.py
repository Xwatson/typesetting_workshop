from __future__ import annotations

from dataclasses import dataclass

A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
IMAGE_DIAMETER_MM = 64.0
SAFE_AREA_DIAMETER_MM = 54.0
OUTER_DIAMETER_MM = 72.0
WHITE_MARGIN_PER_SIDE_MM = (OUTER_DIAMETER_MM - IMAGE_DIAMETER_MM) / 2.0
SLOT_SIZE_MM = OUTER_DIAMETER_MM
HALF_PAGE_WIDTH_MM = A4_WIDTH_MM / 2.0
CUT_GUIDE_OFFSET_MM = 0.0
COLUMN_GAP_MM = 10.0
ROW_GAP_MM = 10.0


def _fit_count(page_mm: float, slot_mm: float, gap_mm: float) -> int:
    count = int((page_mm + gap_mm) // (slot_mm + gap_mm))
    return max(1, count)


COLUMN_COUNT = _fit_count(A4_WIDTH_MM, SLOT_SIZE_MM, COLUMN_GAP_MM)
ROW_COUNT = _fit_count(A4_HEIGHT_MM, SLOT_SIZE_MM, ROW_GAP_MM)
PAGE_CAPACITY = COLUMN_COUNT * ROW_COUNT

CONTENT_HEIGHT_MM = ROW_COUNT * SLOT_SIZE_MM + (ROW_COUNT - 1) * ROW_GAP_MM
MARGIN_Y_MM = (A4_HEIGHT_MM - CONTENT_HEIGHT_MM) / 2.0


def build_column_positions() -> list[float]:
    if COLUMN_COUNT == 2:
        half_margin = (HALF_PAGE_WIDTH_MM - SLOT_SIZE_MM) / 2.0
        return [
            half_margin + CUT_GUIDE_OFFSET_MM,
            HALF_PAGE_WIDTH_MM + half_margin + CUT_GUIDE_OFFSET_MM,
        ]

    start_x = (A4_WIDTH_MM - (COLUMN_COUNT * SLOT_SIZE_MM + (COLUMN_COUNT - 1) * COLUMN_GAP_MM)) / 2.0
    return [
        start_x + column * (SLOT_SIZE_MM + COLUMN_GAP_MM)
        for column in range(COLUMN_COUNT)
    ]


COLUMN_X_POSITIONS_MM = build_column_positions()
CONTENT_WIDTH_MM = (COLUMN_X_POSITIONS_MM[-1] + SLOT_SIZE_MM) - COLUMN_X_POSITIONS_MM[0]
MARGIN_X_MM = COLUMN_X_POSITIONS_MM[0]
CUT_GUIDE_X_MM = HALF_PAGE_WIDTH_MM + CUT_GUIDE_OFFSET_MM


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
            x_mm = COLUMN_X_POSITIONS_MM[column]
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
