"""Storyboard generator using agnes-2.5-flash for zero-cost scene planning."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from video_gen.client import AgnesClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scene:
    """An individual scene within a video storyboard."""

    index: int
    description: str
    visual_prompt: str
    camera_motion: str = "zoom_in"
    duration: float = 4.0


@dataclass(frozen=True)
class Storyboard:
    """A complete sequence of scenes for video rendering."""

    title: str
    summary: str
    scenes: list[Scene]


STORYBOARD_SYSTEM_PROMPT = """You are an expert cinematic director and storyboard artist for AI video generation.
Your job is to transform a user's prompt or idea into a coherent sequence of scenes.

Each scene MUST include:
1. "description": A concise narrative explanation of what happens in this scene.
2. "visual_prompt": A highly detailed image prompt optimized for AI image generation adhering to this structure:
   [Subject] + [Scene / Background] + [Style] + [Lighting] + [Composition] + [Quality Requirements]
   Ensure visual consistency across scenes: keep the character, subject, art style, and core aesthetic stable.
3. "camera_motion": One of ["zoom_in", "zoom_out", "pan_left", "pan_right", "static"].
4. "duration": Float duration in seconds (default 4.0).

Output strictly valid JSON with this exact schema:
{
  "title": "Short title",
  "summary": "Brief summary of the video",
  "scenes": [
    {
      "index": 1,
      "description": "Opening shot description",
      "visual_prompt": "Subject, scene, style, lighting, composition, quality",
      "camera_motion": "zoom_in",
      "duration": 4.0
    }
  ]
}
Do not include any conversational filler, markdown explanations, or commentary. Only return the JSON.
"""


class StoryboardGenerator:
    """Generates structured video storyboards using agnes-2.5-flash."""

    def __init__(self, client: AgnesClient) -> None:
        self.client = client

    def generate(
        self,
        prompt: str,
        num_scenes: int = 4,
        style: Optional[str] = None,
        duration_per_scene: float = 4.0,
    ) -> Storyboard:
        """Create a multi-scene storyboard from a text prompt."""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        if num_scenes <= 0:
            raise ValueError("num_scenes must be at least 1.")

        style_instruction = f" Art style: {style}." if style else ""
        user_message = (
            f"Generate a storyboard with exactly {num_scenes} scenes for the following concept:{style_instruction}\n\n"
            f'"{prompt.strip()}"'
        )

        messages = [
            {"role": "system", "content": STORYBOARD_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        raw_content = self.client.create_chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        return self._parse_response(raw_content, default_duration=duration_per_scene, expected_count=num_scenes)

    def _parse_response(
        self,
        raw_text: str,
        default_duration: float,
        expected_count: int,
    ) -> Storyboard:
        """Parse and validate JSON response from the text model."""
        clean_text = raw_text.strip()

        # Remove markdown code fence if present
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```[a-zA-Z]*\n", "", clean_text)
            clean_text = re.sub(r"\n```$", "", clean_text).strip()

        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError as err:
            # Fallback regex extraction if model included surrounding text
            match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    raise ValueError(f"Could not parse valid JSON from model response: {raw_text[:200]}") from err
            else:
                raise ValueError(f"Could not parse valid JSON from model response: {raw_text[:200]}") from err

        title = str(data.get("title", "Untitled Storyboard"))
        summary = str(data.get("summary", ""))
        raw_scenes = data.get("scenes", [])

        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise ValueError(f"Expected a list of scenes in response, got: {raw_scenes}")

        scenes: list[Scene] = []
        for i, s in enumerate(raw_scenes, start=1):
            if not isinstance(s, dict):
                continue

            index = int(s.get("index", i))
            description = str(s.get("description", f"Scene {index}"))
            visual_prompt = str(s.get("visual_prompt", description))
            camera_motion = str(s.get("camera_motion", "zoom_in")).lower()
            if camera_motion not in {"zoom_in", "zoom_out", "pan_left", "pan_right", "static"}:
                camera_motion = "zoom_in"

            duration = float(s.get("duration", default_duration))
            if duration <= 0:
                duration = default_duration

            scenes.append(
                Scene(
                    index=index,
                    description=description,
                    visual_prompt=visual_prompt,
                    camera_motion=camera_motion,
                    duration=duration,
                )
            )

        if not scenes:
            raise ValueError("No valid scenes extracted from storyboard response.")

        return Storyboard(title=title, summary=summary, scenes=scenes)
