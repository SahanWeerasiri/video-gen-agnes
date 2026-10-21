# Architecture Decision Records (ADRs)

Architecture Decision Records (ADRs) capture important architectural choices made during the lifecycle of this project.

## Index of Decisions

| ADR | Title | Status | Date |
|:---:|:------|:------:|:----:|
| [0001](0001-zero-cost-video-generation-pipeline.md) | Zero-Cost Video Generation Pipeline using Agnes Flash Models and FFmpeg | accepted | 2026-10-21 |
| [0002](0002-native-agnes-video-engine.md) | Dual-Engine Architecture Supporting Native Agnes Video 2.5 and Zero-Cost FFmpeg Pipeline | accepted | 2026-10-21 |
| [0003](0003-deterministic-video-timing-and-ffmpeg-assembly.md) | Deterministic Video Timing and FFmpeg ZoomPan Single-Frame Assembly | accepted | 2026-10-21 |
| [0004](0004-interactive-web-studio-and-asynchronous-task-architecture.md) | Interactive Web Studio and Asynchronous Task Architecture | accepted | 2026-10-21 |
| [0005](0005-api-quota-enforcement-and-graceful-error-handling.md) | API Quota Enforcement and Graceful Error Handling for Agnes AI Services | accepted | 2026-10-21 |

---

## How to Add a New ADR

1. Duplicate the template format: `docs/adr/XXXX-title-with-dashes.md`.
2. Follow the standard sections:
   - **Context:** The problem or design decision we faced.
   - **Alternatives Considered:** Options analyzed and evaluated.
   - **Decision:** The chosen path and rationale.
   - **Consequences:** Positive and negative trade-offs.
