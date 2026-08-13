#!/usr/bin/env python3
"""
push_to_frame.py

Pushes a finished dashboard PNG to a SwitchBot E-Ink Art Frame via the
SwitchBot Cloud API (v1.1).

CURRENT STATUS:
    - Auth signing: WORKING
    - GET /v1.1/devices: WORKING
    - Image upload: CONFIRMED WORKING SHAPE - see upload_image() docstring.
      command="uploadImage", parameter={"imageUrl": <url>}, commandType="command"
    - Storage-cap handling: IMPLEMENTED (graceful failure on statusCode 402)
      Confirmed uploads ADD to the frame's 10-image store rather than
      replacing the current image, and there is no API delete command.

STORAGE-CAP DECISION LOG:
    Chose graceful failure over pre-upload capacity checking, because the
    API has no "list stored images" / count endpoint to check against in
    advance. Instead, upload_image() detects the specific statusCode 402
    ("image count limit reached") response and prints clear instructions
    to clear images in the phone app, rather than a raw error. This means
    the script WILL start failing once 10 images have been uploaded total,
    and a human has to intervene in the app - there's no way around this
    with the current API. A daily-cron use case will need either manual
    periodic clearing, or watching for SwitchBot to add a delete endpoint
    (tracked as a public feature request, unresolved as of testing).

USAGE:
    python3 push_to_frame.py --dry-run     # test auth + device lookup only
    python3 push_to_frame.py               # full run (not implemented yet)

CREDENTIALS:
    Reads SWITCHBOT_TOKEN, SWITCHBOT_SECRET, SWITCHBOT_DEVICE_ID from
    environment variables (see .env.example). Never hardcode these.
"""

import argparse
import base64
import hashlib
import hmac
import os
import sys
import time
import uuid

import requests  # pip install requests
from dotenv import load_dotenv  # pip install python-dotenv

BASE_URL = "https://api.switch-bot.com"
DASHBOARD_IMAGE_PATH = "output/dashboard.png"


def load_credentials() -> dict:
    """Load and validate required credentials from environment variables."""
    load_dotenv()  # reads .env into os.environ if present; no-op if missing

    token = os.environ.get("SWITCHBOT_TOKEN")
    secret = os.environ.get("SWITCHBOT_SECRET")
    device_id = os.environ.get("SWITCHBOT_DEVICE_ID")

    missing = [
        name
        for name, val in [
            ("SWITCHBOT_TOKEN", token),
            ("SWITCHBOT_SECRET", secret),
        ]
        if not val
    ]
    if missing:
        print(f"❌ Missing required environment variable(s): {', '.join(missing)}")
        print("   Copy .env.example to .env and fill in your real values.")
        sys.exit(1)

    # device_id is allowed to be blank on first run - you get it FROM the
    # devices list below, then add it to your .env afterwards.
    return {"token": token, "secret": secret, "device_id": device_id}


def build_auth_headers(token: str, secret: str) -> dict:
    """
    Build the signed headers SwitchBot API v1.1 requires on every request.

    The scheme: sign (token + timestamp + nonce) with HMAC-SHA256 using the
    secret as the key, base64-encode it, uppercase it. The secret itself is
    never sent - only the resulting signature is.
    """
    nonce = str(uuid.uuid4())
    t = str(int(round(time.time() * 1000)))  # milliseconds

    string_to_sign = f"{token}{t}{nonce}"
    signed = hmac.new(
        secret.encode("utf-8"),
        msg=string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(signed).decode("utf-8").upper()

    return {
        "Authorization": token,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json",
    }


def list_devices(token: str, secret: str) -> list:
    """
    Calls GET /v1.1/devices to confirm auth works and list devices on the
    account. This is the first thing that needs to succeed - if this fails,
    nothing downstream will work.
    """
    headers = build_auth_headers(token, secret)
    resp = requests.get(f"{BASE_URL}/v1.1/devices", headers=headers, timeout=10)

    if resp.status_code != 200:
        print(f"❌ Auth/device lookup failed: HTTP {resp.status_code}")
        print(f"   Response: {resp.text}")
        sys.exit(1)

    data = resp.json()
    if data.get("statusCode") != 100:
        print(f"❌ SwitchBot API returned an error: {data}")
        sys.exit(1)

    devices = data.get("body", {}).get("deviceList", [])
    return devices


def read_dashboard_image(path: str) -> bytes:
    """Read the finished dashboard PNG produced by compose.py."""
    if not os.path.exists(path):
        print(f"❌ Dashboard image not found at: {path}")
        print("   Run compose.py first, or point DASHBOARD_IMAGE_PATH at a test PNG.")
        sys.exit(1)
    with open(path, "rb") as f:
        return f.read()


def upload_image(token: str, secret: str, device_id: str, image_url: str) -> dict:
    """
    Push an image to the Art Frame.

    CONFIRMED against the real API (2026-08):
      - command: "uploadImage"
      - parameter: {"imageUrl": <public https URL>}   <- object, key is "imageUrl"
      - commandType: "command"

    CONFIRMED BEHAVIOR: uploads ADD a new stored image rather than replacing
    the current one. There is no known API way to delete stored images, so
    once the frame's 10-image cap is hit, every upload fails with
    statusCode 402 "image count limit reached" until images are cleared
    manually in the phone app. This function detects that specific case and
    fails with a clear, actionable message rather than a raw error dump -
    see the STORAGE-CAP DECISION LOG at the top of this file.

    image_url must be a genuinely public, directly-fetchable https URL
    (e.g. a raw.githubusercontent.com link, NOT a github.com/.../blob/...
    viewer page - that serves an HTML wrapper, not the image bytes).
    """
    headers = build_auth_headers(token, secret)
    body = {
        "command": "uploadImage",
        "parameter": {"imageUrl": image_url},
        "commandType": "command",
    }
    resp = requests.post(
        f"{BASE_URL}/v1.1/devices/{device_id}/commands",
        headers=headers,
        json=body,
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"❌ Upload request failed: HTTP {resp.status_code}")
        print(f"   Response: {resp.text}")
        sys.exit(1)

    data = resp.json()
    status = data.get("statusCode")

    if status == 402:
        print("⚠️  Frame storage is full (10/10 images).")
        print("   SwitchBot's API has no way to delete images remotely.")
        print("   Open the SwitchBot phone app and manually clear some images")
        print("   from the Art Frame, then re-run this script.")
        sys.exit(1)

    if status != 100:
        print(f"❌ SwitchBot API rejected the upload command: {data}")
        sys.exit(1)

    return data


def main():
    parser = argparse.ArgumentParser(description="Push dashboard image to SwitchBot E-Ink Art Frame")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test auth and device lookup only - does not upload anything.",
    )
    args = parser.parse_args()

    creds = load_credentials()

    print("🔐 Testing SwitchBot API authentication...")
    devices = list_devices(creds["token"], creds["secret"])
    print(f"✅ Auth works. Found {len(devices)} device(s) on this account:")
    for d in devices:
        print(f"   - {d.get('deviceName')} ({d.get('deviceType')}) id={d.get('deviceId')}")
    print("   (deviceType above matters if the upload command needs commandType='customize')")

    if not creds["device_id"]:
        print("\nℹ️  SWITCHBOT_DEVICE_ID is not set yet. Copy the Art Frame's")
        print("   deviceId from the list above into your .env file.")

    if args.dry_run:
        print("\n✅ Dry run complete - auth and device lookup succeeded.")
        print("   (Image upload was skipped; upload_image() isn't implemented yet.)")
        return

    # --- Everything below this line is the best-guess upload flow ---
    read_dashboard_image(DASHBOARD_IMAGE_PATH)  # just confirms the file exists locally

    image_url_base = os.environ.get("DASHBOARD_IMAGE_URL")
    if not image_url_base:
        print("❌ DASHBOARD_IMAGE_URL is not set.")
        print("   The upload command needs a PUBLIC https URL where the image")
        print("   is already hosted (SwitchBot fetches it themselves - it does")
        print("   not accept raw bytes). E.g. a GitHub raw URL once the repo's")
        print("   workflow commits output/dashboard.png:")
        print("   https://raw.githubusercontent.com/<user>/<repo>/main/output/dashboard.png")
        sys.exit(1)

    # Cache-bust: GitHub's CDN and/or SwitchBot's own fetcher may not re-fetch
    # a URL they've seen before, even though the file content changed. Append
    # a timestamp query param (ignored by GitHub for routing, but makes the
    # full URL unique every run) so both layers are forced to fetch fresh.
    separator = "&" if "?" in image_url_base else "?"
    image_url = f"{image_url_base}{separator}t={int(time.time())}"
    print(f"🔗 Using cache-busted image URL: {image_url}")

    result = upload_image(creds["token"], creds["secret"], creds["device_id"], image_url)
    print(f"✅ Upload command accepted: {result}")


if __name__ == "__main__":
    main()
