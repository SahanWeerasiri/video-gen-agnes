"""Unit tests for PipelineConfig and configuration loading."""

import os
import tempfile
import unittest
from pathlib import Path

from video_gen.config import PipelineConfig, load_config, parse_env_file


class TestPipelineConfig(unittest.TestCase):
    """Test validation and default values of PipelineConfig."""

    def test_valid_config(self) -> None:
        cfg = PipelineConfig(api_key="test-key-123")
        self.assertEqual(cfg.api_key, "test-key-123")
        self.assertEqual(cfg.base_url, "https://apihub.agnes-ai.com/v1")
        self.assertEqual(cfg.text_model, "agnes-2.5-flash")
        self.assertEqual(cfg.image_model, "agnes-image-2.0-flash")
        self.assertEqual(cfg.fps, 24)
        self.assertEqual(cfg.seconds_per_scene, 4.0)

    def test_empty_api_key_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            PipelineConfig(api_key="")

    def test_invalid_fps_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            PipelineConfig(api_key="key", fps=0)

    def test_invalid_seconds_per_scene_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            PipelineConfig(api_key="key", seconds_per_scene=-1.0)


class TestLoadConfig(unittest.TestCase):
    """Test environment variable and .env file loading."""

    def test_parse_env_file(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("# Comment line\n")
            f.write("AGNES_API_KEY=mock_key_abc\n")
            f.write("AGNES_BASE_URL=https://custom.api/v1\n")
            temp_path = Path(f.name)

        try:
            parsed = parse_env_file(temp_path)
            self.assertEqual(parsed.get("AGNES_API_KEY"), "mock_key_abc")
            self.assertEqual(parsed.get("AGNES_BASE_URL"), "https://custom.api/v1")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_load_config_explicit_key(self) -> None:
        cfg = load_config(api_key="explicit_key", base_url="https://test.api/v1")
        self.assertEqual(cfg.api_key, "explicit_key")
        self.assertEqual(cfg.base_url, "https://test.api/v1")

    def test_load_config_with_custom_env_vars(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("AGNES_API_KEY=file_key\n")
            f.write("AGNES_TEXT_MODEL=custom-text-model\n")
            f.write("AGNES_IMAGE_MODEL=custom-image-model\n")
            f.write("DEFAULT_IMAGE_SIZE=1024x1024\n")
            f.write("DEFAULT_FPS=30\n")
            f.write("DEFAULT_SCENE_DURATION=5.5\n")
            f.write("OUTPUT_DIR=custom_output\n")
            temp_path = Path(f.name)

        try:
            cfg = load_config(env_file=temp_path)
            self.assertEqual(cfg.api_key, "file_key")
            self.assertEqual(cfg.text_model, "custom-text-model")
            self.assertEqual(cfg.image_model, "custom-image-model")
            self.assertEqual(cfg.image_size, "1024x1024")
            self.assertEqual(cfg.fps, 30)
            self.assertEqual(cfg.seconds_per_scene, 5.5)
            self.assertEqual(cfg.output_dir, Path("custom_output"))
        finally:
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
