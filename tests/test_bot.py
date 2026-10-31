import os
import tempfile
import unittest
from unittest.mock import patch

from bot.app import connect, polling_offset, process_update


def update(number, chat_id, text, chat_type="private"):
    return {"update_id": number, "message": {"chat": {"id": chat_id, "type": chat_type}, "text": text}}


class BotTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        self.addCleanup(self.db.close)

    def test_order_is_persisted_once_and_scoped_to_chat(self):
        response = process_update(self.db, update(1, 10, "/order 1"))
        self.assertIn("No payment was taken", response[1])
        self.assertIsNone(process_update(self.db, update(1, 10, "/order 1")))
        self.assertIn("Studio Headphones", process_update(self.db, update(2, 10, "/orders"))[1])
        self.assertEqual("You have no demo orders.", process_update(self.db, update(3, 11, "/orders"))[1])
        self.assertEqual(1, self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0])

    def test_invalid_order_and_group_do_not_create_orders(self):
        self.assertIn("Choose a product", process_update(self.db, update(1, 10, "/order 99"))[1])
        self.assertIsNone(process_update(self.db, update(2, 10, "/order 1", "group")))
        self.assertEqual(0, self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0])

    def test_catalog_and_cursor_survive_reconnection(self):
        self.assertIn("Classic Sunglasses", process_update(self.db, update(5, 10, "/catalog"))[1])
        self.assertEqual(6, self.db.execute("SELECT value FROM state WHERE key = 'offset'").fetchone()[0])
        self.assertIsNone(process_update(self.db, update(4, 10, "/order 1")))

    def test_database_file_is_private_and_rejects_public_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.sqlite3")
            db = connect(path)
            db.close()
            self.assertEqual(0, os.stat(path).st_mode & 0o077)
            os.chmod(path, 0o644)
            with self.assertRaises(PermissionError):
                connect(path)

    def test_idle_cursor_reset_accepts_a_lower_update_id(self):
        with patch("bot.app.time.time", return_value=1_000_000):
            process_update(self.db, update(100, 10, "/order 1"))
        with patch("bot.app.time.time", return_value=1_000_000 + 6 * 24 * 60 * 60):
            self.assertEqual(0, polling_offset(self.db))
            self.assertIn("Demo order placed", process_update(self.db, update(1, 10, "/order 2"))[1])
        self.assertEqual(2, self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
