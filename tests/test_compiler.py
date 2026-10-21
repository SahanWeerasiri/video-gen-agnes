"""Unit tests for FFmpegCompiler."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from video_gen.compiler import FFmpegCompiler, FFmpegError, FFmpegNotFoundError
from video_gen.frame_generator import GeneratedFrame


class TestFFmpegCompiler(unittest.TestCase):
    """Test FFmpeg compilation command generation and execution handling."""

    def setUp(self) -> None:
        self.compiler = FFmpegCompiler(ffmpeg_path="/usr/bin/ffmpeg")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_missing_ffmpeg_raises_error(self) -> None:
        with patch("shutil.which", return_value=None):
            with self.assertRaises(FFmpegNotFoundError):
                FFmpegCompiler(ffmpeg_path=None)

    def test_parse_resolution_valid(self) -> None:
        w, h = self.compiler._parse_resolution("1920x1080")
        self.assertEqual((w, h), (1920, 1080))

    def test_parse_resolution_invalid(self) -> None:
        with self.assertRaises(ValueError):
            self.compiler._parse_resolution("1080p")

    def test_build_zoompan_filter(self) -> None:
        f_in = self.compiler._build_zoompan_filter("zoom_in", 72, 1280, 720)
        self.assertIn("min(zoom+0.0015,1.25)", f_in)
        self.assertIn("s=1280x720", f_in)

        f_out = self.compiler._build_zoompan_filter("zoom_out", 72, 1280, 720)
        self.assertIn("max(1.25-0.0015*on,1.0)", f_out)

        f_pan_left = self.compiler._build_zoompan_filter("pan_left", 72, 1280, 720)
        self.assertIn("1-on/72", f_pan_left)

        f_pan_right = self.compiler._build_zoompan_filter("pan_right", 72, 1280, 720)
        self.assertIn("on/72", f_pan_right)

        f_static = self.compiler._build_zoompan_filter("static", 72, 1280, 720)
        self.assertEqual(f_static, "zoompan=z='1.0':d=72:s=1280x720")

    @patch("subprocess.run")
    def test_compile_video_with_motion(self, mock_run: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        img_file = self.output_dir / "frame_001.png"
        img_file.write_bytes(b"dummy")

        frames = [
            GeneratedFrame(
                scene_index=1,
                image_path=img_file,
                prompt="test",
                camera_motion="zoom_in",
                duration=3.0,
            )
        ]

        out_mp4 = self.output_dir / "result.mp4"
        res = self.compiler.compile_video(frames=frames, output_file=out_mp4, fps=24, enable_motion=True)

        self.assertEqual(res, out_mp4)
        # Should have run scene clip rendering and final concat
        self.assertEqual(mock_run.call_count, 2)

    @patch("subprocess.run")
    def test_ffmpeg_failure_raises_ffmpeg_error(self, mock_run: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Invalid codec option"
        mock_run.return_value = mock_proc

        img_file = self.output_dir / "frame_001.png"
        img_file.write_bytes(b"dummy")
        frames = [
            GeneratedFrame(scene_index=1, image_path=img_file, prompt="test", camera_motion="static", duration=2.0)
        ]

        with self.assertRaises(FFmpegError) as ctx:
            self.compiler.compile_video(frames, self.output_dir / "test.mp4", enable_motion=False)
        self.assertIn("Invalid codec option", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
