# User Guide & CLI Manual

This guide covers usage instructions, configuration parameters, and best practices for the Zero-Cost Video Generator using Agnes AI Flash models and FFmpeg.

---

## 1. Quick Start

### 1.1 Prerequisites
1. **Python 3.10+** (Python 3.14 verified)
2. **FFmpeg** installed and accessible in `PATH`:
   ```bash
   ffmpeg -version
   ```
3. An **Agnes AI Platform Account** and API key.

### 1.2 Virtual Environment & Dependencies
Set up the Python virtual environment (`.venv`):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1.3 Environment Setup
Create a `.env` file in the project root:
```bash
cp .env.example .env
```
Ensure your `.env` contains your Agnes API key:
```dotenv
AGNES_API_KEY="your-agnes-api-key-here"
AGNES_BASE_URL="https://apihub.agnes-ai.com/v1"
```

---

## 2. Interactive Web Studio UI

Launch the Web Studio interface:
```bash
python app.py
```
Open **http://localhost:5000** in your browser to:
- Monitor live server status and uptime via the built-in health badge.
- Test creative ideas with 1-click prompt chips.
- Adjust scenes, durations, resolution, and styles interactively.
- Track real-time progress and logs.
- Watch and download generated videos directly in your browser.

### 2.1 Health Check API
You can check server health programmatically or from monitoring agents:
```bash
curl http://localhost:5000/health
# or
curl http://localhost:5000/api/health
```

Example Response:
```json
{
  "status": "healthy",
  "server": "Agnes Studio",
  "version": "0.1.0",
  "uptime_seconds": 45.2,
  "ffmpeg_installed": true,
  "has_api_key": true,
  "timestamp": "2026-10-21T03:15:20.123456+00:00"
}
```

---

## 3. CLI Reference

Run the video generation tool via Python module:
```bash
python -m video_gen --prompt "<your-video-prompt>" [options]
```

### Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `-p`, `--prompt` | `str` | *Required* | Text prompt or creative concept describing the video. |
| `--engine` | `str` | `zero_cost` | Generation engine: `zero_cost` (Flash + FFmpeg Ken Burns) or `native_video` (Agnes Video 2.5 AI diffusion). |
| `-n`, `--scenes` | `int` | `4` | Number of sequential scenes to plan and generate (or stitch). |
| `-d`, `--duration`| `float` | `4.0` | Duration in seconds per scene (Zero-Cost engine). |
| `--video-seconds`| `str` | `"5"` | Duration in seconds for native video (`"4"`–`"12"`). |
| `--video-size` | `str` | `720P` | Resolution tier for native video (`720P`, `1080P`, `1K`, `2K`). |
| `--video-aspect-ratio` | `str` | `16:9` | Aspect ratio for native video (`16:9`, `9:16`, `1:1`, `4:3`, `21:9`). |
| `-s`, `--size` | `str` | `1024x768` | Output resolution tier (`1024x768`, `1024x1024`, `768x1024`). |
| `--style` | `str` | `None` | Artistic style directive (e.g., `'cinematic cyberpunk'`, `'anime'`, `'photorealistic'`). |
| `--fps` | `int` | `24` | Video frame rate. |
| `-o`, `--output-dir`| `Path`| `./output` | Output folder for storyboard, frames, and final MP4. |
| `--output-name` | `str` | `video.mp4` | Filename for compiled video. |
| `--no-motion` | `flag` | `False` | Disables Ken Burns zoom/pan camera motion (renders static slideshow). |
| `--no-continuity`| `flag`| `False` | Disables image-to-image sequential anchoring. |
| `--dry-run` | `flag` | `False` | Plans and outputs the storyboard JSON without calling image generation or FFmpeg. |
| `--api-key` | `str` | `None` | Override API key from CLI without editing `.env`. |
| `-v`, `--verbose`| `flag` | `False` | Enables detailed debug logging. |

---

## 3. Usage Examples

### 3.1 Zero-Cost Video Generation ($0 Unlimited)
Generate a 16-second video (4 scenes × 4.0s) with cinematic camera motion:
```bash
python -m video_gen \
  --prompt "A silver sports car driving through a futuristic city at night after rain" \
  --style "cinematic cyberpunk, neon reflections, 8k" \
  --scenes 4 \
  --duration 4.0 \
  --size "1024x768" \
  --output-name "cyber_car.mp4"
```

### 3.2 Native Agnes Video 2.5 (Direct AI Diffusion)
Generate a direct 6-second high-definition AI diffusion video with natural subject and camera motion:
```bash
python -m video_gen \
  --prompt "A majestic eagle soaring over snow-capped mountains, cinematic tracking shot" \
  --engine native_video \
  --video-seconds 6 \
  --video-size 1080P \
  --video-aspect-ratio 16:9 \
  --output-name "eagle_native.mp4"
```

### 3.3 Multi-Scene Native Assembly (Stitched with FFmpeg)
Decompose a script into multiple scenes, generate a native video clip for each, and stitch them seamlessly:
```bash
python -m video_gen \
  --prompt "Deep sea exploration documentary discovering glowing alien coral reefs" \
  --engine native_video \
  --scenes 3 \
  --video-seconds 5 \
  --output-name "deep_sea_film.mp4"
```

### 3.4 Previewing Storyboard (Dry Run - Zero API Image/Video Calls)
Check how `agnes-2.5-flash` interprets your prompt and breaks it into scenes before generating media:
```bash
python -m video_gen --prompt "A lone astronaut exploring a crystal cave on Mars" --dry-run
```
Outputs `output/storyboard.json` with scene breakdowns, camera directions, and visual prompts.

---

## 4. Python API Usage

You can also integrate the pipeline directly into Python applications:

```python
from video_gen import VideoPipeline, load_config

# Load config from .env or environment
config = load_config(image_size="1024x768", fps=24, seconds_per_scene=3.0)

# Initialize pipeline
pipeline = VideoPipeline(config=config)

# 1. Zero-Cost generation ($0)
result = pipeline.run(
    prompt="A majestic eagle soaring over snow-capped mountains",
    num_scenes=3,
    style="cinematic nature documentary, golden hour",
    output_name="eagle_flight.mp4",
    on_status=lambda msg: print(f"Progress: {msg}"),
)

# 2. Native Agnes Video 2.5 generation
native_result = pipeline.run(
    prompt="Cyberpunk flying vehicle navigating neon skyscrapers",
    engine="native_video",
    video_seconds="6",
    video_size="1080P",
    output_name="cyber_flight.mp4",
    on_status=lambda msg: print(f"Agnes Video: {msg}"),
)

print(f"Video created at: {native_result.video_path}")
print(f"Total duration: {native_result.total_duration} seconds")
```

---

## 5. Rate Limits & Error Handling

- **Rate Limits (HTTP 429)**: The client automatically retries up to 5 times using exponential backoff with full jitter. If you encounter rate limits on a free account, the generator will wait and resume without failing your job.
- **Visual Continuity**: When continuity is enabled (default in Zero-Cost mode), scene 2+ provides the prior scene's image URL into `extra_body.image` of `agnes-image-2.0-flash` ($0 promotional price), keeping subjects and color palettes coherent.
- **Asynchronous Task Polling**: For Agnes Video 2.5, tasks are created via `POST /v1/videos` and queried via `GET /agnesapi` every 2 seconds with automatic progress reporting (0–100%) and error capture.
