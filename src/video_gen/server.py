"""Flask web server providing an interactive UI and REST API for video generation."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict
from pathlib import Path
import shutil
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, send_from_directory

import video_gen
from video_gen.config import PipelineConfig, load_config
from video_gen.pipeline import ZeroCostVideoPipeline

logger = logging.getLogger(__name__)


def create_app(config: Optional[PipelineConfig] = None) -> Flask:
    """Create and configure the Flask web application."""
    start_time = time.time()
    base_dir = Path(__file__).parent
    template_folder = base_dir / "templates"
    static_folder = base_dir / "static"

    app = Flask(
        __name__,
        template_folder=str(template_folder),
        static_folder=str(static_folder),
    )

    app.config["PIPELINE_CONFIG"] = config or load_config()
    tasks: dict[str, dict[str, Any]] = {}
    tasks_lock = threading.Lock()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health", methods=["GET"])
    @app.route("/api/health", methods=["GET"])
    def health_check():
        cfg: PipelineConfig = app.config["PIPELINE_CONFIG"]
        has_key = bool(cfg.api_key and cfg.api_key != "your_agnes_api_key_here")
        ffmpeg_available = bool(shutil.which("ffmpeg"))
        uptime = round(time.time() - start_time, 2)

        return jsonify({
            "status": "healthy",
            "server": "Agnes Studio",
            "version": getattr(video_gen, "__version__", "0.1.0"),
            "uptime_seconds": uptime,
            "ffmpeg_installed": ffmpeg_available,
            "has_api_key": has_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @app.route("/api/config", methods=["GET"])
    def get_config():
        cfg: PipelineConfig = app.config["PIPELINE_CONFIG"]
        has_key = bool(cfg.api_key and cfg.api_key != "your_agnes_api_key_here")
        masked_key = (
            f"{cfg.api_key[:4]}...{cfg.api_key[-4:]}"
            if has_key and len(cfg.api_key) > 8
            else ("Set" if has_key else "Missing")
        )

        return jsonify({
            "has_api_key": has_key,
            "masked_key": masked_key,
            "base_url": cfg.base_url,
            "text_model": cfg.text_model,
            "image_model": cfg.image_model,
            "video_model": cfg.video_model,
            "default_engine": cfg.engine,
            "default_size": cfg.image_size,
            "default_fps": cfg.fps,
            "default_duration": cfg.seconds_per_scene,
            "default_video_seconds": cfg.video_seconds,
            "default_video_size": cfg.video_size,
            "default_video_aspect": cfg.video_aspect_ratio,
            "default_video_mode": cfg.video_mode,
        })

    @app.route("/api/generate", methods=["POST"])
    def start_generation():
        cfg: PipelineConfig = app.config["PIPELINE_CONFIG"]
        data = request.get_json() or {}

        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        engine = str(data.get("engine", cfg.engine))
        scenes = int(data.get("scenes", 4))
        duration = float(data.get("duration", cfg.seconds_per_scene))
        size = str(data.get("size", cfg.image_size))
        style = data.get("style") or None
        fps = int(data.get("fps", cfg.fps))
        enable_motion = bool(data.get("enable_motion", True))
        use_continuity = bool(data.get("use_continuity", True))
        dry_run = bool(data.get("dry_run", False))

        video_seconds = str(data.get("video_seconds", cfg.video_seconds))
        video_size = str(data.get("video_size", cfg.video_size))
        video_aspect_ratio = str(data.get("video_aspect_ratio", cfg.video_aspect_ratio))
        video_mode = str(data.get("video_mode", cfg.video_mode))

        task_id = str(uuid.uuid4())
        task_output_dir = cfg.output_dir / task_id

        task_state: dict[str, Any] = {
            "task_id": task_id,
            "status": "queued",
            "progress": 0,
            "stage": "Initializing...",
            "logs": [],
            "storyboard": None,
            "frames": [],
            "video_url": None,
            "error": None,
            "prompt": prompt,
            "engine": engine,
            "dry_run": dry_run,
        }

        with tasks_lock:
            tasks[task_id] = task_state

        def run_task():
            with tasks_lock:
                tasks[task_id]["status"] = "running"
                tasks[task_id]["progress"] = 5
                tasks[task_id]["stage"] = (
                    "Initializing Agnes Video 2.5 AI diffusion..."
                    if engine == "native_video"
                    else "Planning storyboard with agnes-2.5-flash ($0)..."
                )
                tasks[task_id]["logs"].append(f"Started video generation task (engine: {engine})")

            def on_status(msg: str):
                import re
                with tasks_lock:
                    tasks[task_id]["logs"].append(msg)
                    prog_match = re.search(r"progress:\s*(\d+)%", msg)
                    if prog_match:
                        pct = int(prog_match.group(1))
                        # Scale progress between 15% and 90%
                        scaled_pct = 15 + int(pct * 0.75)
                        tasks[task_id]["progress"] = scaled_pct
                        tasks[task_id]["stage"] = msg
                    elif "Planning scene storyboard" in msg:
                        tasks[task_id]["progress"] = 15
                        tasks[task_id]["stage"] = "Designing storyboard & scenes..."
                    elif "Generating" in msg and "frames" in msg:
                        tasks[task_id]["progress"] = 35
                        tasks[task_id]["stage"] = "Synthesizing keyframe images..."
                    elif "Generated frame" in msg:
                        current_prog = tasks[task_id]["progress"]
                        tasks[task_id]["progress"] = min(80, current_prog + 10)
                        tasks[task_id]["stage"] = msg
                    elif "Submitting native video task" in msg:
                        tasks[task_id]["progress"] = 15
                        tasks[task_id]["stage"] = "Submitting task to Agnes Video 2.5..."
                    elif "Downloading generated video" in msg or "Downloading video" in msg:
                        tasks[task_id]["progress"] = 92
                        tasks[task_id]["stage"] = "Downloading generated video..."
                    elif "Compiling frames" in msg or "Stitching multi-scene" in msg:
                        tasks[task_id]["progress"] = 85
                        tasks[task_id]["stage"] = "Rendering / stitching MP4 with FFmpeg..."
                    elif "Video generated successfully" in msg:
                        tasks[task_id]["progress"] = 100
                        tasks[task_id]["stage"] = "Complete!"

            try:
                task_config = PipelineConfig(
                    api_key=cfg.api_key,
                    base_url=cfg.base_url,
                    text_model=cfg.text_model,
                    image_model=cfg.image_model,
                    video_model=cfg.video_model,
                    engine=engine,
                    image_size=size,
                    video_seconds=video_seconds,
                    video_size=video_size,
                    video_aspect_ratio=video_aspect_ratio,
                    video_mode=video_mode,
                    fps=fps,
                    seconds_per_scene=duration,
                    output_dir=task_output_dir,
                )

                pipeline = ZeroCostVideoPipeline(config=task_config)
                result = pipeline.run(
                    prompt=prompt,
                    num_scenes=scenes,
                    style=style,
                    output_name="video.mp4",
                    enable_motion=enable_motion,
                    use_continuity=use_continuity,
                    dry_run=dry_run,
                    engine=engine,
                    video_seconds=video_seconds,
                    video_size=video_size,
                    video_aspect_ratio=video_aspect_ratio,
                    video_mode=video_mode,
                    on_status=on_status,
                )

                frame_items = []
                for f in result.frames:
                    frame_items.append({
                        "scene_index": f.scene_index,
                        "url": f"/media/{task_id}/frames/{f.image_path.name}",
                        "prompt": f.prompt,
                        "camera_motion": f.camera_motion,
                        "duration": f.duration,
                    })

                with tasks_lock:
                    tasks[task_id]["status"] = "completed"
                    tasks[task_id]["progress"] = 100
                    tasks[task_id]["stage"] = "Finished successfully"
                    tasks[task_id]["storyboard"] = {
                        "title": result.storyboard.title,
                        "summary": result.storyboard.summary,
                        "scenes": [asdict(s) for s in result.storyboard.scenes],
                    }
                    tasks[task_id]["frames"] = frame_items
                    if result.video_path:
                        tasks[task_id]["video_url"] = f"/media/{task_id}/video.mp4"

            except Exception as e:
                logger.exception("Error executing video generation task %s", task_id)
                with tasks_lock:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = str(e)
                    tasks[task_id]["stage"] = f"Failed: {e}"
                    tasks[task_id]["logs"].append(f"ERROR: {e}")

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return jsonify({"task_id": task_id, "status": "queued"}), 202

    @app.route("/api/task/<task_id>", methods=["GET"])
    def get_task_status(task_id: str):
        with tasks_lock:
            task = tasks.get(task_id)
            if not task:
                return jsonify({"error": "Task not found"}), 404
            return jsonify(task)

    @app.route("/media/<task_id>/<path:filename>")
    def serve_media(task_id: str, filename: str):
        cfg: PipelineConfig = app.config["PIPELINE_CONFIG"]
        task_dir = cfg.output_dir / task_id
        return send_from_directory(str(task_dir.resolve()), filename)

    return app


def main() -> None:
    """Run the Flask development server."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    app = create_app()
    port = 5000
    print(f"\n🚀 Agnes AI Video Generator Web UI starting at: http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
