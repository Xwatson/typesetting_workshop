from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from typesetting_workshop.services.layout import page_size_pixels  # noqa: E402
from typesetting_workshop.services.renderer import RendererService  # noqa: E402


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_render_calibration_page_matches_a4_size(self) -> None:
        renderer = RendererService()
        dpi = 300

        image = renderer.render_calibration_page(dpi)

        self.assertFalse(image.isNull())
        self.assertEqual((image.width(), image.height()), page_size_pixels(dpi))


if __name__ == "__main__":
    unittest.main()
