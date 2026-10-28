import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import game_asset_store


class GameAssetStoreTests(unittest.TestCase):
    def test_save_list_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'assets.sqlite3'
            with patch.object(game_asset_store, 'DB_PATH', db):
                game_asset_store.init_game_asset_db()
                item = game_asset_store.save_game_asset({
                    'name': 'Slime', 'prompt': 'green slime', 'asset_type': 'sprite',
                    'width': 64, 'height': 64, 'transparent': True, 'provider': 'pixellab',
                    'image_url': '/static/assets/pixellab_test.png'
                })
                listed = game_asset_store.list_game_assets()
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]['id'], item['id'])
                self.assertTrue(listed[0]['transparent'])
                self.assertEqual(game_asset_store.delete_game_asset(item['id']), '/static/assets/pixellab_test.png')
                self.assertEqual(game_asset_store.list_game_assets(), [])


if __name__ == '__main__':
    unittest.main()
