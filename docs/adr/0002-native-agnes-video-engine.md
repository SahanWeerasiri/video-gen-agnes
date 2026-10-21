# ADR-0002: Dual-Engine Architecture Supporting Native Agnes Video 2.5 and Zero-Cost FFmpeg Pipeline

**Date**: 2026-10-21  
**Status**: accepted  
**Deciders**: Engineering Team, User  

## Context

In ADR-0001, we established a strictly zero-cost ($0) pipeline combining `agnes-2.5-flash` for storyboarding, `agnes-image-2.0-flash` for keyframe generation, and local `FFmpeg` for Ken Burns animation and stitching.

However, users also need true generative AI video synthesis featuring realistic physical dynamics, fluid subject motion, and camera tracking directly from video diffusion models. The official Agnes AI API provides `agnes-video-2.5` through `POST /v1/videos` and asynchronous polling via `GET /agnesapi?video_id=<ID>&model_name=agnes-video-2.5`.

The user instructed to assume native video generation is free/viable and build support for direct AI video generation alongside the zero-cost pipeline.

## Decision

We will implement a unified **Dual-Engine Architecture** that supports both generation modalities seamlessly across the CLI, Python API, and Web Studio UI:

1. **Engine 1: Hybrid Zero-Cost (`zero_cost`)**
   - Retains the 100% free promotional pipeline (`agnes-2.5-flash` + `agnes-image-2.0-flash` + FFmpeg).
   - Ideal for unlimited rapid prototyping, long presentations, and local offline-rendered slideshows.

2. **Engine 2: Native Agnes Video 2.5 (`native_video`)**
   - Directly integrates with the official Agnes Video 2.5 asynchronous API:
     - Task creation via `POST /v1/videos` with parameters: `model="agnes-video-2.5"`, `mode` (`text`, `keyframe`, `reference`), `seconds` ("4" to "12"), `size` ("720P", "1080P", "1K", "2K"), and `aspect_ratio` ("16:9", "9:16", "1:1").
     - Polling with exponential backoff on `GET /agnesapi?video_id=<ID>&model_name=agnes-video-2.5` tracking task `status` and `progress` (0–100%).
     - Automated asset streaming and download of the finished MP4 video into the project output folder.
   - Supports both:
     - **Direct Mode**: Single continuous AI video clip generated directly from the user's prompt (4–12s).
     - **Multi-Scene Storyboard Mode**: Storyboard planned by `agnes-2.5-flash`, each scene generated as a separate native video clip via `agnes-video-2.5`, then stitched cleanly with FFmpeg into an extended multi-scene movie.

3. **Client & Pipeline Abstraction**:
   - `AgnesClient` gains typed methods: `create_video_task()`, `get_video_task()`, `wait_for_video()`, and `download_video()`.
   - `VideoPipeline` dynamically dispatches to either the hybrid zero-cost compiler or the native Agnes video workflow based on `PipelineConfig.engine`.
   - Web Studio UI exposes an intuitive Engine Toggle and parameter panel with real-time asynchronous polling progress bars.

## Alternatives Considered

### Alternative 1: Replace Zero-Cost Pipeline Entirely
- **Why not**: Discarding the zero-cost pipeline would eliminate the ability for users to generate unlimited free videos with promotional image endpoints. Dual-engine keeps both available.

### Alternative 2: Separate Standalone CLI / Web Service for Video
- **Why not**: Fragmenting into two separate codebases or CLIs would increase maintenance overhead, duplicate HTTP retry logic, and complicate the user experience. A unified interface is significantly cleaner.

## Consequences

### Positive
- **Maximum Versatility**: Users can choose between 100% free unlimited Ken Burns animation or cutting-edge AI video diffusion in a single click or CLI flag.
- **Standards-Compliant**: Fully adheres to the official Agnes Video 2.5 API documentation.
- **Rich User Experience**: Real-time progress percentage in the Web UI and CLI progress bars during video generation.
- **Future-Proof**: Enables keyframe image-to-video (`first_frame`, `last_frame`) and multimodal reference video generation.

### Negative / Trade-offs
- Native video generation requires asynchronous polling (typically 30–90 seconds per clip) compared to quick image-only generation.
- **Strict Paid Billing Requirement (Validated in Production)**: Live API testing confirmed that `POST /v1/videos` strictly enforces billing quota, returning `HTTP 403: {"code":"insufficient_user_quota","message":"Insufficient user quota, remaining: ＄0.000000"}` on accounts with zero balance. Unlike `agnes-2.5-flash` and `agnes-image-2.0-flash`, `agnes-video-2.5` has no free promotional tier.

### Risks & Mitigations
- **Quota Exhaustion (HTTP 403)**: Mitigated by providing clear actionable error messaging directing users without funded accounts to the 100% free Zero-Cost engine (`zero_cost`).
- **Network / Polling Timeouts**: Mitigated by exponential backoff on `GET /agnesapi`, configurable timeouts (`video_timeout_sec=600`), and live UI progress display.
