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

    def test_create_video_task_text_mode(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "task_12345",
            "video_id": "video_12345",
            "task_id": "task_12345",
            "status": "queued",
        }
        self.mock_session.post.return_value = mock_response

        res = self.client.create_video_task(
            prompt="Futuristic city with flying vehicles",
            seconds="6",
            size="1080P",
            aspect_ratio="16:9",
        )

        self.assertEqual(res["video_id"], "video_12345")
        self.assertEqual(res["status"], "queued")
        call_kwargs = self.mock_session.post.call_args.kwargs
        self.assertEqual(call_kwargs["json"]["model"], "agnes-video-2.5")
        self.assertEqual(call_kwargs["json"]["mode"], "text")
        self.assertEqual(call_kwargs["json"]["seconds"], "6")
        self.assertEqual(call_kwargs["json"]["size"], "1080P")

    def test_create_video_task_keyframe_mode(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "task_kf",
            "video_id": "video_kf",
            "status": "queued",
        }
        self.mock_session.post.return_value = mock_response

        res = self.client.create_video_task(
            prompt="Transition from day to night",
            mode="keyframe",
            first_frame="https://example.com/day.png",
            last_frame="https://example.com/night.png",
        )
        self.assertEqual(res["video_id"], "video_kf")
        call_kwargs = self.mock_session.post.call_args.kwargs
        self.assertEqual(call_kwargs["json"]["first_frame"], "https://example.com/day.png")
        self.assertEqual(call_kwargs["json"]["last_frame"], "https://example.com/night.png")

    def test_get_video_task(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "task_999",
            "status": "in_progress",
            "progress": 55,
            "url": None,
        }
        self.mock_session.get.return_value = mock_response

        status_info = self.client.get_video_task(video_id="video_999")
        self.assertEqual(status_info["status"], "in_progress")
        self.assertEqual(status_info["progress"], 55)

        call_kwargs = self.mock_session.get.call_args.kwargs
        self.assertIn("agnesapi", call_kwargs["url"])
        self.assertEqual(call_kwargs["params"]["video_id"], "video_999")
        self.assertEqual(call_kwargs["params"]["model_name"], "agnes-video-2.5")

    def test_wait_for_video_success(self) -> None:
        resp_pending = MagicMock()
        resp_pending.status_code = 200
        resp_pending.json.return_value = {"status": "in_progress", "progress": 50, "url": None}

        resp_done = MagicMock()
        resp_done.status_code = 200
        resp_done.json.return_value = {
            "status": "completed",
            "progress": 100,
            "url": "https://storage.googleapis.com/agnes/clip.mp4",
        }
        self.mock_session.get.side_effect = [resp_pending, resp_done]

        res = self.client.wait_for_video(video_id="video_abc", poll_interval=0.01, timeout_seconds=5)
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["url"], "https://storage.googleapis.com/agnes/clip.mp4")

    def test_wait_for_video_failed(self) -> None:
        resp_failed = MagicMock()
        resp_failed.status_code = 200
        resp_failed.json.return_value = {
            "status": "failed",
            "progress": 0,
            "error": {"message": "GPU generation out of memory"},
        }
        self.mock_session.get.return_value = resp_failed

    def test_create_video_task_quota_error_provides_zero_cost_hint(self) -> None:
        quota_err = MagicMock()
        quota_err.status_code = 403
        quota_err.json.return_value = {
            "code": "insufficient_user_quota",
            "message": "Insufficient user quota, remaining: $0.000000",
            "data": None,
        }
        self.mock_session.post.return_value = quota_err

        with self.assertRaises(AgnesAPIError) as ctx:
            self.client.create_video_task(prompt="test prompt")

        self.assertIn("Insufficient account quota for Agnes Video 2.5", str(ctx.exception))
        self.assertIn("Zero-Cost Pipeline", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
