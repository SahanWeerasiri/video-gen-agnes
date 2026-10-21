"""Command-line interface for the zero-cost Agnes video generator."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from video_gen.config import load_config
from video_gen.pipeline import ZeroCostVideoPipeline


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="video-gen-agnes",
        description="Generate unlimited videos with $0 cost using Agnes AI Flash models and FFmpeg.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-p", "--prompt",
        type=str,
        required=True,
        help="Text prompt or concept describing the video.",
    )
    parser.add_argument(
        "-n", "--scenes",
        type=int,
        default=4,
        help="Number of scenes to plan and generate.",
    )
    parser.add_argument(
        "-d", "--duration",
        type=float,
        default=4.0,
        help="Duration in seconds per scene.",
    )
    parser.add_argument(
        "-s", "--size",
        type=str,
        default="1024x768",
        choices=["1024x768", "1024x1024", "768x1024"],
        help="Output resolution for generated frames and final video.",
    )
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Artistic style instruction (e.g., 'cinematic cyberpunk', 'studio ghibli anime', 'photorealistic').",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        help="Video frame rate.",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="zero_cost",
        choices=["zero_cost", "native_video"],
        help="Generation engine: 'zero_cost' (Flash + FFmpeg Ken Burns) or 'native_video' (Agnes Video 2.5 AI diffusion).",
    )
    parser.add_argument(
        "--video-seconds",
        type=str,
        default="5",
        help="Video duration in seconds for native video ('4'–'12').",
    )
    parser.add_argument(
        "--video-size",
        type=str,
        default="720P",
        choices=["720P", "1080P", "1K", "2K"],
        help="Output resolution tier for native Agnes Video 2.5.",
    )
    parser.add_argument(
        "--video-aspect-ratio",
        type=str,
        default="16:9",
        choices=["16:9", "9:16", "1:1", "4:3", "21:9"],
        help="Aspect ratio for native video generation.",
    )
    parser.add_argument(
        "--video-mode",
        type=str,
        default="text",
        choices=["text", "keyframe", "reference"],
        help="Generation mode for native Agnes Video 2.5.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory to store storyboard, frames, and final video.",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="video.mp4",
        help="Filename for the compiled MP4 video.",
    )
    parser.add_argument(
        "--no-motion",
        action="store_true",
        help="Disable Ken Burns zoom/pan camera dynamics (renders slideshow instead).",
    )
    parser.add_argument(
        "--no-continuity",
        action="store_true",
        help="Disable sequential image-to-image style anchoring.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan and save storyboard JSON without invoking image generation or FFmpeg.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Agnes API Key override (defaults to AGNES_API_KEY from environment or .env).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the CLI."""
    args = parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        config = load_config(
            api_key=args.api_key,
            engine=args.engine,
            image_size=args.size,
            video_seconds=args.video_seconds,
            video_size=args.video_size,
            video_aspect_ratio=args.video_aspect_ratio,
            video_mode=args.video_mode,
            fps=args.fps,
            seconds_per_scene=args.duration,
            output_dir=args.output_dir,
        )

        pipeline = ZeroCostVideoPipeline(config=config)

        print("\n" + "=" * 60)
        if args.engine == "native_video":
            print("🎬 AGNES VIDEO 2.5 (Native AI Diffusion Video)")
            print("=" * 60)
            print(f"Prompt:       {args.prompt}")
            print(f"Engine:       Agnes Video 2.5 (native_video)")
            print(f"Video Spec:   {args.video_seconds}s @ {args.video_size} ({args.video_aspect_ratio})")
            print(f"Mode:         {args.video_mode} mode")
            if args.scenes > 1:
                print(f"Multi-Scene:  {args.scenes} scenes stitched via FFmpeg")
        else:
            print("🎬 AGNES ZERO-COST VIDEO GENERATOR ($0 Unlimited)")
            print("=" * 60)
            print(f"Prompt:       {args.prompt}")
            print(f"Engine:       Zero-Cost Flash + Ken Burns FFmpeg ($0)")
            print(f"Scenes:       {args.scenes} scenes (~{args.scenes * args.duration:.1f}s total)")
            print(f"Resolution:   {args.size} @ {args.fps} FPS")
            print(f"Motion:       {'Enabled (Ken Burns)' if not args.no_motion else 'Disabled (Static)'}")
            print(f"Continuity:   {'Enabled (Img2Img anchor)' if not args.no_continuity else 'Disabled'}")
        if args.style:
            print(f"Style:        {args.style}")
        print(f"Output Dir:   {args.output_dir.resolve()}")
        print("=" * 60 + "\n")

        result = pipeline.run(
            prompt=args.prompt,
            num_scenes=args.scenes,
            style=args.style,
            output_name=args.output_name,
            enable_motion=not args.no_motion,
            use_continuity=not args.no_continuity,
            dry_run=args.dry_run,
            engine=args.engine,
            video_seconds=args.video_seconds,
            video_size=args.video_size,
            video_aspect_ratio=args.video_aspect_ratio,
            video_mode=args.video_mode,
            on_status=lambda msg: print(f"  ➜ {msg}"),
        )

        print("\n" + "-" * 60)
        print("✅ Generation Summary:")
        print(f"   Title:   {result.storyboard.title}")
        print(f"   Summary: {result.storyboard.summary}")
        for s in result.storyboard.scenes:
            print(f"   Scene {s.index} ({s.duration}s): {s.description}")

        if result.video_path:
            print(f"\n🎉 Video Ready: {result.video_path.resolve()}")
        print("-" * 60 + "\n")
        return 0

    except Exception as e:
        print(f"\n❌ Execution failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
