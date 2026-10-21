# ADR-0004: Interactive Web Studio and Asynchronous Task Architecture

**Date**: 2026-10-21  
**Status**: accepted  
**Deciders**: Engineering Team, User  

## Context

Video generation combines multi-step AI orchestration (LLM storyboarding, high-resolution keyframe synthesis, and FFmpeg encoding or cloud diffusion polling). These tasks typically require 10 to 90 seconds to complete.

Operating solely via the CLI is insufficient for non-technical users or creative iteration. Furthermore, running long tasks over synchronous HTTP requests causes browser connection timeouts, prevents real-time user feedback, and risks aborting in-flight generation jobs if a client disconnects.

## Decision

We implement a decoupled, asynchronous Web Studio UI and REST API:

1. **Lightweight Flask Server with Background Threading**:
   - Use Flask as a lightweight, zero-boilerplate web server (`src/video_gen/server.py`).
   - Offload video generation jobs to background worker threads (`threading.Thread(target=run_task, daemon=True)`).
   - Return `HTTP 202 Accepted` immediately upon job submission with a unique `task_id` (UUID4).

2. **In-Memory Thread-Safe Task Registry**:
   - Track job state in an in-memory dictionary protected by `threading.Lock()`.
   - Maintain state fields: `status`, `progress` (0–100%), `stage`, `logs`, `storyboard`, `frames`, `video_url`, and `error`.

3. **Short-Polling and Progress Regex Extraction**:
   - The frontend polls `GET /api/task/<task_id>` every 1.5 seconds.
   - The server inspects pipeline status logs with regex (`progress:\s*(\d+)%`) to dynamically map cloud diffusion progress into the UI progress bar.

4. **Proactive Health Monitoring**:
   - Provide `/health` and `/api/health` endpoints returning server version, uptime, FFmpeg installation status, and API key configuration.
   - The UI polls `/api/health` every 10 seconds to update a live pulsating status badge.

5. **Aesthetic Vanilla CSS Glassmorphic UI**:
   - Built with Vanilla CSS design tokens (custom properties), dark glassmorphism (`backdrop-filter: blur`), modern typography (`Outfit`, `Inter`, `JetBrains Mono`), prompt inspiration chips, and interactive aspect ratio cards.

## Alternatives Considered

### Alternative 1: Server-Sent Events (SSE) or WebSockets
- **Pros**: Push-based real-time updates.
- **Cons**: Requires persistent connection handling, proxy configuration issues with WSGI dev servers, and reconnect complexity.
- **Why not**: Short-polling at 1.5s intervals is simple, robust against network drops, stateless, and adds negligible load for local/single-user studio usage.

### Alternative 2: External Distributed Task Queue (Celery + Redis)
- **Pros**: Persistent task queues, multi-worker scaling, automatic process recovery.
- **Cons**: Requires running external Redis or RabbitMQ broker daemons, drastically increasing setup friction.
- **Why not**: Violates the principle of lightweight local execution without external infrastructure dependencies.

## Consequences

### Positive
- **Instant Responsiveness**: The browser never hangs or times out.
- **Live Observability**: Users see real-time progress percentages, stages, and console logs as each scene is generated.
- **Zero Heavy Dependencies**: Operates with standard Python libraries and lightweight Flask without external brokers.
- **Self-Healing UI**: Health checks alert the user immediately if the backend server terminates.

### Negative
- Task states are in-memory; restarting the Flask server clears task history (acceptable for a desktop studio application; generated videos remain persisted on disk in `output/`).

### Risks & Mitigations
- **Resource Exhaustion**: Daemon threads are bounded by user interaction; output directories are organized per task ID (`output/<uuid>/`).
