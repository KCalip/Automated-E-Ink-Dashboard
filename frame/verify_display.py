#!/usr/bin/env python3
"""
verify_display.py

Failsafe check: confirms the SwitchBot Art Frame is actually displaying
today's dashboard image, by comparing image CONTENT (a hash of the actual
bytes), not URLs.

WHY NOT COMPARE URLS:
SwitchBot re-hosts every uploaded image on its own S3 bucket and returns a
fresh, temporary signed URL (different every time you check status) - it
does NOT remember or echo back the source URL you uploaded from. So the
`imageUrl` in a status response will NEVER match your GitHub raw URL, even
when the frame IS correctly showing today's dashboard. The only reliable
check is: download whatever's currently on display, hash it, and compare
that hash to a hash of the file we actually uploaded.

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
import hashlib
import os
import sys
import time

import requests

from push_to_frame import (
    BASE_URL,
    DASHBOARD_IMAGE_PATH,
    build_auth_headers,
    load_credentials,
)

MAX_CYCLE_ATTEMPTS = 10  # matches the frame's 10-image storage cap
SECONDS_BETWEEN_ATTEMPTS = 3  # give the frame a moment to register each switch


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_local_file(path: str) -> str:
    if not os.path.exists(path):
        print(f"❌ Local dashboard image not found at: {path}")
        sys.exit(1)
    with open(path, "rb") as f:
        return hash_bytes(f.read())


def hash_remote_image(url: str) -> str:
    """Download the currently-displayed image and hash its bytes."""
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        print(f"❌ Could not fetch currently-displayed image: HTTP {resp.status_code}")
        sys.exit(1)
    return hash_bytes(resp.content)


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
    print(f"   {DASHBOARD_IMAGE_PATH} -> {expected_hash[:16]}...")

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
    print(f"   Currently displayed content hash: {current_hash[:16]}...")

    if current_hash == expected_hash:
        print("✅ Frame is showing today's dashboard (content matches). Nothing to do.")
        sys.exit(0)

    print("⚠️  MISMATCH - displayed image content does not match today's dashboard.")

    if not args.fix:
        print("   Run again with --fix to cycle through stored images with `next`.")
        sys.exit(1)

    print(f"\n🔧 --fix given: cycling with `next` (up to {MAX_CYCLE_ATTEMPTS} attempts)...")
    for attempt in range(1, MAX_CYCLE_ATTEMPTS + 1):
        send_simple_command(creds["token"], creds["secret"], creds["device_id"], "next")
        time.sleep(SECONDS_BETWEEN_ATTEMPTS)

        status = get_status(creds["token"], creds["secret"], creds["device_id"])
        current_url = status.get("imageUrl", "")
        current_hash = hash_remote_image(current_url) if current_url else ""
        print(f"   Attempt {attempt}/{MAX_CYCLE_ATTEMPTS}: hash {current_hash[:16]}...")

        if current_hash == expected_hash:
            print(f"✅ Found it after {attempt} `next` command(s).")
            sys.exit(0)

    print(f"\n❌ Cycled through {MAX_CYCLE_ATTEMPTS} images without finding a content match.")
    print("   Today's dashboard may not be among the stored images at all -")
    print("   check whether today's upload actually succeeded (statusCode 100),")
    print("   and whether displayMode is Slideshow (see warning above).")
    sys.exit(1)


if __name__ == "__main__":
    main()
