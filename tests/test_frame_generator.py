"""Unit tests for FrameGenerator."""

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from video_gen.frame_generator import FrameGenerator
from video_gen.storyboard import Scene, Storyboard


class TestFrameGenerator(unittest.TestCase):
    """Test frame generation and sequential continuity anchoring."""

    def setUp(self) -> None:
        self.mock_client = MagicMock()
        self.mock_session = MagicMock()
        self.generator = FrameGenerator(client=self.mock_client, session=self.mock_session)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generate_frames_with_continuity(self) -> None:
        storyboard = Storyboard(
            title="Cyber City",
            summary="Test",
            scenes=[
                Scene(index=1, description="Wide shot", visual_prompt="Prompt 1"),
                Scene(index=2, description="Medium shot", visual_prompt="Prompt 2"),
            ],
        )

        frame1_url = "https://mock.storage/frame1.png"
        frame2_url = "https://mock.storage/frame2.png"
        self.mock_client.generate_image.side_effect = [frame1_url, frame2_url]

        # Mock session download response
        mock_download_resp = MagicMock()
        mock_download_resp.status_code = 200
        mock_download_resp.content = b"fake-png-bytes"
        self.mock_session.get.return_value = mock_download_resp

        progress_calls = []

        frames = self.generator.generate_frames(
            storyboard=storyboard,
            output_dir=self.output_dir,
            use_continuity=True,
            on_progress=lambda current, total: progress_calls.append((current, total)),
        )

        self.assertEqual(len(frames), 2)
        self.assertEqual(progress_calls, [(1, 2), (2, 2)])

        # First call: no reference images
        first_call_kwargs = self.mock_client.generate_image.call_args_list[0].kwargs
        self.assertIsNone(first_call_kwargs["reference_images"])

        # Second call: uses first frame as reference for visual continuity
        second_call_kwargs = self.mock_client.generate_image.call_args_list[1].kwargs
        self.assertEqual(second_call_kwargs["reference_images"], [frame1_url])

        # Verify files were written
        self.assertTrue(frames[0].image_path.exists())
        self.assertTrue(frames[1].image_path.exists())

    def test_save_base64_image(self) -> None:
        storyboard = Storyboard(
            title="Base64 Test",
            summary="Test",
            scenes=[Scene(index=1, description="One", visual_prompt="P1")],
        )

        raw_bytes = b"my-binary-image-data"
        b64_str = base64.b64encode(raw_bytes).decode("ascii")
        self.mock_client.generate_image.return_value = f"data:image/png;base64,{b64_str}"

        frames = self.generator.generate_frames(
            storyboard=storyboard,
            output_dir=self.output_dir,
            use_continuity=False,
        )

        self.assertEqual(len(frames), 1)
        saved_bytes = frames[0].image_path.read_bytes()
        self.assertEqual(saved_bytes, raw_bytes)


if __name__ == "__main__":
    unittest.main()
