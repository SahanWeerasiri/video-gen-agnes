"""Unit tests for the Flask web application in src/video_gen/server.py."""

import json
import unittest
from unittest.mock import MagicMock, patch

from video_gen.config import PipelineConfig
from video_gen.server import create_app


class TestServer(unittest.TestCase):
    """Test Flask routes and API endpoints."""

    def setUp(self) -> None:
        self.config = PipelineConfig(
            api_key="mock_key_12345",
            base_url="https://apihub.agnes-ai.com/v1",
        )
        self.app = create_app(config=self.config)
        self.client = self.app.test_client()

    def test_index_route(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Agnes Studio", response.data)

    def test_get_config(self) -> None:
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["has_api_key"])
        self.assertIn("mock...2345", data["masked_key"])
        self.assertEqual(data["text_model"], "agnes-2.5-flash")
        self.assertEqual(data["image_model"], "agnes-image-2.0-flash")

    def test_generate_missing_prompt(self) -> None:
        response = self.client.post(
            "/api/generate",
            data=json.dumps({"prompt": "   "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Prompt is required", response.get_json()["error"])

    @patch("threading.Thread.start")
    def test_generate_valid_prompt_queues_task(self, mock_start: MagicMock) -> None:
        response = self.client.post(
            "/api/generate",
            data=json.dumps({
                "prompt": "Cyberpunk city at night",
                "scenes": 2,
                "duration": 3.0,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 202)
        data = response.get_json()
        self.assertIn("task_id", data)
        self.assertEqual(data["status"], "queued")
        mock_start.assert_called_once()

    def test_get_unknown_task_returns_404(self) -> None:
        response = self.client.get("/api/task/non-existent-task-id")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
