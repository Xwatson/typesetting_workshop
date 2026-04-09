from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typesetting_workshop.services.layout import (  # noqa: E402
    A4_HEIGHT_MM,
    A4_WIDTH_MM,
    COLUMN_COUNT,
    COLUMN_GAP_MM,
    COLUMN_X_POSITIONS_MM,
    CONTENT_HEIGHT_MM,
    CONTENT_WIDTH_MM,
    CUT_GUIDE_OFFSET_MM,
    CUT_GUIDE_X_MM,
    HALF_PAGE_WIDTH_MM,
    IMAGE_DIAMETER_MM,
    MARGIN_X_MM,
    MARGIN_Y_MM,
    OUTER_DIAMETER_MM,
    PAGE_CAPACITY,
    ROW_GAP_MM,
    ROW_COUNT,
    SAFE_AREA_DIAMETER_MM,
    SLOT_SIZE_MM,
    SLOTS,
    WHITE_MARGIN_PER_SIDE_MM,
)


class LayoutTests(unittest.TestCase):
    def test_capacity_is_six(self) -> None:
        self.assertEqual(PAGE_CAPACITY, 6)
        self.assertEqual(COLUMN_COUNT, 2)
        self.assertEqual(ROW_COUNT, 3)
        self.assertEqual(IMAGE_DIAMETER_MM, 64.0)
        self.assertEqual(SAFE_AREA_DIAMETER_MM, 54.0)
        self.assertEqual(OUTER_DIAMETER_MM, 72.0)
        self.assertEqual(WHITE_MARGIN_PER_SIDE_MM, 4.0)
        self.assertEqual(SLOT_SIZE_MM, 72.0)
        self.assertEqual(CUT_GUIDE_OFFSET_MM, 0.0)
        self.assertEqual(COLUMN_GAP_MM, 10.0)
        self.assertEqual(ROW_GAP_MM, 10.0)

    def test_content_is_centered_on_page(self) -> None:
        self.assertAlmostEqual(MARGIN_Y_MM * 2 + CONTENT_HEIGHT_MM, A4_HEIGHT_MM)

    def test_each_column_is_centered_in_half_page(self) -> None:
        left_center = COLUMN_X_POSITIONS_MM[0] + SLOT_SIZE_MM / 2.0
        right_center = COLUMN_X_POSITIONS_MM[1] + SLOT_SIZE_MM / 2.0
        self.assertAlmostEqual(left_center, HALF_PAGE_WIDTH_MM / 2.0 + CUT_GUIDE_OFFSET_MM)
        self.assertAlmostEqual(right_center, HALF_PAGE_WIDTH_MM + HALF_PAGE_WIDTH_MM / 2.0 + CUT_GUIDE_OFFSET_MM)
        self.assertAlmostEqual(CUT_GUIDE_X_MM, HALF_PAGE_WIDTH_MM + CUT_GUIDE_OFFSET_MM)

    def test_slots_are_stable(self) -> None:
        self.assertEqual(len(SLOTS), PAGE_CAPACITY)
        self.assertAlmostEqual(SLOTS[0].x_mm, 16.5)
        self.assertAlmostEqual(SLOTS[0].y_mm, 30.5)
        self.assertAlmostEqual(SLOTS[-1].x_mm, 121.5)
        self.assertAlmostEqual(SLOTS[-1].y_mm, 194.5)


if __name__ == "__main__":
    unittest.main()
