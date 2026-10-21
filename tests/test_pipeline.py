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

    def test_run_native_video_single_clip(self) -> None:
        self.mock_client.create_video_task.return_value = {
            "id": "task_1",
            "video_id": "vid_1",
            "status": "queued",
        }
        self.mock_client.wait_for_video.return_value = {
            "status": "completed",
            "progress": 100,
            "url": "https://example.com/clip.mp4",
        }
        def fake_download(url: str, output_path: Path) -> Path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            return p
        self.mock_client.download_video.side_effect = fake_download

        result = self.pipeline.run(
            prompt="A futuristic neon car speeding at night",
            num_scenes=1,
            engine="native_video",
            video_seconds="6",
            video_size="720P",
            video_aspect_ratio="16:9",
        )

        self.assertIsNotNone(result.video_path)
        self.assertEqual(result.total_duration, 6.0)
        self.assertTrue(result.video_path.exists())
        self.mock_client.create_video_task.assert_called_once_with(
            prompt="A futuristic neon car speeding at night",
            mode="text",
            seconds="6",
            size="720P",
            aspect_ratio="16:9",
        )
        self.mock_client.wait_for_video.assert_called_once()
        self.mock_client.download_video.assert_called_once()

    def test_run_native_video_multi_scenes(self) -> None:
        mock_storyboard = Storyboard(
            title="Space Journey",
            summary="Journey through the cosmos",
            scenes=[
                Scene(index=1, description="Rocket takeoff", visual_prompt="P1", duration=4.0),
                Scene(index=2, description="Orbiting Earth", visual_prompt="P2", duration=5.0),
            ],
        )
        self.mock_storyboard_gen.generate.return_value = mock_storyboard
        self.mock_client.create_video_task.side_effect = [
            {"id": "t1", "video_id": "v1"},
            {"id": "t2", "video_id": "v2"},
        ]
        self.mock_client.wait_for_video.side_effect = [
            {"status": "completed", "url": "https://example.com/c1.mp4"},
            {"status": "completed", "url": "https://example.com/c2.mp4"},
        ]
        def fake_download(url: str, output_path: Path) -> Path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            return p
        self.mock_client.download_video.side_effect = fake_download
        def fake_concat(clip_paths: list[Path], output_file: Path) -> Path:
            output_file.touch()
            return output_file
        self.mock_compiler.concat_clips.side_effect = fake_concat

        result = self.pipeline.run(
            prompt="Space voyage documentary",
            num_scenes=2,
            engine="native_video",
        )

        self.assertIsNotNone(result.video_path)
        self.assertEqual(result.total_duration, 9.0)
        self.assertEqual(self.mock_client.create_video_task.call_count, 2)
        self.assertEqual(self.mock_client.wait_for_video.call_count, 2)
        self.mock_compiler.concat_clips.assert_called_once()


class TestCLI(unittest.TestCase):
    """Test CLI argument parsing and execution."""

    def test_parse_args_defaults(self) -> None:
        args = parse_args(["--prompt", "A flying eagle"])
        self.assertEqual(args.prompt, "A flying eagle")
        self.assertEqual(args.scenes, 4)
        self.assertEqual(args.duration, 4.0)
        self.assertEqual(args.size, "1024x768")
        self.assertEqual(args.engine, "zero_cost")
        self.assertEqual(args.video_size, "720P")
        self.assertEqual(args.video_seconds, "5")
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
