"""FFmpeg compilation engine for assembling generated image sequences into animated video."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from video_gen.frame_generator import GeneratedFrame

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Exception raised when an FFmpeg command fails."""


class FFmpegNotFoundError(FFmpegError):
    """Exception raised when ffmpeg executable is not installed or not in PATH."""


class FFmpegCompiler:
    """Compiles image frames into video using local FFmpeg."""

    def __init__(self, ffmpeg_path: Optional[str] = None) -> None:
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        if not self.ffmpeg_path:
            raise FFmpegNotFoundError(
                "FFmpeg executable not found in system PATH. "
                "Please install FFmpeg to compile videos locally."
            )

    def compile_video(
        self,
        frames: list[GeneratedFrame],
        output_file: Path,
        fps: int = 24,
        resolution: str = "1280x720",
        enable_motion: bool = True,
    ) -> Path:
        """Compile a list of generated frames into an MP4 video."""
        if not frames:
            raise ValueError("No frames provided for compilation.")

        output_file = output_file.resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        width, height = self._parse_resolution(resolution)

        if enable_motion:
            return self._compile_with_ken_burns(frames, output_file, fps, width, height)
        return self._compile_static_slideshow(frames, output_file, fps, width, height)

    def _parse_resolution(self, resolution: str) -> tuple[int, int]:
        """Parse resolution string e.g. '1280x720' or '1024x768' into width and height."""
        try:
            parts = resolution.lower().split("x")
            return int(parts[0]), int(parts[1])
        except Exception as err:
            raise ValueError(f"Invalid resolution format '{resolution}', expected 'WIDTHxHEIGHT'") from err

    def _build_zoompan_filter(
        self,
        motion: str,
        total_frames: int,
        width: int,
        height: int,
        fps: int = 24,
    ) -> str:
        """Generate the FFmpeg zoompan filter string for cinematic camera movements."""
        motion = motion.lower()

        if motion == "zoom_in":
            # Zooms in from 1.0 to 1.25 towards the center
            return (
                f"zoompan=z='min(zoom+0.0015,1.25)':d={total_frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
            )
        elif motion == "zoom_out":
            # Zooms out from 1.25 to 1.0 from the center
            return (
                f"zoompan=z='max(1.25-0.0015*on,1.0)':d={total_frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
            )
        elif motion == "pan_left":
            # Pans horizontally from right to left
            return (
                f"zoompan=z='1.15':d={total_frames}:"
                f"x='(1-on/{total_frames})*(iw-iw/zoom)':y='(ih-ih/zoom)/2':s={width}x{height}:fps={fps}"
            )
        elif motion == "pan_right":
            # Pans horizontally from left to right
            return (
                f"zoompan=z='1.15':d={total_frames}:"
                f"x='(on/{total_frames})*(iw-iw/zoom)':y='(ih-ih/zoom)/2':s={width}x{height}:fps={fps}"
            )
        else:
            # Static: gentle scale to destination resolution
            return f"zoompan=z='1.0':d={total_frames}:s={width}x{height}:fps={fps}"

    def _compile_with_ken_burns(
        self,
        frames: list[GeneratedFrame],
        output_file: Path,
        fps: int,
        width: int,
        height: int,
    ) -> Path:
        """Render individual motion clips per scene, then concatenate them seamlessly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            clip_paths: list[Path] = []

            for i, frame in enumerate(frames):
                clip_path = temp_path / f"clip_{i:03d}.mp4"
                total_frames = max(1, int(round(frame.duration * fps)))
                zoompan_filter = self._build_zoompan_filter(
                    motion=frame.camera_motion,
                    total_frames=total_frames,
                    width=width,
                    height=height,
                    fps=fps,
                )

                # Filter graph: zoompan -> setpts -> format
                vf = f"{zoompan_filter},setpts=PTS-STARTPTS,format=yuv420p"

                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", str(frame.image_path.resolve()),
                    "-vf", vf,
                    "-frames:v", str(total_frames),
                    "-t", f"{frame.duration:.3f}",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    str(clip_path),
                ]

                self._run_ffmpeg(cmd, desc=f"Rendering scene {frame.scene_index} motion clip")
                clip_paths.append(clip_path)

            # Build concat demuxer file
            concat_list = temp_path / "concat_list.txt"
            with open(concat_list, "w", encoding="utf-8") as f:
                for cp in clip_paths:
                    f.write(f"file '{cp.resolve()}'\n")

            # Final concat into output mp4
            concat_cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(output_file),
            ]

            self._run_ffmpeg(concat_cmd, desc="Concatenating scenes into final video")

        return output_file

    def _compile_static_slideshow(
        self,
        frames: list[GeneratedFrame],
        output_file: Path,
        fps: int,
        width: int,
        height: int,
    ) -> Path:
        """Fast slideshow compilation using concat demuxer."""
        total_duration = sum(f.duration for f in frames)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            concat_list = temp_path / "slideshow_list.txt"

            with open(concat_list, "w", encoding="utf-8") as f:
                for frame in frames:
                    f.write(f"file '{frame.image_path.resolve()}'\n")
                    f.write(f"duration {frame.duration}\n")
                # Repeat last file per concat demuxer specification
                f.write(f"file '{frames[-1].image_path.resolve()}'\n")

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-t", f"{total_duration:.3f}",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(output_file),
            ]

            self._run_ffmpeg(cmd, desc="Compiling slideshow video")

        return output_file

    def concat_clips(self, clip_paths: list[Path], output_file: Path) -> Path:
        """Concatenate multiple video clips into a single continuous video."""
        if not clip_paths:
            raise ValueError("No video clips provided for concatenation.")
        output_file = output_file.resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if len(clip_paths) == 1:
            shutil.copyfile(clip_paths[0], output_file)
            return output_file

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            concat_list = temp_path / "concat_clips.txt"
            with open(concat_list, "w", encoding="utf-8") as f:
                for clip in clip_paths:
                    f.write(f"file '{clip.resolve()}'\n")

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(output_file),
            ]
            self._run_ffmpeg(cmd, desc="Concatenating video clips")

        return output_file

    def _run_ffmpeg(self, cmd: list[str], desc: str) -> None:
        """Execute FFmpeg command and raise FFmpegError with stderr details on failure."""
        logger.debug("Running FFmpeg: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or proc.stdout.strip()
            raise FFmpegError(f"FFmpeg failed during {desc} (code {proc.returncode}): {error_msg}")
