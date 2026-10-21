"""Unit tests for AgnesClient using mocked responses."""

import unittest
from unittest.mock import MagicMock, patch

from video_gen.client import AgnesAPIError, AgnesClient, AgnesRateLimitError
from video_gen.config import PipelineConfig


class TestAgnesClient(unittest.TestCase):
    """Test AgnesClient HTTP methods and retry behavior."""

    def setUp(self) -> None:
        self.config = PipelineConfig(
            api_key="mock_dummy_key",
            base_url="https://apihub.agnes-ai.com/v1",
            max_retries=2,
            base_backoff_sec=0.01,
        )
        self.mock_session = MagicMock()
        self.client = AgnesClient(config=self.config, session=self.mock_session)

    def test_create_chat_completion_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Generated scene breakdown",
                    }
                }
            ]
        }
        self.mock_session.post.return_value = mock_response

        messages = [{"role": "user", "content": "Generate 3 scenes"}]
        result = self.client.create_chat_completion(messages=messages)

        self.assertEqual(result, "Generated scene breakdown")
        self.mock_session.post.assert_called_once()
        call_kwargs = self.mock_session.post.call_args.kwargs
        self.assertIn("Authorization", call_kwargs["headers"])
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer mock_dummy_key")
        self.assertEqual(call_kwargs["json"]["model"], "agnes-2.5-flash")

    def test_generate_image_text_to_image(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "url": "https://storage.googleapis.com/agnes-aigc/test_image.png",
                    "b64_json": None,
                }
            ]
        }
        self.mock_session.post.return_value = mock_response

        url = self.client.generate_image(prompt="Cybernetic tiger in neon rain")
        self.assertEqual(url, "https://storage.googleapis.com/agnes-aigc/test_image.png")

        call_kwargs = self.mock_session.post.call_args.kwargs
        payload = call_kwargs["json"]
        self.assertEqual(payload["model"], "agnes-image-2.0-flash")
        self.assertEqual(payload["size"], "1024x768")
        self.assertEqual(payload["extra_body"]["response_format"], "url")
        self.assertNotIn("image", payload["extra_body"])

    def test_generate_image_with_reference(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"url": "https://storage.googleapis.com/agnes-aigc/frame_2.png"}
            ]
        }
        self.mock_session.post.return_value = mock_response

        ref_url = "https://storage.googleapis.com/agnes-aigc/frame_1.png"
        url = self.client.generate_image(
            prompt="Tiger leaping forward",
            reference_images=[ref_url],
        )
        self.assertEqual(url, "https://storage.googleapis.com/agnes-aigc/frame_2.png")

        payload = self.mock_session.post.call_args.kwargs["json"]
        self.assertEqual(payload["extra_body"]["image"], [ref_url])

    def test_rate_limit_retry_and_recovery(self) -> None:
        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Recovered"}}]
        }

        self.mock_session.post.side_effect = [rate_limited, success]

        result = self.client.create_chat_completion(messages=[{"role": "user", "content": "hi"}])
        self.assertEqual(result, "Recovered")
        self.assertEqual(self.mock_session.post.call_count, 2)

    def test_rate_limit_exhausted_raises_error(self) -> None:
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        self.mock_session.post.return_value = rate_limited

        with self.assertRaises(AgnesRateLimitError):
            self.client.create_chat_completion(messages=[{"role": "user", "content": "hi"}])

    def test_unrecoverable_400_error(self) -> None:
        bad_req = MagicMock()
        bad_req.status_code = 400
        bad_req.json.return_value = {"error": {"message": "Invalid parameter"}}
        self.mock_session.post.return_value = bad_req

        with self.assertRaises(AgnesAPIError) as ctx:
            self.client.generate_image(prompt="test")
        self.assertIn("Invalid parameter", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
