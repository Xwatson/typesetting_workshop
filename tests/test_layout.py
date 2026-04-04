from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typesetting_workshop.services.layout import (  # noqa: E402
    A4_HEIGHT_MM,
    A4_WIDTH_MM,
    COLUMN_COUNT,
    COLUMN_GAP_MM,
    CONTENT_HEIGHT_MM,
    CONTENT_WIDTH_MM,
    MARGIN_X_MM,
    MARGIN_Y_MM,
    PAGE_CAPACITY,
    ROW_GAP_MM,
    ROW_COUNT,
    SLOTS,
)


class LayoutTests(unittest.TestCase):
    def test_capacity_is_six(self) -> None:
        self.assertEqual(PAGE_CAPACITY, 6)
        self.assertEqual(COLUMN_COUNT, 2)
        self.assertEqual(ROW_COUNT, 3)
        self.assertEqual(COLUMN_GAP_MM, 10.0)
        self.assertEqual(ROW_GAP_MM, 10.0)

    def test_content_is_centered_on_page(self) -> None:
        self.assertAlmostEqual(MARGIN_X_MM * 2 + CONTENT_WIDTH_MM, A4_WIDTH_MM)
        self.assertAlmostEqual(MARGIN_Y_MM * 2 + CONTENT_HEIGHT_MM, A4_HEIGHT_MM)

    def test_slots_are_stable(self) -> None:
        self.assertEqual(len(SLOTS), PAGE_CAPACITY)
        self.assertAlmostEqual(SLOTS[0].x_mm, 26.0)
        self.assertAlmostEqual(SLOTS[0].y_mm, 27.5)
        self.assertAlmostEqual(SLOTS[-1].x_mm, 110.0)
        self.assertAlmostEqual(SLOTS[-1].y_mm, 195.5)


if __name__ == "__main__":
    unittest.main()
