from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typesetting_workshop.models import AppSettings, CropState  # noqa: E402
from typesetting_workshop.services.repository import QueueRepository  # noqa: E402


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = QueueRepository(":memory:")

    def tearDown(self) -> None:
        self.repo.close()

    def test_settings_round_trip(self) -> None:
        settings = AppSettings(watch_folder="/tmp/inbox", printer_name="Printer A", export_dpi=300)
        self.repo.save_settings(settings)
        loaded = self.repo.load_settings()
        self.assertEqual(loaded.watch_folder, settings.watch_folder)
        self.assertEqual(loaded.printer_name, settings.printer_name)
        self.assertEqual(loaded.export_dpi, settings.export_dpi)

    def test_register_photo_deduplicates_by_md5(self) -> None:
        inserted_first = self.repo.register_photo("a.jpg", "managed/a.jpg", "same-md5")
        inserted_second = self.repo.register_photo("b.jpg", "managed/b.jpg", "same-md5")
        batch = self.repo.get_current_batch()

        self.assertTrue(inserted_first)
        self.assertFalse(inserted_second)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0].record.source_path, "b.jpg")

    def test_crop_state_and_mark_printed(self) -> None:
        self.repo.register_photo("a.jpg", "managed/a.jpg", "md5-1")
        self.repo.save_crop_state("md5-1", CropState(zoom=2.2, offset_x=0.5, offset_y=-0.25))
        batch = self.repo.get_current_batch()
        self.assertEqual(batch[0].crop_state.zoom, 2.2)

        self.repo.mark_printed(["md5-1"])
        self.assertEqual(self.repo.count_pending(), 0)

    def test_pending_queries_are_scoped_to_watch_folder(self) -> None:
        self.repo.register_photo(r"C:\photos\a\1.jpg", "managed/a1.jpg", "md5-a1")
        self.repo.register_photo(r"C:\photos\a\2.jpg", "managed/a2.jpg", "md5-a2")
        self.repo.register_photo(r"C:\photos\b\1.jpg", "managed/b1.jpg", "md5-b1")

        batch = self.repo.get_current_batch(r"C:\photos\a")
        self.assertEqual(len(batch), 2)
        self.assertEqual(self.repo.count_pending(r"C:\photos\a"), 2)
        self.assertEqual(self.repo.count_pending(r"C:\photos\b"), 1)

    def test_clear_pending_only_clears_current_folder(self) -> None:
        self.repo.register_photo(r"C:\photos\a\1.jpg", "managed/a1.jpg", "md5-a1")
        self.repo.register_photo(r"C:\photos\b\1.jpg", "managed/b1.jpg", "md5-b1")

        removed = self.repo.clear_pending(r"C:\photos\a")

        self.assertEqual(removed, 1)
        self.assertEqual(self.repo.count_pending(r"C:\photos\a"), 0)
        self.assertEqual(self.repo.count_pending(r"C:\photos\b"), 1)


if __name__ == "__main__":
    unittest.main()
