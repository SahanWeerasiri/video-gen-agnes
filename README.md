# Zero-Cost & Native AI Video Generator

A modular, production-ready AI video generator built to support **two flexible creation engines**:
1. **Zero-Cost Engine ($0 Unlimited)**: Employs the promotional free pricing of Agnes AI Flash models (`agnes-2.5-flash` + `agnes-image-2.0-flash`) combined with local FFmpeg Ken Burns animation and stitching.
2. **Native Agnes Video 2.5 Engine**: Direct integration with the official `agnes-video-2.5` diffusion model (`POST /v1/videos` and asynchronous polling via `GET /agnesapi`) for realistic subject motion, physical dynamics, and multi-scene cinematic films.

Includes both a **modern, responsive Web Studio UI** with real-time progress tracking and a **rich CLI tool**.

---

## 💡 Dual-Engine Architecture

| Feature | Zero-Cost Engine (`zero_cost`) | Native Agnes Video Engine (`native_video`) |
| :--- | :--- | :--- |
| **Primary Model** | `agnes-2.5-flash` + `agnes-image-2.0-flash` | `agnes-video-2.5` |
| **Pricing / Cost** | **Strictly $0** (Free promotional tiers) | Assumed free / API credits |
| **Motion Synthesis**| Ken Burns 2D/3D camera zoom & pan via local FFmpeg | Native video diffusion subject & camera motion |
| **Assembly Mode** | Sequential keyframes + continuity anchoring | Single continuous clip (4–12s) or multi-scene stitched film |
| **Resolutions** | 1024x768, 1024x1024, 768x1024 | 720P, 1080P, 1K, 2K |
| **Aspect Ratios** | 4:3, 1:1, 3:4 | 16:9, 9:16, 1:1, 4:3, 21:9 |
| **Hardware Reqs** | Zero local GPU needed; runs on any CPU with FFmpeg | Zero local GPU needed (cloud diffusion) |

```
┌─────────────────────────────────────────────────────────────┐
│                       User Prompt                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
               Select Generation Engine
              ┌────────────────┴────────────────┐
              ▼                                 ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│     Zero-Cost Engine      │     │    Native Agnes Video     │
│  agnes-2.5-flash ($0)     │     │     agnes-video-2.5       │
│  agnes-image-2.0-flash    │     │  Asynchronous Cloud API   │
│  FFmpeg Ken Burns ($0)    │     │  Direct or Multi-Scene    │
└─────────────┬─────────────┘     └─────────────┬─────────────┘
              │                                 │
              └────────────────┬────────────────┘
                               ▼
              ┌─────────────────────────────────┐
              │         Final MP4 Video         │
              └─────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Requirements
* **Python 3.10+** (tested on Python 3.14)
* **FFmpeg** installed on your system (`ffmpeg -version`)

### 2. Set Up Virtual Environment (`.venv`)
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy `.env.example` to `.env` and provide your Agnes API key:
```bash
cp .env.example .env
```
In `.env`:
```dotenv
AGNES_API_KEY=your_api_key_here
AGNES_BASE_URL=https://apihub.agnes-ai.com/v1
```

---

## 🌐 Launch the Interactive Web Studio UI

Start the local web server:
```bash
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

### Web Studio Features
* **Server Health & Heartbeat**: Real-time server connectivity indicator (`/health` and `/api/health`) tracking backend uptime and FFmpeg status.
* **Interactive Prompt Playground**: Auto-expanding prompt input with 1-click inspirational starter chips (Cyberpunk, Studio Ghibli, Nature Documentary, Sci-Fi).
* **Visual Style Presets**: Quick pills for Cinematic 8K, Cyberpunk, Studio Ghibli, Photorealistic, Anime, and 35mm Vintage Film.
* **Aspect Ratio Cards**: Instant switching between 4:3 Landscape (`1024x768`), 1:1 Square (`1024x1024`), and 3:4 Portrait (`768x1024`).
* **Live Multi-Stage Tracker**: Real-time progress bar, stage transitions, and live terminal event stream.
* **Integrated Player & Gallery**: HTML5 video playback with download button alongside a visual gallery displaying the generated frame for each scene!

---

## 💻 CLI Usage

You can also run the generator directly from the command line:

```bash
# Preview storyboard only (Dry run: no images generated)
python -m video_gen --prompt "A cybernetic tiger prowling in neon rain" --dry-run

# Generate a full 4-scene cinematic video
python -m video_gen \
  --prompt "A cybernetic tiger prowling through a rainy neon city" \
  --style "cinematic cyberpunk, photorealistic, 8k" \
  --scenes 4 \
  --duration 4.0 \
  --output-name "cyber_tiger.mp4"
```

### CLI Options

| Option | Default | Description |
| :--- | :--- | :--- |
| `-p, --prompt` | *Required* | Concept or description for the video. |
| `-n, --scenes` | `4` | Number of sequential scenes. |
| `-d, --duration`| `4.0` | Seconds per scene. |
| `-s, --size` | `1024x768` | Resolution tier (`1024x768`, `1024x1024`, `768x1024`). |
| `--style` | `None` | Visual style directive (e.g. `anime`, `cyberpunk`, `documentary`). |
| `--fps` | `24` | Video frames per second. |
| `-o, --output-dir`| `output` | Output directory for storyboard, frames, and video. |
| `--output-name` | `video.mp4` | Filename of the output MP4. |
| `--no-motion` | `False` | Disables camera zoom/pan (renders static slideshow). |
| `--no-continuity`| `False` | Disables sequential image-to-image style anchoring. |
| `--dry-run` | `False` | Generates and saves storyboard without image synthesis. |
| `-v, --verbose` | `False` | Enables debug logging. |

---

## 🧪 Testing

The unit test suite runs with 100% mocked dependencies — **no network calls are made and no API credits are consumed**:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

---

## 📁 Repository Structure

```
.
├── app.py                 # Web application launcher (python app.py)
├── requirements.txt       # Project dependencies (requests, flask)
├── .venv/                 # Local Python virtual environment
├── src/video_gen/
│   ├── __init__.py        # Package exports & version
│   ├── config.py          # Configuration & environment loading
│   ├── client.py          # Agnes API client with 429 rate limit backoff
│   ├── storyboard.py      # agnes-2.5-flash scene & prompt planner
│   ├── frame_generator.py # agnes-image-2.0-flash frame generator with continuity
│   ├── compiler.py        # FFmpeg Ken Burns motion compilation
│   ├── pipeline.py        # End-to-end orchestration pipeline
│   ├── server.py          # Flask REST API & Web Server
│   ├── cli.py             # Rich CLI interface
│   ├── static/            # Frontend assets (style.css, app.js)
│   └── templates/         # Web Studio UI (index.html)
├── tests/                 # Unit test suite (46 tests, fully mocked)
├── docs/
│   ├── adr/               # Architecture Decision Records
│   │   ├── README.md
│   │   ├── 0001-zero-cost-video-generation-pipeline.md
│   │   └── 0002-native-agnes-video-engine.md
│   ├── agnes/             # Agnes AI API documentation
│   ├── architecture.md    # System architecture specification
│   └── usage.md           # User manual and advanced examples
├── AGENTS.md              # Engineering guidelines
└── README.md              # Project documentation
```

---

## 📖 Architecture & Documentation
* [ADR-0001: Zero-Cost Video Generation Pipeline](docs/adr/0001-zero-cost-video-generation-pipeline.md)
* [ADR-0002: Dual-Engine Architecture Supporting Native Agnes Video 2.5](docs/adr/0002-native-agnes-video-engine.md)
* [System Architecture](docs/architecture.md)
* [Usage Guide & Manual](docs/usage.md)
