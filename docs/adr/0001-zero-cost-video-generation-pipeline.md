# ADR-0001: Zero-Cost Video Generation Pipeline using Agnes Flash Models and FFmpeg

**Date**: 2026-10-21  
**Status**: accepted  
**Deciders**: Engineering Team, User  

## Context

The objective is to achieve unlimited, production-grade video generation from text prompts with strictly **$0 cost** (no paid API usage), accepting standard rate limiting.

Upon analyzing the Agnes AI API documentation:
1. `agnes-video-2.5` (`POST /v1/videos`) is billed per second ($0.025/sec for 720P, $0.040/sec for 1080P/1K, and $0.055/sec for 2K), plus additional fees for excess reference media. There is no free or promotional tier for this endpoint.
2. In contrast, `agnes-2.5-flash` (`POST /v1/chat/completions`) has a promotional pricing of **$0 / 1M tokens** across cached input, input, and output tokens.
3. `agnes-image-2.0-flash` (`POST /v1/images/generations`) has promotional pricing of **$0** across all output resolutions (1K, 2K, 3K, 4K) as well as input reference images, supporting both text-to-image and image-to-image continuity.

## Decision

We will implement a composite zero-cost video generation pipeline that decouples scene direction, image synthesis, and motion assembly:

1. **Scene Breakdown & Storyboard**: Call `agnes-2.5-flash` via `POST /v1/chat/completions` ($0 promotional price) to decompose user prompts into sequential scene shots, keyframe descriptions, visual continuity directives, and camera motion instructions.
2. **Keyframe & Transition Generation**: Call `agnes-image-2.0-flash` via `POST /v1/images/generations` ($0 promotional price):
   - Text-to-image for establishing the opening frame.
   - Image-to-image with reference inputs (`extra_body.image`) to preserve character, style, and lighting continuity across sequential frames.
3. **Local Video Motion & Compilation**: Use local `FFmpeg` to stitch generated image sequences into high-definition MP4 videos, applying Ken Burns pan/zoom motion, crossfade transitions, and 24/30 FPS video timing.
4. **Resilience & Rate Limiting**: Implement exponential backoff and jitter for HTTP 429 and network timeouts to safely operate within Agnes API rate limits without failing user jobs.

## Alternatives Considered

### Alternative 1: Direct Agnes Video API (`agnes-video-2.5`)
- **Pros**: End-to-end AI video diffusion model in a single asynchronous call.
- **Cons**: Strictly paid ($0.025 - $0.055 per second). A single 5-second video costs $0.125 minimum.
- **Why not**: Violates the non-negotiable requirement of strictly $0 cost.

### Alternative 2: Local Open-Source Diffusion Models (e.g., Stable Video Diffusion, AnimateDiff)
- **Pros**: Completely offline and free.
- **Cons**: Requires high-end local GPUs with 16GB+ VRAM, slow rendering on CPU/consumer hardware, and complex local model weights management.
- **Why not**: Agnes image generation is accelerated in the cloud for free ($0), allowing users on any machine with FFmpeg to generate videos without requiring specialized GPU hardware.

## Consequences

### Positive
- **100% Free**: Operates entirely within the free promotional tiers of Agnes AI text and image models.
- **Unlimited Generation**: Users can generate videos repeatedly without balance depletion.
- **High Resolution**: Supports up to 4K resolution image generation and 1080P/4K video output.
- **Deterministic & Lightweight**: FFmpeg provides predictable, reliable video encoding with zero cloud compute cost.

### Negative
- **Multi-step Pipeline**: Requires orchestrating text expansion, image generation, and FFmpeg assembly rather than a single API endpoint.
- **Motion Type**: Motion is synthesized through scene continuity, camera zoom/pan (Ken Burns), and crossfade transitions rather than native 3D diffusion fluid deformation.

### Risks & Mitigations
- **API Rate Limits (HTTP 429)**: Mitigated by implementing automatic retry with exponential backoff and request pacing.
- **Promotional Pricing Changes**: Agnes promotional $0 pricing may be adjusted in the future. The architecture remains modular so that models or endpoints can be swapped via configuration without rewriting application logic.
- **Visual Consistency**: Mitigated by feeding prior frame URLs or Base64 references into `extra_body.image` for image-to-image style anchoring.
