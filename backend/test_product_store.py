import tempfile
import unittest
from pathlib import Path

import product_store


class ProductStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        product_store.DB_PATH = Path(self.tmp.name) / "test.sqlite3"
        product_store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_read_update_delete(self):
        created = product_store.save_product({"id": 123, "title": "Original", "price": 12.5, "tags": ["a"]})
        self.assertEqual(created["id"], "123")
        self.assertEqual(product_store.get_product("123")["title"], "Original")
        updated = product_store.update_product("123", {"title": "Updated", "price": 15})
        self.assertEqual(updated["title"], "Updated")
        self.assertEqual(updated["price"], 15)
        self.assertEqual(updated["tags"], ["a"])
        self.assertTrue(product_store.delete_product("123"))
        self.assertIsNone(product_store.get_product("123"))
        self.assertFalse(product_store.delete_product("123"))

    def test_persists_after_reopen(self):
        product_store.save_product({"id": "persist-me", "title": "Saved"})
        self.assertEqual(product_store.list_products()[0]["title"], "Saved")


if __name__ == "__main__":
    unittest.main()
