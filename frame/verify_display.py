#!/usr/bin/env python3
"""
verify_display.py

Failsafe check: confirms the SwitchBot Art Frame is actually displaying
today's dashboard image, by comparing images PERCEPTUALLY (a fuzzy visual
hash), not by exact bytes or URL.

WHY NOT COMPARE URLS:
SwitchBot re-hosts every uploaded image on its own S3 bucket and returns a
fresh, temporary signed URL (different every time you check status) - it
does NOT remember or echo back the source URL you uploaded from.

WHY NOT COMPARE EXACT BYTES EITHER:
SwitchBot converts the uploaded image to JPEG for storage (note the stored
filename ends in .jpg, not .png) - JPEG is lossy, so even a correct,
matching upload will NEVER produce identical bytes to the source PNG. An
exact-hash check would report every single successful upload as a
"mismatch." Instead this uses a perceptual hash (imagehash.phash), which is
designed to tolerate exactly this kind of re-encoding noise while still
catching genuinely different images (like the Great Wave).

CONFIRMED against official docs (devices/others/ai-art-frame.md):
  - GET /v1.1/devices/{id}/status returns `imageUrl` (currently displayed,
    a temporary signed S3 URL - fetch it promptly, these expire) and
    `displayMode` (0 = Static image, 1 = Slideshow).
  - `next` / `previous` commands: {"command": "next", "parameter": "default",
    "commandType": "command"} - switches to the next/previous stored image.

USAGE:
    python3 verify_display.py
    python3 verify_display.py --fix     # cycle with `next` until it matches

Exits 0 if the frame is confirmed showing today's dashboard, 1 otherwise.
"""

import argparse
import os
import sys
import time
from io import BytesIO

import requests
from PIL import Image
import imagehash

from push_to_frame import (
    BASE_URL,
    DASHBOARD_IMAGE_PATH,
    build_auth_headers,
    load_credentials,
)

MAX_CYCLE_ATTEMPTS = 10  # matches the frame's 10-image storage cap
SECONDS_BETWEEN_ATTEMPTS = 3  # give the frame a moment to register each switch
HASH_DIFFERENCE_THRESHOLD = 8  # perceptual hash "distance" allowed as still-a-match
                                 # (0 = pixel-identical; SwitchBot re-encodes to JPEG,
                                 # which is lossy, so exact byte/pixel matches never
                                 # happen even on a correct upload - some tolerance
                                 # is required. 8 is a reasonably strict starting point;
                                 # raise it if genuine matches are still being flagged
                                 # as mismatches, lower it if false positives occur.)


def perceptual_hash(image: Image.Image):
    return imagehash.phash(image)


def hash_local_file(path: str):
    if not os.path.exists(path):
        print(f"❌ Local dashboard image not found at: {path}")
        sys.exit(1)
    with Image.open(path) as img:
        return perceptual_hash(img.convert("RGB"))


def hash_remote_image(url: str):
    """Download the currently-displayed image and compute its perceptual hash."""
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        print(f"❌ Could not fetch currently-displayed image: HTTP {resp.status_code}")
        sys.exit(1)
    with Image.open(BytesIO(resp.content)) as img:
        return perceptual_hash(img.convert("RGB"))


def get_status(token: str, secret: str, device_id: str) -> dict:
    """GET /v1.1/devices/{id}/status - full status body (imageUrl, displayMode, etc)."""
    headers = build_auth_headers(token, secret)
    resp = requests.get(
        f"{BASE_URL}/v1.1/devices/{device_id}/status", headers=headers, timeout=10
    )
    if resp.status_code != 200:
        print(f"❌ Status check failed: HTTP {resp.status_code}")
        print(f"   Response: {resp.text}")
        sys.exit(1)

    data = resp.json()
    if data.get("statusCode") != 100:
        print(f"❌ SwitchBot API rejected the status request: {data}")
        sys.exit(1)

    return data.get("body", {})


def send_simple_command(token: str, secret: str, device_id: str, command: str) -> dict:
    headers = build_auth_headers(token, secret)
    body = {"command": command, "parameter": "default", "commandType": "command"}
    resp = requests.post(
        f"{BASE_URL}/v1.1/devices/{device_id}/commands",
        headers=headers,
        json=body,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"❌ '{command}' command failed: HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    if data.get("statusCode") != 100:
        print(f"❌ '{command}' command rejected: {data}")
        sys.exit(1)

    return data


def describe_display_mode(mode) -> str:
    return {0: "Static image", 1: "Slideshow"}.get(mode, f"unknown ({mode})")


def main():
    parser = argparse.ArgumentParser(description="Verify the Art Frame shows today's dashboard")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Cycle through stored images with `next` until a content match is found.",
    )
    args = parser.parse_args()

    creds = load_credentials()

    print("🔍 Hashing local dashboard image (the source of truth)...")
    expected_hash = hash_local_file(DASHBOARD_IMAGE_PATH)
    print(f"   {DASHBOARD_IMAGE_PATH} -> {expected_hash}")

    print("🔍 Checking frame status...")
    status = get_status(creds["token"], creds["secret"], creds["device_id"])
    display_mode = status.get("displayMode")
    current_url = status.get("imageUrl", "")
    print(f"   displayMode: {describe_display_mode(display_mode)}")

    if display_mode == 1:
        print("\n⚠️  Frame is in SLIDESHOW mode - it will keep auto-advancing")
        print("   through stored images on its own schedule, regardless of what")
        print("   this script does. Switch it to Static in the SwitchBot app to")
        print("   stop this from happening again.\n")

    if not current_url:
        print("❌ Status response had no imageUrl to check.")
        sys.exit(1)

    current_hash = hash_remote_image(current_url)
    difference = current_hash - expected_hash
    print(f"   Currently displayed perceptual hash: {current_hash} (difference: {difference})")

    if difference <= HASH_DIFFERENCE_THRESHOLD:
        print("✅ Frame is showing today's dashboard (image matches within tolerance). Nothing to do.")
        sys.exit(0)

    print(f"⚠️  MISMATCH - displayed image differs too much (distance {difference} > {HASH_DIFFERENCE_THRESHOLD}).")

    if not args.fix:
        print("   Run again with --fix to cycle through stored images with `next`.")
        sys.exit(1)

    print(f"\n🔧 --fix given: cycling with `next` (up to {MAX_CYCLE_ATTEMPTS} attempts)...")
    for attempt in range(1, MAX_CYCLE_ATTEMPTS + 1):
        send_simple_command(creds["token"], creds["secret"], creds["device_id"], "next")
        time.sleep(SECONDS_BETWEEN_ATTEMPTS)

        status = get_status(creds["token"], creds["secret"], creds["device_id"])
        current_url = status.get("imageUrl", "")
        if not current_url:
            print(f"   Attempt {attempt}/{MAX_CYCLE_ATTEMPTS}: no imageUrl in status, skipping")
            continue
        current_hash = hash_remote_image(current_url)
        difference = current_hash - expected_hash
        print(f"   Attempt {attempt}/{MAX_CYCLE_ATTEMPTS}: hash {current_hash} (difference: {difference})")

        if difference <= HASH_DIFFERENCE_THRESHOLD:
            print(f"✅ Found it after {attempt} `next` command(s).")
            sys.exit(0)

    print(f"\n❌ Cycled through {MAX_CYCLE_ATTEMPTS} images without finding a content match.")
    print("   Today's dashboard may not be among the stored images at all -")
    print("   check whether today's upload actually succeeded (statusCode 100),")
    print("   and whether displayMode is Slideshow (see warning above).")
    sys.exit(1)


if __name__ == "__main__":
    main()
