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
- Test creative ideas with 1-click prompt chips.
- Adjust scenes, durations, resolution, and styles interactively.
- Track real-time progress and logs.
- Watch and download generated videos directly in your browser.

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
| `-n`, `--scenes` | `int` | `4` | Number of sequential scenes to plan and generate. |
| `-d`, `--duration`| `float` | `4.0` | Duration in seconds per scene. |
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

### 3.1 Previewing Storyboard (Dry Run - Zero API Image Calls)
Check how `agnes-2.5-flash` interprets your prompt and breaks it into scenes before generating images:
```bash
python -m video_gen --prompt "A lone astronaut exploring a crystal cave on Mars" --dry-run
```
Outputs `output/storyboard.json` with scene breakdowns, camera directions, and visual prompts.

### 3.2 Full Video Generation
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

### 3.3 Square Social Video (1:1 Aspect Ratio)
For Instagram / TikTok feed square format:
```bash
python -m video_gen \
  --prompt "A cute red panda wearing a chef hat making ramen in a cozy Tokyo shop" \
  --style "studio ghibli animation style" \
  --size "1024x1024" \
  --output-name "red_panda_chef.mp4"
```

---

## 4. Python API Usage

You can also integrate the pipeline directly into Python applications:

```python
from video_gen import ZeroCostVideoPipeline, load_config

# Load config from .env or environment
config = load_config(image_size="1024x768", fps=24, seconds_per_scene=3.5)

# Initialize pipeline
pipeline = ZeroCostVideoPipeline(config=config)

# Run end-to-end generation
result = pipeline.run(
    prompt="A majestic eagle soaring over snow-capped mountains",
    num_scenes=3,
    style="cinematic nature documentary, golden hour",
    output_name="eagle_flight.mp4",
    on_status=lambda msg: print(f"Progress: {msg}"),
)

print(f"Video created at: {result.video_path}")
print(f"Total duration: {result.total_duration} seconds")
```

---

## 5. Rate Limits & Error Handling

- **Rate Limits (HTTP 429)**: The client automatically retries up to 5 times using exponential backoff with full jitter. If you encounter rate limits on a free account, the generator will wait and resume without failing your job.
- **Visual Continuity**: When continuity is enabled (default), scene 2+ provides the prior scene's image URL into `extra_body.image` of `agnes-image-2.0-flash` ($0 promotional price), keeping subjects and color palettes coherent.
