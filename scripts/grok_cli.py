#!/usr/bin/env python3
"""Simple CLI wrapper for grok.tap365.org.

Based on GROK_API_DOC.md.

Supported operations (all call https://grok.tap365.org/v1 by default):

- chat            -> /v1/chat/completions
- image           -> /v1/images/generations
- image-edit      -> /v1/images/edits
- video           -> /v1/videos (text-to-video)
- video-from-image-> /v1/videos (image-to-video)

Base URL can be overridden via env GROK_BASE_URL.
"""

import argparse
import ipaddress
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests


DEFAULT_BASE_URL = "https://grok.tap365.org/v1"
DEFAULT_API_KEY = "sk-sublb123456"


def get_base_url() -> str:
    return os.environ.get("GROK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _is_loopback_host(hostname: Optional[str]) -> bool:
    if not hostname:
        return False

    normalized = hostname.strip().strip("[]").lower()
    if normalized == "localhost":
        return True

    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def create_session(target_url: str) -> requests.Session:
    session = requests.Session()
    parsed = urlparse(target_url)
    if _is_loopback_host(parsed.hostname):
        session.trust_env = False
    return session


def get_api_key(args: argparse.Namespace) -> str:
    cli_key = getattr(args, "api_key", None)
    if cli_key:
        return cli_key.strip()

    env_key = os.environ.get("GROK_API_KEY", "").strip()
    if env_key:
        return env_key

    return DEFAULT_API_KEY


def build_headers(args: argparse.Namespace) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {get_api_key(args)}",
    }


def build_download_headers(url: str, args: argparse.Namespace) -> Optional[Dict[str, str]]:
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return build_headers(args)

    base = get_base_url()
    parsed_base = urlparse(base)
    if parsed_url.scheme == parsed_base.scheme and parsed_url.netloc == parsed_base.netloc:
        return build_headers(args)

    return None


def normalize_output_url(raw_url: str, base_url: str) -> str:
    raw = (raw_url or "").strip()
    if not raw:
        return raw

    parsed_base = urlparse(base_url)
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    base_path = parsed_base.path.rstrip("/")

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        if raw.startswith("/"):
            return f"{base_origin}{raw}"
        return raw

    if (
        parsed.scheme == parsed_base.scheme
        and parsed.netloc == parsed_base.netloc
        and base_path
    ):
        duplicated_prefix = f"{base_path}{base_path}/"
        if parsed.path.startswith(duplicated_prefix):
            return parsed._replace(path=parsed.path[len(base_path):]).geturl()

    return raw


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def cmd_chat(args: argparse.Namespace) -> None:
    base = get_base_url()
    url = f"{base}/chat/completions"
    session = create_session(url)

    payload: Dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": False,
    }

    resp = session.post(url, json=payload, headers=build_headers(args), timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if args.raw:
        print_json(data)
        return

    # Try to extract first choice text
    try:
        content = data["choices"][0]["message"]["content"]
        sys.stdout.write(str(content) + "\n")
    except Exception:
        print_json(data)


def cmd_image(args: argparse.Namespace) -> None:
    base = get_base_url()
    url = f"{base}/images/generations"
    session = create_session(url)

    payload: Dict[str, Any] = {
        "model": "grok-imagine-1.0",
        "prompt": args.prompt,
        "size": args.size,
        "response_format": "url",
    }

    resp = session.post(url, json=payload, headers=build_headers(args), timeout=120)
    resp.raise_for_status()
    data = resp.json()

    urls = [item.get("url") for item in data.get("data", []) if item.get("url")]
    if not urls:
        print_json(data)
        return

    first_url = urls[0]
    full_url = normalize_output_url(first_url, base)

    if args.output:
        _download_file(
            full_url,
            Path(args.output),
            headers=build_download_headers(full_url, args),
            session=session,
        )
        sys.stdout.write(f"Saved image to {args.output}\n")
    else:
        sys.stdout.write(full_url + "\n")


def cmd_image_edit(args: argparse.Namespace) -> None:
    base = get_base_url()
    url = f"{base}/images/edits"
    session = create_session(url)

    image_path = Path(args.image)
    if not image_path.is_file():
        sys.stderr.write(f"Image not found: {image_path}\n")
        sys.exit(1)

    files = {
        "image": (image_path.name, image_path.read_bytes()),
    }
    data: Dict[str, str] = {
        "model": "grok-imagine-1.0-edit",
        "prompt": args.prompt,
        "size": args.size,
        "response_format": "url",
    }

    resp = session.post(url, files=files, data=data, headers=build_headers(args), timeout=180)
    resp.raise_for_status()
    body = resp.json()

    urls = [item.get("url") for item in body.get("data", []) if item.get("url")]
    if not urls:
        print_json(body)
        return

    first_url = urls[0]
    full_url = normalize_output_url(first_url, base)

    if args.output:
        _download_file(
            full_url,
            Path(args.output),
            headers=build_download_headers(full_url, args),
            session=session,
        )
        sys.stdout.write(f"Saved edited image to {args.output}\n")
    else:
        sys.stdout.write(full_url + "\n")


def cmd_video(args: argparse.Namespace) -> None:
    base = get_base_url()
    url = f"{base}/videos"
    session = create_session(url)

    payload: Dict[str, Any] = {
        "prompt": args.prompt,
        "model": "grok-imagine-1.0-video",
        "size": args.size,
        "seconds": args.seconds,
        "quality": args.quality,
    }

    resp = session.post(url, json=payload, headers=build_headers(args), timeout=300)
    resp.raise_for_status()
    data = resp.json()

    video_url = _extract_video_url(data)
    if not video_url:
        print_json(data)
        return
    video_url = normalize_output_url(video_url, base)

    if args.output:
        _download_file(
            video_url,
            Path(args.output),
            headers=build_download_headers(video_url, args),
            session=session,
        )
        sys.stdout.write(f"Saved video to {args.output}\n")
    else:
        sys.stdout.write(video_url + "\n")


def cmd_video_from_image(args: argparse.Namespace) -> None:
    base = get_base_url()
    url = f"{base}/videos"
    session = create_session(url)

    image_path = Path(args.image)
    if not image_path.is_file():
        sys.stderr.write(f"Image not found: {image_path}\n")
        sys.exit(1)

    files = {
        "input_reference": (image_path.name, image_path.read_bytes()),
    }
    data: Dict[str, str] = {
        "model": "grok-imagine-1.0-video",
        "prompt": args.prompt,
        "size": args.size,
        "seconds": str(args.seconds),
        "quality": args.quality,
    }

    resp = session.post(url, files=files, data=data, headers=build_headers(args), timeout=600)
    resp.raise_for_status()
    body = resp.json()

    video_url = _extract_video_url(body)
    if not video_url:
        print_json(body)
        return
    video_url = normalize_output_url(video_url, base)

    if args.output:
        _download_file(
            video_url,
            Path(args.output),
            headers=build_download_headers(video_url, args),
            session=session,
        )
        sys.stdout.write(f"Saved video to {args.output}\n")
    else:
        sys.stdout.write(video_url + "\n")


def _extract_video_url(data: Dict[str, Any]) -> Optional[str]:
    # The exact field may vary; start simple and fall back to scan.
    url = data.get("url") or data.get("video_url")
    if url:
        return str(url)

    files = data.get("files") or data.get("data")
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            cand = item.get("url") or item.get("video_url")
            if cand:
                return str(cand)
    return None


def _download_file(
    url: str,
    path: Path,
    headers: Optional[Dict[str, str]] = None,
    session: Optional[requests.Session] = None,
) -> None:
    active_session = session or create_session(url)
    resp = active_session.get(url, headers=headers, stream=True, timeout=600)
    resp.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grok-cli",
        description="CLI wrapper for https://grok.tap365.org/v1",
    )
    parser.add_argument(
        "--base-url",
        dest="base_url",
        help="Override base URL (default: env GROK_BASE_URL or https://grok.tap365.org/v1)",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        help="Override API key (default: env GROK_API_KEY or sk-sublb123456)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # chat
    p_chat = sub.add_parser("chat", help="Text chat via /v1/chat/completions")
    p_chat.add_argument("prompt", help="User prompt text")
    p_chat.add_argument(
        "--model",
        default="grok-4.1-fast",
        help="Model ID (default: grok-4.1-fast)",
    )
    p_chat.add_argument(
        "--raw",
        action="store_true",
        help="Print full JSON response instead of just message content",
    )
    p_chat.set_defaults(func=cmd_chat)

    # image
    p_img = sub.add_parser("image", help="Text-to-image via /v1/images/generations")
    p_img.add_argument("prompt", help="Image generation prompt")
    p_img.add_argument(
        "--size",
        default="1024x1024",
        help="Image size (default: 1024x1024)",
    )
    p_img.add_argument(
        "-o",
        "--output",
        help="Save image to file instead of printing URL",
    )
    p_img.set_defaults(func=cmd_image)

    # image-edit
    p_edit = sub.add_parser("image-edit", help="Image-to-image via /v1/images/edits")
    p_edit.add_argument("image", help="Path to reference image")
    p_edit.add_argument("prompt", help="Edit prompt")
    p_edit.add_argument(
        "--size",
        default="1024x1024",
        help="Image size (default: 1024x1024)",
    )
    p_edit.add_argument(
        "-o",
        "--output",
        help="Save edited image to file instead of printing URL",
    )
    p_edit.set_defaults(func=cmd_image_edit)

    # video
    p_video = sub.add_parser("video", help="Text-to-video via /v1/videos")
    p_video.add_argument("prompt", help="Video generation prompt")
    p_video.add_argument(
        "--size",
        default="1792x1024",
        help="Video size (default: 1792x1024)",
    )
    p_video.add_argument(
        "--seconds",
        type=int,
        default=6,
        help="Video length in seconds (default: 6)",
    )
    p_video.add_argument(
        "--quality",
        default="standard",
        help="Video quality (default: standard)",
    )
    p_video.add_argument(
        "-o",
        "--output",
        help="Save video to file instead of printing URL",
    )
    p_video.set_defaults(func=cmd_video)

    # video-from-image
    p_vimg = sub.add_parser("video-from-image", help="Image-to-video via /v1/videos")
    p_vimg.add_argument("image", help="Path to reference image")
    p_vimg.add_argument("prompt", help="Prompt describing motion / style")
    p_vimg.add_argument(
        "--size",
        default="1792x1024",
        help="Video size (default: 1792x1024)",
    )
    p_vimg.add_argument(
        "--seconds",
        type=int,
        default=6,
        help="Video length in seconds (default: 6)",
    )
    p_vimg.add_argument(
        "--quality",
        default="standard",
        help="Video quality (default: standard)",
    )
    p_vimg.add_argument(
        "-o",
        "--output",
        help="Save video to file instead of printing URL",
    )
    p_vimg.set_defaults(func=cmd_video_from_image)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Allow overriding base URL via --base-url
    if args.base_url:
        os.environ["GROK_BASE_URL"] = args.base_url

    try:
        args.func(args)
    except requests.HTTPError as exc:
        sys.stderr.write(f"HTTP error: {exc}\n")
        if exc.response is not None:
            try:
                print_json(exc.response.json())
            except Exception:
                sys.stderr.write(exc.response.text + "\n")
        sys.exit(1)
    except requests.RequestException as exc:
        sys.stderr.write(f"Request failed: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
