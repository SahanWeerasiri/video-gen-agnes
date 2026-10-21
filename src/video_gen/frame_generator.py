"""Frame generator using agnes-image-2.0-flash with visual continuity anchoring."""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

from video_gen.client import AgnesClient
from video_gen.storyboard import Storyboard

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedFrame:
    """Metadata for an image frame generated for a specific scene."""

    scene_index: int
    image_path: Path
    prompt: str
    camera_motion: str
    duration: float
    remote_url: Optional[str] = None


class FrameGenerator:
    """Orchestrates image generation across storyboard scenes, maintaining style continuity."""

    def __init__(
        self,
        client: AgnesClient,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.client = client
        self.session = session or requests.Session()

    def generate_frames(
        self,
        storyboard: Storyboard,
        output_dir: Path,
        use_continuity: bool = True,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> list[GeneratedFrame]:
        """Generate all scene images from the storyboard and save locally."""
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        generated_frames: list[GeneratedFrame] = []
        last_image_ref: Optional[str] = None
        total_scenes = len(storyboard.scenes)

        for i, scene in enumerate(storyboard.scenes, start=1):
            frame_filename = f"frame_{scene.index:03d}.png"
            dest_path = frames_dir / frame_filename

            logger.info(
                "Generating frame %d/%d for scene: %s",
                i,
                total_scenes,
                scene.description[:40],
            )

            # Determine whether to anchor to prior frame for visual continuity
            reference_images: Optional[list[str]] = None
            if use_continuity and last_image_ref and i > 1:
                # Per Agnes docs, image-to-image takes reference URLs or base64 in extra_body.image
                reference_images = [last_image_ref]

            image_result = self.client.generate_image(
                prompt=scene.visual_prompt,
                reference_images=reference_images,
                return_base64=False,
            )

            # Save the image to local disk
            self._save_image(image_result, dest_path)

            # Track reference for subsequent frame continuity
            last_image_ref = image_result

            frame = GeneratedFrame(
                scene_index=scene.index,
                image_path=dest_path,
                prompt=scene.visual_prompt,
                camera_motion=scene.camera_motion,
                duration=scene.duration,
                remote_url=image_result if image_result.startswith("http") else None,
            )
            generated_frames.append(frame)

            if on_progress:
                on_progress(i, total_scenes)

        return generated_frames

    def _save_image(self, image_data: str, dest_path: Path) -> None:
        """Save image content, handling either an HTTP URL or a Base64 string."""
        if image_data.startswith("http://") or image_data.startswith("https://"):
            resp = self.session.get(image_data, timeout=60.0)
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(resp.content)
        else:
            # Strip data URI header if present: data:image/png;base64,...
            clean_b64 = re.sub(r"^data:image/[a-zA-Z]+;base64,", "", image_data).strip()
            raw_bytes = base64.b64decode(clean_b64)
            with open(dest_path, "wb") as f:
                f.write(raw_bytes)
