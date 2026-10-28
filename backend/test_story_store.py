import os, tempfile, unittest

class StoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['AGENT_FACTORY_DB'] = os.path.join(self.tmp.name, 'test.sqlite3')
        import story_store
        self.store = story_store
        self.store.init_story_db()
    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop('AGENT_FACTORY_DB', None)
    def test_character_and_story_persist_and_delete(self):
        character = self.store.save_character({'name':'Mina','appearance':'silver hair'})
        self.assertEqual(self.store.get_character(character['id'])['name'], 'Mina')
        story = self.store.save_story({'title':'First story','panels':[{'number':1,'prompt':'same look'}]})
        self.assertEqual(self.store.get_story(story['id'])['panels'][0]['prompt'], 'same look')
        self.assertTrue(self.store.delete_character(character['id']))
        self.assertTrue(self.store.delete_story(story['id']))
        self.assertIsNone(self.store.get_character(character['id']))

if __name__ == '__main__': unittest.main()
