from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typesetting_workshop.models import AppSettings, CropState  # noqa: E402
from typesetting_workshop.services.layout import PAGE_CAPACITY  # noqa: E402
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

    def test_pending_queries_support_posix_paths(self) -> None:
        self.repo.register_photo("/photos/a/1.jpg", "managed/a1.jpg", "md5-a1")
        self.repo.register_photo("/photos/a/2.jpg", "managed/a2.jpg", "md5-a2")
        self.repo.register_photo("/photos/b/1.jpg", "managed/b1.jpg", "md5-b1")

        batch = self.repo.get_current_batch("/photos/a")
        self.assertEqual(len(batch), 2)
        self.assertEqual(self.repo.count_pending("/photos/a"), 2)
        self.assertEqual(self.repo.count_pending("/photos/b"), 1)

    def test_clear_printed_only_removes_printed_records(self) -> None:
        self.repo.register_photo("/photos/a/1.jpg", "managed/a1.jpg", "md5-a1")
        self.repo.register_photo("/photos/a/2.jpg", "managed/a2.jpg", "md5-a2")
        self.repo.mark_printed(["md5-a1"])

        removed = self.repo.clear_printed()

        self.assertEqual(removed, 1)
        self.assertEqual(self.repo.count_printed(), 0)
        self.assertEqual(self.repo.count_pending("/photos/a"), 1)

    def test_current_batch_defaults_to_page_capacity(self) -> None:
        for index in range(PAGE_CAPACITY + 2):
            self.repo.register_photo(
                f"/photos/a/{index}.jpg",
                f"managed/{index}.jpg",
                f"md5-{index}",
            )

        batch = self.repo.get_current_batch("/photos/a")

        self.assertEqual(len(batch), PAGE_CAPACITY)

    def test_batch_page_includes_printed_records_and_supports_paging(self) -> None:
        for index in range(PAGE_CAPACITY + 1):
            self.repo.register_photo(
                f"/photos/a/{index}.jpg",
                f"managed/{index}.jpg",
                f"md5-page-{index}",
            )
        self.repo.mark_printed(["md5-page-0", "md5-page-1"])

        first_page = self.repo.get_batch_page("/photos/a", page_index=0)
        second_page = self.repo.get_batch_page("/photos/a", page_index=1)

        self.assertEqual(len(first_page), PAGE_CAPACITY)
        self.assertEqual(first_page[0].record.status, "printed")
        self.assertEqual(first_page[1].record.status, "printed")
        self.assertEqual(len(second_page), 1)
        self.assertEqual(second_page[0].slot_index, 0)

    def test_count_photos_and_printed_can_be_scoped_to_watch_folder(self) -> None:
        self.repo.register_photo(r"C:\photos\a\1.jpg", "managed/a1.jpg", "md5-a1")
        self.repo.register_photo(r"C:\photos\a\2.jpg", "managed/a2.jpg", "md5-a2")
        self.repo.register_photo(r"C:\photos\b\1.jpg", "managed/b1.jpg", "md5-b1")
        self.repo.mark_printed(["md5-a1", "md5-b1"])

        self.assertEqual(self.repo.count_photos(r"C:\photos\a"), 2)
        self.assertEqual(self.repo.count_printed(r"C:\photos\a"), 1)
        self.assertEqual(self.repo.count_printed(r"C:\photos\b"), 1)


if __name__ == "__main__":
    unittest.main()
