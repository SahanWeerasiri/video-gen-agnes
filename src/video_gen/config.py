"""Configuration management for the zero-cost Agnes video generation pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable configuration for video generation."""

    api_key: str
    base_url: str = "https://apihub.agnes-ai.com/v1"
    text_model: str = "agnes-2.5-flash"
    image_model: str = "agnes-image-2.0-flash"
    image_size: str = "1024x768"
    fps: int = 24
    seconds_per_scene: float = 4.0
    transition_duration: float = 1.0
    output_dir: Path = Path("output")
    max_retries: int = 5
    base_backoff_sec: float = 2.0
    timeout_sec: float = 120.0

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("AGNES_API_KEY cannot be empty.")
        if self.fps <= 0:
            raise ValueError(f"fps must be positive, got {self.fps}")
        if self.seconds_per_scene <= 0:
            raise ValueError(f"seconds_per_scene must be positive, got {self.seconds_per_scene}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {self.max_retries}")


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a simple .env file without external dependencies."""
    env_vars: dict[str, str] = {}
    if not env_path.is_file():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key:
                    env_vars[key] = value
    return env_vars


def load_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    text_model: Optional[str] = None,
    image_model: Optional[str] = None,
    image_size: Optional[str] = None,
    fps: Optional[int] = None,
    seconds_per_scene: Optional[float] = None,
    output_dir: Optional[Path] = None,
    env_file: Optional[Path] = None,
) -> PipelineConfig:
    """Load and validate configuration from parameters, environment variables, or .env file."""
    # First check env_file or default .env in cwd
    file_vars: dict[str, str] = {}
    candidate_env = env_file or Path(".env")
    if candidate_env.exists():
        file_vars = parse_env_file(candidate_env)

    resolved_key = (
        api_key
        or os.environ.get("AGNES_API_KEY")
        or file_vars.get("AGNES_API_KEY", "")
    )

    resolved_base_url = (
        base_url
        or os.environ.get("AGNES_BASE_URL")
        or file_vars.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
    ).rstrip("/")

    resolved_text_model = (
        text_model
        or os.environ.get("AGNES_TEXT_MODEL")
        or file_vars.get("AGNES_TEXT_MODEL", "agnes-2.5-flash")
    )

    resolved_image_model = (
        image_model
        or os.environ.get("AGNES_IMAGE_MODEL")
        or file_vars.get("AGNES_IMAGE_MODEL", "agnes-image-2.0-flash")
    )

    resolved_image_size = (
        image_size
        or os.environ.get("DEFAULT_IMAGE_SIZE")
        or file_vars.get("DEFAULT_IMAGE_SIZE", "1024x768")
    )

    raw_fps = fps or os.environ.get("DEFAULT_FPS") or file_vars.get("DEFAULT_FPS", 24)
    resolved_fps = int(raw_fps)

    raw_duration = (
        seconds_per_scene
        or os.environ.get("DEFAULT_SCENE_DURATION")
        or file_vars.get("DEFAULT_SCENE_DURATION", 4.0)
    )
    resolved_duration = float(raw_duration)

    raw_out = (
        output_dir
        or os.environ.get("OUTPUT_DIR")
        or file_vars.get("OUTPUT_DIR", "output")
    )
    resolved_output_dir = Path(raw_out)

    return PipelineConfig(
        api_key=resolved_key,
        base_url=resolved_base_url,
        text_model=resolved_text_model,
        image_model=resolved_image_model,
        image_size=resolved_image_size,
        fps=resolved_fps,
        seconds_per_scene=resolved_duration,
        output_dir=resolved_output_dir,
    )
