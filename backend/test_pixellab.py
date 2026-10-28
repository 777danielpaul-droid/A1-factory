import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image

from services.pixellab import PixelLabClient, PixelLabError


def tiny_png_b64():
    out = io.BytesIO()
    Image.new('RGBA', (2, 2), (255, 0, 0, 255)).save(out, format='PNG')
    return base64.b64encode(out.getvalue()).decode()


class PixelLabClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_image_response_is_saved_as_png(self):
        b64 = tiny_png_b64()
        async def handler(request):
            self.assertEqual(request.url.path, '/v2/create-image-pixen')
            self.assertEqual(request.headers['authorization'], 'Bearer test-token')
            return httpx.Response(200, json={'image': {'type': 'base64', 'base64': b64}})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch('services.pixellab.ASSET_DIR', Path(tempfile.mkdtemp())):
            path = await PixelLabClient('test-token', client).generate('tiny sprite', 32, 32)
            self.assertTrue(path.exists())
            with Image.open(path) as image:
                self.assertEqual(image.format, 'PNG')
        await client.aclose()

    async def test_async_job_is_polled_until_completed(self):
        b64 = tiny_png_b64()
        async def handler(request):
            if request.url.path == '/v2/create-image-pixen':
                return httpx.Response(202, json={'background_job_id': 'job-123', 'status': 'processing'})
            if request.url.path == '/v2/background-jobs/job-123':
                return httpx.Response(200, json={'status': 'completed', 'last_response': {'images': [{'base64': b64}]}})
            return httpx.Response(404)
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch('services.pixellab.ASSET_DIR', Path(tempfile.mkdtemp())), patch('services.pixellab.asyncio.sleep', new=AsyncMock()):
            path = await PixelLabClient('test-token', client).generate('tiny sprite')
            self.assertTrue(path.exists())
        await client.aclose()


    async def test_reference_image_uses_image_to_pixelart_endpoint(self):
        b64 = tiny_png_b64()
        async def handler(request):
            self.assertEqual(request.url.path, '/v2/image-to-pixelart')
            body = __import__('json').loads(request.content)
            self.assertIn('image', body)
            self.assertIn('base64', body['image'])
            return httpx.Response(200, json={'image': {'type': 'base64', 'base64': b64}})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        reference = {'mime': 'image/png', 'b64': b64}
        with patch('services.pixellab.ASSET_DIR', Path(tempfile.mkdtemp())):
            path = await PixelLabClient('test-token', client).generate('convert my sprite', 32, 32, reference=reference)
            self.assertTrue(path.exists())
        await client.aclose()

    async def test_auth_failure_has_clear_message(self):
        async def handler(request):
            return httpx.Response(401, text='unauthorized')
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with self.assertRaisesRegex(PixelLabError, 'API-Key'):
            await PixelLabClient('bad-token', client).generate('sprite')
        await client.aclose()

    async def test_missing_key_is_rejected(self):
        with self.assertRaisesRegex(PixelLabError, 'API-Key'):
            PixelLabClient(' ')


if __name__ == '__main__':
    unittest.main()
