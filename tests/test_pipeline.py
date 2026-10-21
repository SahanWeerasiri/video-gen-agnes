"""Unit tests for ZeroCostVideoPipeline and CLI."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from video_gen.cli import main, parse_args
from video_gen.config import PipelineConfig
from video_gen.frame_generator import GeneratedFrame
from video_gen.pipeline import ZeroCostVideoPipeline
from video_gen.storyboard import Scene, Storyboard


class TestZeroCostVideoPipeline(unittest.TestCase):
    """Test full pipeline orchestration with mocked components."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

        self.config = PipelineConfig(
            api_key="mock_key",
            output_dir=self.output_dir,
            seconds_per_scene=3.0,
        )

        self.mock_client = MagicMock()
        self.mock_storyboard_gen = MagicMock()
        self.mock_frame_gen = MagicMock()
        self.mock_compiler = MagicMock()

        self.pipeline = ZeroCostVideoPipeline(
            config=self.config,
            client=self.mock_client,
            storyboard_gen=self.mock_storyboard_gen,
            frame_gen=self.mock_frame_gen,
            compiler=self.mock_compiler,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_end_to_end(self) -> None:
        mock_storyboard = Storyboard(
            title="Sunrise Ocean",
            summary="Calm ocean waves at dawn",
            scenes=[
                Scene(index=1, description="Sun peeking over horizon", visual_prompt="P1", camera_motion="zoom_in", duration=3.0),
                Scene(index=2, description="Waves crashing on beach", visual_prompt="P2", camera_motion="pan_right", duration=3.0),
            ],
        )
        self.mock_storyboard_gen.generate.return_value = mock_storyboard

        f1 = self.output_dir / "f1.png"
        f2 = self.output_dir / "f2.png"
        f1.touch()
        f2.touch()

        mock_frames = [
            GeneratedFrame(scene_index=1, image_path=f1, prompt="P1", camera_motion="zoom_in", duration=3.0),
            GeneratedFrame(scene_index=2, image_path=f2, prompt="P2", camera_motion="pan_right", duration=3.0),
        ]
        self.mock_frame_gen.generate_frames.return_value = mock_frames

        status_messages: list[str] = []
        result = self.pipeline.run(
            prompt="Sunrise ocean video",
            num_scenes=2,
            output_name="sunset.mp4",
            on_status=lambda msg: status_messages.append(msg),
        )

        self.assertIsNotNone(result.video_path)
        self.assertEqual(result.total_duration, 6.0)
        self.assertEqual(len(result.frames), 2)
        self.assertTrue((self.output_dir / "storyboard.json").exists())

        # Verify storyboard.json content
        saved_sb = json.loads((self.output_dir / "storyboard.json").read_text())
        self.assertEqual(saved_sb["title"], "Sunrise Ocean")
        self.assertEqual(len(saved_sb["scenes"]), 2)

        # Verify compiler was invoked
        self.mock_compiler.compile_video.assert_called_once()

    def test_run_dry_run_mode(self) -> None:
        mock_storyboard = Storyboard(
            title="Dry Run Test",
            summary="Only plan storyboard",
            scenes=[Scene(index=1, description="Scene 1", visual_prompt="P1", duration=4.0)],
        )
        self.mock_storyboard_gen.generate.return_value = mock_storyboard

        result = self.pipeline.run(
            prompt="Dry run test",
            dry_run=True,
        )

        self.assertIsNone(result.video_path)
        self.assertEqual(len(result.frames), 0)
        self.assertTrue((self.output_dir / "storyboard.json").exists())
        self.mock_frame_gen.generate_frames.assert_not_called()
        self.mock_compiler.compile_video.assert_not_called()


class TestCLI(unittest.TestCase):
    """Test CLI argument parsing and execution."""

    def test_parse_args_defaults(self) -> None:
        args = parse_args(["--prompt", "A flying eagle"])
        self.assertEqual(args.prompt, "A flying eagle")
        self.assertEqual(args.scenes, 4)
        self.assertEqual(args.duration, 4.0)
        self.assertEqual(args.size, "1024x768")
        self.assertFalse(args.no_motion)
        self.assertFalse(args.dry_run)

    @patch("video_gen.cli.ZeroCostVideoPipeline")
    def test_cli_main_dry_run(self, mock_pipeline_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_pipeline_cls.return_value = mock_instance

        mock_result = MagicMock()
        mock_result.video_path = None
        mock_result.storyboard.title = "Mock Title"
        mock_result.storyboard.summary = "Mock Summary"
        mock_result.storyboard.scenes = []
        mock_instance.run.return_value = mock_result

        exit_code = main(["--prompt", "Space station", "--dry-run", "--api-key", "test_key"])
        self.assertEqual(exit_code, 0)
        mock_instance.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
