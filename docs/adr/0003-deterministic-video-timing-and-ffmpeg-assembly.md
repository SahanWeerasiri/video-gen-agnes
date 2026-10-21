# ADR-0003: Deterministic Video Timing and FFmpeg ZoomPan Single-Frame Assembly

**Date**: 2026-10-21  
**Status**: accepted  
**Deciders**: Engineering Team, User  

## Context

During multi-scene video synthesis testing, a prompt requesting 3 scenes of 3.0 seconds each exhibited two major timing bugs:
1. Each scene's planned duration defaulted to 4.0s instead of 3.0s.
2. The final rendered MP4 video ballooned to ~23+ seconds rather than the expected 9.0s.

Investigation revealed two interacting root causes:
1. **LLM Schema Bias**: The JSON example in `storyboard.py` hardcoded `"duration": 4.0`. Without explicit per-scene duration constraints in the user message, the model copied the 4.0s example, and the parser accepted the LLM's returned duration.
2. **FFmpeg `zoompan` Frame Multiplication**: The compilation command applied `-loop 1` to single-image inputs. In FFmpeg, `-loop 1` feeds a continuous 25 FPS stream of the same image into the filter graph. Because the `zoompan` filter generates `d` (e.g., 72) output frames for *every incoming input frame*, it generated hundreds of frames per scene, resulting in a ~23-second video when played at 24 FPS.

## Decision

We implement strict end-to-end timing determinism across both prompt engineering and FFmpeg command construction:

1. **Explicit Prompt & Parser Duration Clamping**:
   - In `StoryboardGenerator.generate()`, inject explicit target durations into the prompt:
     `Target duration per scene: {duration_per_scene:.1f} seconds. Each scene must have "duration": {duration_per_scene:.1f}.`
   - In `_parse_response()`, strictly override and clamp scene durations to the user-specified `target_duration`.

2. **Single-Image Input without Looping in `zoompan`**:
   - Remove `-loop 1` on image inputs passed to `zoompan`.
   - Embed the target frame rate directly into the filter string: `zoompan=...:s={width}x{height}:fps={fps}`.
   - Enforce exact frame counts and duration limits via `-frames:v {total_frames}` and `-t {duration:.3f}`.

3. **Lossless Multi-Scene Stitching**:
   - Provide `FFmpegCompiler.concat_clips()` using the FFmpeg concat demuxer (`-f concat -safe 0 -c copy`) to instantly concatenate individual scene MP4 clips without generational quality loss or transcoding overhead.

## Alternatives Considered

### Alternative 1: Complex Multi-Input Crossfade Filter Graph in a Single FFmpeg Command
- **Pros**: Can apply crossfade blending (`xfade`) between scenes.
- **Cons**: Filter graph syntax scales quadratically in complexity with scene count; failure in one scene aborts the entire render; difficult to debug timing drift.
- **Why not**: Rendering individual scenes first with strict frame clamping, then concatenating, isolates failures, runs faster, and guarantees deterministic duration.

### Alternative 2: Static Frame Looping without ZoomPan
- **Pros**: Trivial timing calculation using `-loop 1 -t <duration>`.
- **Cons**: Completely eliminates cinematic camera movement (zoom-in, pan-left, pan-right), degrading output to a static slideshow.
- **Why not**: ZoomPan provides essential production value. Fixing the input stream and filter syntax gives both motion and exact duration.

## Consequences

### Positive
- **Exact Timing**: 3 scenes × 3.0s renders in <0.3s and probes with `ffprobe` to exactly 9.000000s.
- **Automated Verification**: Covered by an automated integration test (`test_real_ffmpeg_compile_exact_duration`) verifying output duration with `ffprobe`.
- **Fast Execution**: Single-image filter pipeline eliminates redundant frame processing, reducing rendering time significantly.

### Negative
- Direct concat demuxer requires identical codecs and resolutions across clips (guaranteed by our internal pipeline).

### Risks & Mitigations
- **Sub-second rounding**: Clamping both `-frames:v` and `-t` prevents FFmpeg container timestamp rounding drift.
