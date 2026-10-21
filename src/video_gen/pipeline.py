"""End-to-end orchestration pipeline for zero-cost video generation."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from video_gen.client import AgnesClient
from video_gen.compiler import FFmpegCompiler
from video_gen.config import PipelineConfig, load_config
from video_gen.frame_generator import FrameGenerator, GeneratedFrame
from video_gen.storyboard import Storyboard, StoryboardGenerator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """The outcome of a video generation pipeline run."""

    video_path: Optional[Path]
    storyboard: Storyboard
    frames: list[GeneratedFrame]
    total_duration: float


class ZeroCostVideoPipeline:
    """Orchestrates Agnes 2.5 Flash, Agnes Image 2.0 Flash, and FFmpeg for $0 video production."""

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        client: Optional[AgnesClient] = None,
        storyboard_gen: Optional[StoryboardGenerator] = None,
        frame_gen: Optional[FrameGenerator] = None,
        compiler: Optional[FFmpegCompiler] = None,
    ) -> None:
        self.config = config or load_config()
        self.client = client or AgnesClient(self.config)
        self.storyboard_gen = storyboard_gen or StoryboardGenerator(self.client)
        self.frame_gen = frame_gen or FrameGenerator(self.client)
        self.compiler = compiler or FFmpegCompiler()

    def run(
        self,
        prompt: str,
        num_scenes: int = 4,
        style: Optional[str] = None,
        output_name: str = "video.mp4",
        enable_motion: bool = True,
        use_continuity: bool = True,
        dry_run: bool = False,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> PipelineResult:
        """Execute the full video generation pipeline."""
        out_dir = self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # Stage 1: Storyboard Generation via agnes-2.5-flash ($0)
        self._notify(on_status, "Planning scene storyboard using agnes-2.5-flash ($0)...")
        storyboard = self.storyboard_gen.generate(
            prompt=prompt,
            num_scenes=num_scenes,
            style=style,
            duration_per_scene=self.config.seconds_per_scene,
        )

        # Save storyboard.json for transparency and inspection
        storyboard_path = out_dir / "storyboard.json"
        storyboard_dict = {
            "title": storyboard.title,
            "summary": storyboard.summary,
            "scenes": [asdict(s) for s in storyboard.scenes],
        }
        with open(storyboard_path, "w", encoding="utf-8") as f:
            json.dump(storyboard_dict, f, indent=2)

        total_duration = sum(s.duration for s in storyboard.scenes)

        if dry_run:
            self._notify(on_status, f"Dry run complete. Storyboard saved to {storyboard_path}")
            return PipelineResult(
                video_path=None,
                storyboard=storyboard,
                frames=[],
                total_duration=total_duration,
            )

        # Stage 2: Frame Generation via agnes-image-2.0-flash ($0)
        self._notify(on_status, f"Generating {len(storyboard.scenes)} scene frames via agnes-image-2.0-flash ($0)...")
        frames = self.frame_gen.generate_frames(
            storyboard=storyboard,
            output_dir=out_dir,
            use_continuity=use_continuity,
            on_progress=lambda current, total: self._notify(
                on_status,
                f"Generated frame {current}/{total} ({storyboard.scenes[current - 1].description[:35]}...)",
            ),
        )

        # Stage 3: Local Video Synthesis via FFmpeg ($0 compute)
        self._notify(on_status, "Compiling frames and motion dynamics into MP4 using FFmpeg...")
        final_video_path = out_dir / output_name
        self.compiler.compile_video(
            frames=frames,
            output_file=final_video_path,
            fps=self.config.fps,
            resolution=self.config.image_size,
            enable_motion=enable_motion,
        )

        self._notify(on_status, f"Video generated successfully at: {final_video_path}")
        return PipelineResult(
            video_path=final_video_path,
            storyboard=storyboard,
            frames=frames,
            total_duration=total_duration,
        )

    def _notify(self, callback: Optional[Callable[[str], None]], message: str) -> None:
        logger.info(message)
        if callback:
            callback(message)
