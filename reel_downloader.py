#!/usr/bin/env python3
"""Download a single Instagram Reel video as an MP4 file.

Install the dependency before running:
    pip install instaloader

Example usage:
    python reel_downloader.py "https://www.instagram.com/reel/SHORTCODE/" --username your_username

Authentication:
    You can provide credentials with --username and --password, or set
    IG_USERNAME and IG_PASSWORD in your environment. If password is omitted,
    the script will prompt for it securely.
"""

from __future__ import annotations

import argparse
import getpass
import importlib
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_DOWNLOAD_DIR = Path("downloads")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the MP4 video from an Instagram post or Reel URL."
    )
    parser.add_argument("url", help="Instagram post or Reel URL")
    parser.add_argument(
        "--username",
        default=os.getenv("IG_USERNAME"),
        help="Instagram username (or set IG_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("IG_PASSWORD"),
        help="Instagram password (or set IG_PASSWORD; otherwise you will be prompted)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help="Directory where the MP4 will be saved (default: downloads)",
    )
    return parser.parse_args()


def extract_shortcode(reel_url: str) -> str:
    match = re.search(r"/(?:reel|p)/([A-Za-z0-9_-]+)/?", reel_url)
    if match:
        return match.group(1)

    parsed = urlparse(reel_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] in {"reel", "p"}:
        return parts[1]

    raise ValueError("Invalid Instagram URL: unable to extract shortcode.")


def load_instaloader_module():
    try:
        return importlib.import_module("instaloader")
    except ModuleNotFoundError:
        return None


def build_loader(instaloader_module, username: str | None, password: str | None):
    loader = instaloader_module.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    if username:
        if password is None:
            password = getpass.getpass(f"Instagram password for {username}: ")
        loader.login(username, password)

    return loader


def download_video(loader, video_url: str, output_path: Path) -> None:
    response = loader.context._session.get(video_url, stream=True, timeout=30)
    response.raise_for_status()
    response.raw.decode_content = True

    with output_path.open("wb") as target_file:
        shutil.copyfileobj(response.raw, target_file)


def save_caption(caption: str | None, output_path: Path) -> None:
    if not caption:
        return

    output_path.write_text(caption.strip() + "\n", encoding="utf-8")


def build_base_filename(owner_username: str, shortcode: str) -> str:
    safe_owner = re.sub(r"[^A-Za-z0-9._-]", "_", owner_username)
    return f"{safe_owner}_{shortcode}"


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)

    instaloader_module = load_instaloader_module()
    if instaloader_module is None:
        print("Missing dependency: install it with 'pip install instaloader'.")
        return 1

    insta_exceptions = instaloader_module.exceptions

    try:
        shortcode = extract_shortcode(args.url)
        loader = build_loader(instaloader_module, args.username, args.password)
        post = instaloader_module.Post.from_shortcode(loader.context, shortcode)

        if not post.is_video:
            print("The provided URL does not point to a video Reel.")
            return 1

        output_dir.mkdir(parents=True, exist_ok=True)
        base_filename = build_base_filename(post.owner_username, shortcode)
        output_path = output_dir / f"{base_filename}.mp4"
        download_video(loader, post.video_url, output_path)
        save_caption(post.caption, output_dir / f"{base_filename}.txt")

        print(f"Downloaded video to {output_path}")
        return 0

    except ValueError as exc:
        print(f"Invalid input: {exc}")
    except insta_exceptions.PrivateProfileNotFollowedException:
        print(
            "Access denied: the Reel belongs to a private account you do not follow."
        )
    except insta_exceptions.BadResponseException as exc:
        print(f"Instagram returned an error while fetching the Reel: {exc}")
    except insta_exceptions.LoginRequiredException:
        print("Login required: provide valid Instagram credentials and try again.")
    except insta_exceptions.InstaloaderException as exc:
        print(f"Instaloader error: {exc}")
    except OSError as exc:
        print(f"File system error while saving the video: {exc}")
    except Exception as exc:  # noqa: BLE001 - keep the script user-friendly on unexpected failures
        print(f"Unexpected error: {exc}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
