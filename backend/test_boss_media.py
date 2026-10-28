import base64
import io
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

import main


class FakeVisionGateway:
    last_user = ""

    async def generate_text(self, provider, api_key, system, user, model=None, base_url=None, image=None):
        assert image and image["mime"] == "image/jpeg"
        return "Ein roter Sportwagen vor einer nächtlichen Stadtkulisse."

    async def generate_json(self, provider, api_key, system, user, model=None, base_url=None, retries=1):
        FakeVisionGateway.last_user = user
        return {"reply": "Ich habe die Bildreferenz analysiert.", "workflow": "media", "category": "Cinematic Sportwagen-Clip", "next_step": "Video erzeugen"}


class BossMediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_image_attachment_is_analysed_and_used_as_video_reference(self):
        buffer = io.BytesIO()
        Image.new("RGB", (32, 32), (220, 30, 30)).save(buffer, format="PNG")
        data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        req = main.BossChatRequest(provider="openai", api_key="test-key", model="gpt-4o", message="Mach daraus einen kurzen Videoclip", attachments=[{"name": "car.png", "kind": "image", "type": "image/png", "data_url": data_url}])
        with patch.object(main, "LLMGateway", FakeVisionGateway):
            result = await main.boss_chat(req)
        self.assertIn("bildreferenz", result["reply"].lower())
        self.assertEqual(result["media_analysis"][0]["frames"][0]["summary"], "Ein roter Sportwagen vor einer nächtlichen Stadtkulisse.")
        self.assertTrue(result["video_reference_frame_data_url"].startswith("data:image/jpeg;base64,"))
        self.assertIn("nächtlichen Stadtkulisse", FakeVisionGateway.last_user)
        for attachment in result["attachments"]:
            path = main.BASE / "output" / "assets" / "boss-attachments" / Path(attachment["url"]).name
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
