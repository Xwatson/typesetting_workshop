from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image  # noqa: E402

from typesetting_workshop.services.importer import PhotoImportService  # noqa: E402
from typesetting_workshop.services.repository import QueueRepository  # noqa: E402


class ImporterTests(unittest.TestCase):
    def test_cleared_printed_photos_can_be_imported_again(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            watch_folder = root / "watch"
            managed_folder = root / "managed"
            database_path = root / "queue.sqlite3"
            watch_folder.mkdir()

            photo_path = watch_folder / "sample.png"
            Image.new("RGB", (32, 32), "red").save(photo_path)

            repository = QueueRepository(database_path)
            try:
                importer = PhotoImportService(repository, managed_folder)

                imported_first = importer.scan_folder(watch_folder)
                self.assertEqual(imported_first, 1)
                self.assertEqual(repository.count_pending(str(watch_folder)), 1)

                batch = repository.get_current_batch(str(watch_folder))
                repository.mark_printed([item.record.md5 for item in batch])
                self.assertEqual(repository.count_printed(), 1)

                removed = repository.clear_printed()
                self.assertEqual(removed, 1)
                self.assertEqual(repository.count_printed(), 0)

                imported_again = importer.scan_folder(watch_folder)
                self.assertEqual(imported_again, 1)
                self.assertEqual(repository.count_pending(str(watch_folder)), 1)
            finally:
                repository.close()


if __name__ == "__main__":
    unittest.main()
