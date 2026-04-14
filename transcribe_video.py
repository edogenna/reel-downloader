#!/usr/bin/env python3
"""Transcribe the audio from a local MP4 video file.

Install the dependency before running:
    pip install -U openai-whisper

You also need FFmpeg installed on your system.
On macOS with Homebrew:
    brew install ffmpeg

Example usage:
    python transcribe_video.py input.mp4
    python transcribe_video.py input.mp4 --output transcript.txt
    python transcribe_video.py input.mp4 --model small
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


DEFAULT_MODEL = "base"


def load_whisper_module():
    try:
        return importlib.import_module("whisper")
    except ModuleNotFoundError:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe the audio from a local MP4 video file."
    )
    parser.add_argument("video", help="Path to the input MP4 video file")
    parser.add_argument(
        "--output",
        help="Path to the transcript text file (default: same name as the video)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Whisper model to use (tiny, base, small, medium, large)",
    )
    return parser.parse_args()


def resolve_output_path(video_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)
    return video_path.with_name(f"{video_path.stem}_trasncription.txt")


def transcribe_video(video_path: Path, model_name: str) -> str:
    whisper = load_whisper_module()
    if whisper is None:
        raise ModuleNotFoundError("openai-whisper is not installed")

    model = whisper.load_model(model_name)
    result = model.transcribe(str(video_path))
    return result.get("text", "").strip()


def main() -> int:
    args = parse_args()

    whisper = load_whisper_module()
    if whisper is None:
        print("Missing dependency: install it with 'pip install -U openai-whisper'.")
        return 1

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Input file not found: {video_path}")
        return 1

    if video_path.suffix.lower() != ".mp4":
        print("Warning: the input file does not have an .mp4 extension, but it will still be processed.")

    output_path = resolve_output_path(video_path, args.output)

    try:
        transcript = transcribe_video(video_path, args.model)
        output_path.write_text(transcript + "\n", encoding="utf-8")
        print(f"Transcript saved to {output_path}")
        print("\n--- Transcript ---\n")
        print(transcript)
        return 0
    except FileNotFoundError as exc:
        print(f"FFmpeg or input file missing: {exc}")
    except Exception as exc:  # noqa: BLE001 - keep CLI errors readable
        print(f"Unexpected error while transcribing: {exc}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
