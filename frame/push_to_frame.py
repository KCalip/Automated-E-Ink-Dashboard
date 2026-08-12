#!/usr/bin/env python3
"""
push_to_frame.py

Pushes a finished dashboard PNG to a SwitchBot E-Ink Art Frame via the
SwitchBot Cloud API (v1.1).

CURRENT STATUS: Step 1 of the build order (see project handoff doc).
    - Auth signing: WORKING
    - GET /v1.1/devices: WORKING
    - Image upload: NOT YET IMPLEMENTED (see upload_image() below - this is
      the next thing to figure out, since the exact upload endpoint/payload
      shape needs to be confirmed against current SwitchBot docs)
    - Storage-cap handling: NOT YET IMPLEMENTED

STORAGE-CAP DECISION LOG (fill this in once you've decided):
    TODO - document whichever approach you land on (overwrite / detect-and-warn
    / graceful-failure) and why, once you've confirmed what the API actually
    allows.

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


def upload_image(token: str, secret: str, device_id: str, image_bytes: bytes) -> None:
    """
    TODO: NOT YET IMPLEMENTED.

    This is the next piece to figure out. Before writing this function,
    confirm against CURRENT official SwitchBot docs:
      1. The exact command/endpoint for pushing an image to the Art Frame.
      2. Whether it wants raw bytes (multipart), base64 in the JSON body,
         or a publicly-hosted URL to the image.
      3. Whether uploading REPLACES the currently displayed image or ADDS
         a new one to the 10-image storage cap.

    Once confirmed, this function should also implement whatever storage-cap
    strategy was decided (see the decision log at the top of this file).
    """
    raise NotImplementedError(
        "Image upload not implemented yet - see docstring for what to confirm first."
    )


def check_storage_capacity(token: str, secret: str, device_id: str) -> None:
    """
    TODO: NOT YET IMPLEMENTED.

    If the API exposes a way to list/count stored images on the frame,
    call it here and print a warning if capacity is close to the 10-image
    cap (e.g. "⚠️ 9/10 slots used - clear the frame in the app soon").
    """
    pass


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

    if not creds["device_id"]:
        print("\nℹ️  SWITCHBOT_DEVICE_ID is not set yet. Copy the Art Frame's")
        print("   deviceId from the list above into your .env file.")

    if args.dry_run:
        print("\n✅ Dry run complete - auth and device lookup succeeded.")
        print("   (Image upload was skipped; upload_image() isn't implemented yet.)")
        return

    # --- Everything below this line depends on upload_image() being implemented ---
    image_bytes = read_dashboard_image(DASHBOARD_IMAGE_PATH)
    check_storage_capacity(creds["token"], creds["secret"], creds["device_id"])
    upload_image(creds["token"], creds["secret"], creds["device_id"], image_bytes)
    print("✅ Dashboard image pushed to frame.")


if __name__ == "__main__":
    main()
