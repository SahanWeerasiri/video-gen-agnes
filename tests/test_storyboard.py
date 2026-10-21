"""Unit tests for StoryboardGenerator."""

import unittest
from unittest.mock import MagicMock

from video_gen.storyboard import StoryboardGenerator


class TestStoryboardGenerator(unittest.TestCase):
    """Test storyboard generation and parsing from agnes-2.5-flash responses."""

    def setUp(self) -> None:
        self.mock_client = MagicMock()
        self.generator = StoryboardGenerator(client=self.mock_client)

    def test_generate_clean_json(self) -> None:
        mock_json = """{
            "title": "Neon Chase",
            "summary": "A futuristic car chases a drone through rain-slicked streets.",
            "scenes": [
                {
                    "index": 1,
                    "description": "Opening wide shot of neon skyline",
                    "visual_prompt": "Cinematic futuristic city, neon towers, rain reflections, 8k",
                    "camera_motion": "pan_left",
                    "duration": 4.0
                },
                {
                    "index": 2,
                    "description": "Close-up of driver in sports car",
                    "visual_prompt": "Driver gripping steering wheel, dashboard glowing, realistic lighting",
                    "camera_motion": "zoom_in",
                    "duration": 3.5
                }
            ]
        }"""
        self.mock_client.create_chat_completion.return_value = mock_json

        storyboard = self.generator.generate(prompt="Futuristic car chase in rain", num_scenes=2)

        self.assertEqual(storyboard.title, "Neon Chase")
        self.assertEqual(len(storyboard.scenes), 2)
        self.assertEqual(storyboard.scenes[0].camera_motion, "pan_left")
        self.assertEqual(storyboard.scenes[1].duration, 3.5)

    def test_generate_json_in_markdown_fence(self) -> None:
        mock_response = """```json
{
    "title": "Ancient Forest",
    "summary": "A peaceful journey through misty redwoods.",
    "scenes": [
        {
            "index": 1,
            "description": "Sunbeams piercing fog",
            "visual_prompt": "Giant redwood trees, morning mist, golden sunbeams, wide angle",
            "camera_motion": "tilt_up",
            "duration": 5.0
        }
    ]
}
```"""
        self.mock_client.create_chat_completion.return_value = mock_response

        storyboard = self.generator.generate(prompt="Ancient forest mist")
        self.assertEqual(storyboard.title, "Ancient Forest")
        self.assertEqual(len(storyboard.scenes), 1)
        # Note: 'tilt_up' gets defaulted to 'zoom_in' because it's not in the 5 supported ffmpeg motion presets
        self.assertEqual(storyboard.scenes[0].camera_motion, "zoom_in")

    def test_empty_prompt_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            self.generator.generate(prompt="   ")

    def test_invalid_num_scenes_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            self.generator.generate(prompt="Valid prompt", num_scenes=0)

    def test_unparseable_json_raises_error(self) -> None:
        self.mock_client.create_chat_completion.return_value = "Sorry, I cannot produce JSON."
        with self.assertRaises(ValueError):
            self.generator.generate(prompt="Something")


if __name__ == "__main__":
    unittest.main()
