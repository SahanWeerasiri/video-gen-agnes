# Video Generation Architecture

## Overview

This project provides a **strictly $0, unlimited video generation pipeline** leveraging promotional free endpoints from Agnes AI, combined with local FFmpeg video synthesis.

```
┌────────────────────────────────┐
│         User Prompt            │
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│   Storyboard Generator         │  <-- agnes-2.5-flash ($0 / 1M tokens)
│   (Scene & Prompt Planning)    │
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│   Frame Generator              │  <-- agnes-image-2.0-flash ($0 all resolutions)
│   (Text2Img + Img2Img Anchor)  │
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│   FFmpeg Compiler              │  <-- Local execution ($0 compute cost)
│   (Pan/Zoom, Transitions, MP4) │
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│       Final Video (.mp4)       │
└────────────────────────────────┘
```

## Core Components

### 1. Configuration & Client (`video_gen.config`, `video_gen.client`)
- Manages credentials via `AGNES_API_KEY` without hardcoding or leaking secrets.
- Targets the Agnes Base URL `https://apihub.agnes-ai.com/v1`.
- Built-in exponential backoff with full jitter to transparently handle HTTP 429 rate limits.

### 2. Storyboard Engine (`video_gen.storyboard`)
- Uses `agnes-2.5-flash` to expand a brief prompt into a structured multi-scene storyboard.
- Produces image prompts optimized for `agnes-image-2.0-flash`: `[Subject] + [Scene] + [Style] + [Lighting] + [Composition] + [Quality]`.

### 3. Frame Synthesis (`video_gen.frame_generator`)
- Generates establishing shots using text-to-image.
- Applies image-to-image (`extra_body.image`) for subsequent frames to preserve character, lighting, and style consistency.

### 4. FFmpeg Video Compiler (`video_gen.compiler`)
- Stitches the generated scene frames into smooth MP4 videos.
- Applies Ken Burns zoom/pan motion and crossfade transitions.
