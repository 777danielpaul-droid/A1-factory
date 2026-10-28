import unittest
from services.media_generation import generate_speech, generate_video, generate_sound_effect, compose_video_audio


class MediaValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_speech_requires_key(self):
        with self.assertRaisesRegex(ValueError, "ElevenLabs-API-Key"):
            await generate_speech(api_key="", text="Hallo", voice_id="voice_123", model_id="eleven_multilingual_v2")

    async def test_speech_requires_text(self):
        with self.assertRaisesRegex(ValueError, "Text für die Sprachausgabe"):
            await generate_speech(api_key="dummy", text=" ", voice_id="voice_123", model_id="eleven_multilingual_v2")

    async def test_video_requires_key(self):
        with self.assertRaisesRegex(ValueError, "Replicate-API-Token"):
            await generate_video(api_key="", prompt="Eine Szene", model_slug="minimax/video-01")

    async def test_video_model_slug_must_be_owner_model(self):
        with self.assertRaisesRegex(ValueError, "Anbieter/Modell"):
            await generate_video(api_key="dummy", prompt="Eine Szene", model_slug="https://example.com")

    async def test_video_requires_prompt(self):
        with self.assertRaisesRegex(ValueError, "Beschreibung für das Video"):
            await generate_video(api_key="dummy", prompt=" ", model_slug="minimax/video-01")

    async def test_video_rejects_invalid_reference_image(self):
        with self.assertRaisesRegex(ValueError, "Referenzbild"):
            await generate_video(api_key="dummy", prompt="Eine Szene", model_slug="minimax/video-01", reference_image_data_url="not-a-data-url")

    async def test_sound_effect_requires_key(self):
        with self.assertRaisesRegex(ValueError, "ElevenLabs-API-Key"):
            await generate_sound_effect(api_key="", prompt="Lautes Katzenmiauen")

    async def test_sound_effect_requires_prompt(self):
        with self.assertRaisesRegex(ValueError, "Soundeffekt"):
            await generate_sound_effect(api_key="dummy", prompt=" ")

    def test_compose_rejects_non_factory_filenames(self):
        with self.assertRaisesRegex(ValueError, "Dateiname ist ungültig"):
            compose_video_audio(video_filename="../../secret.mp4", audio_filename="sound-" + "a" * 32 + ".mp3")


if __name__ == "__main__":
    unittest.main()
