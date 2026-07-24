import unittest
from io import BytesIO
from urllib.parse import urlparse
from unittest.mock import patch

from PIL import Image

from app import create_app


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP error {self.status_code}")


def _make_png_bytes(size=(100, 100), color=(255, 0, 0, 255)):
    img = Image.new("RGBA", size, color)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img.close()
    return buffer.getvalue()


class ImageProcessEndpointTests(unittest.TestCase):
    def setUp(self):
        with patch("app._preload_model", return_value=None):
            self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.url = "/api/v1/image/image-process"
        self.headers = {"X-API-KEY": "Bearer test_token_for_testing_only"}

    @patch("app.routes.image._remove_background")
    @patch("app.routes.image.requests.get")
    def test_image_process_returns_download_url(self, mock_get, mock_remove_background):
        original_bytes = _make_png_bytes(size=(80, 80), color=(255, 0, 0, 255))
        background_bytes = _make_png_bytes(size=(300, 180), color=(0, 255, 0, 255))

        mock_get.side_effect = [
            FakeResponse(original_bytes, headers={"Content-Length": str(len(original_bytes))}),
            FakeResponse(background_bytes, headers={"Content-Length": str(len(background_bytes))}),
        ]

        mock_remove_background.side_effect = lambda image: image

        response = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner-final.jpg",
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("download_url", payload)
        self.assertIn("expires_at", payload)
        self.assertIn("render_metadata", payload)
        self.assertEqual(payload["filename"], "banner-final.png")
        self.assertEqual(
            payload["render_metadata"]["output_subject_size"],
            {"width": 169, "height": 169},
        )

        download_path = urlparse(payload["download_url"]).path
        download_response = self.client.get(download_path)
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.headers.get("Content-Type"), "image/png")

        output_image = Image.open(BytesIO(download_response.data))
        self.assertEqual(output_image.size, (300, 180))
        output_image.close()
        download_response.close()

    @patch("app.routes.image.VALIDATE_HTTPS_URL", True)
    def test_image_process_rejects_non_https_url_when_enabled(self):
        response = self.client.post(
            self.url,
            json={
                "imageUrl": "http://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner.png",
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertIn("https", payload["message"].lower())

    def test_image_process_requires_api_key(self):
        response = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner.png",
            },
        )

        self.assertEqual(response.status_code, 401)

    @patch("app.routes.image.requests.get")
    def test_image_process_rejects_large_remote_file(self, mock_get):
        tiny_png = _make_png_bytes(size=(10, 10))
        mock_get.return_value = FakeResponse(
            tiny_png,
            headers={"Content-Length": str((10 * 1024 * 1024) + 1)},
        )

        response = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner.png",
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 413)
        payload = response.get_json()
        self.assertFalse(payload["success"])

    @patch("app.routes.image._remove_background")
    @patch("app.routes.image.requests.get")
    def test_image_process_clamps_scale_to_max(self, mock_get, mock_remove_background):
        original_bytes = _make_png_bytes(size=(80, 80), color=(255, 0, 0, 255))
        background_bytes = _make_png_bytes(size=(300, 180), color=(0, 255, 0, 255))

        mock_get.side_effect = [
            FakeResponse(original_bytes, headers={"Content-Length": str(len(original_bytes))}),
            FakeResponse(background_bytes, headers={"Content-Length": str(len(background_bytes))}),
        ]
        mock_remove_background.side_effect = lambda image: image

        response = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner-final.jpg",
                "scalePercent": 200,
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["render_metadata"]["scale_requested_percent"], 200.0)
        self.assertEqual(payload["render_metadata"]["scale_applied_percent"], 100.0)
        self.assertEqual(
            payload["render_metadata"]["output_subject_size"],
            {"width": 180, "height": 180},
        )

    @patch("app.routes.image._remove_background")
    @patch("app.routes.image.requests.get")
    def test_image_process_padding_reduces_subject_size(self, mock_get, mock_remove_background):
        original_bytes = _make_png_bytes(size=(80, 80), color=(255, 0, 0, 255))
        background_bytes = _make_png_bytes(size=(300, 180), color=(0, 255, 0, 255))

        mock_get.side_effect = [
            FakeResponse(original_bytes, headers={"Content-Length": str(len(original_bytes))}),
            FakeResponse(background_bytes, headers={"Content-Length": str(len(background_bytes))}),
            FakeResponse(original_bytes, headers={"Content-Length": str(len(original_bytes))}),
            FakeResponse(background_bytes, headers={"Content-Length": str(len(background_bytes))}),
        ]
        mock_remove_background.side_effect = lambda image: image

        response_no_padding = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner-final.jpg",
                "paddingPercent": 0,
                "scalePercent": 100,
            },
            headers=self.headers,
        )
        response_with_padding = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner-final.jpg",
                "paddingPercent": 20,
                "scalePercent": 100,
            },
            headers=self.headers,
        )

        self.assertEqual(response_no_padding.status_code, 200)
        self.assertEqual(response_with_padding.status_code, 200)

        payload_no_padding = response_no_padding.get_json()
        payload_with_padding = response_with_padding.get_json()

        size_no_padding = payload_no_padding["render_metadata"]["output_subject_size"]["height"]
        size_with_padding = payload_with_padding["render_metadata"]["output_subject_size"]["height"]

        self.assertGreater(size_no_padding, size_with_padding)

    @patch("app.routes.image._remove_background")
    @patch("app.routes.image.requests.get")
    def test_image_process_center_bottom_alignment(self, mock_get, mock_remove_background):
        original_bytes = _make_png_bytes(size=(80, 80), color=(255, 0, 0, 255))
        background_bytes = _make_png_bytes(size=(300, 180), color=(0, 255, 0, 255))

        mock_get.side_effect = [
            FakeResponse(original_bytes, headers={"Content-Length": str(len(original_bytes))}),
            FakeResponse(background_bytes, headers={"Content-Length": str(len(background_bytes))}),
        ]
        mock_remove_background.side_effect = lambda image: image

        response = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner-bottom.png",
                "paddingPercent": 0,
                "scalePercent": 80,
                "horizontalAlign": "center",
                "verticalAlign": "bottom",
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["render_metadata"]["position"], {"x": 78, "y": 36})

    @patch("app.routes.image._remove_background")
    @patch("app.routes.image.requests.get")
    def test_image_process_percent_offset_is_applied(self, mock_get, mock_remove_background):
        original_bytes = _make_png_bytes(size=(80, 80), color=(255, 0, 0, 255))
        background_bytes = _make_png_bytes(size=(300, 180), color=(0, 255, 0, 255))

        mock_get.side_effect = [
            FakeResponse(original_bytes, headers={"Content-Length": str(len(original_bytes))}),
            FakeResponse(background_bytes, headers={"Content-Length": str(len(background_bytes))}),
        ]
        mock_remove_background.side_effect = lambda image: image

        response = self.client.post(
            self.url,
            json={
                "imageUrl": "https://example.com/original.png",
                "backgroundUrl": "https://example.com/background.png",
                "outputFilename": "banner-offset.png",
                "paddingPercent": 0,
                "scalePercent": 80,
                "horizontalAlign": "center",
                "verticalAlign": "center",
                "offsetX": 10,
                "offsetY": -10,
                "offsetUnit": "percent",
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["render_metadata"]["offset"]["applied_x_px"], 30)
        self.assertEqual(payload["render_metadata"]["offset"]["applied_y_px"], -18)


if __name__ == "__main__":
    unittest.main()
