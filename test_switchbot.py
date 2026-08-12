import os
import time
import uuid
import hmac
import hashlib
import base64

import requests
from dotenv import load_dotenv

def get_env_credentials():
    load_dotenv()

    token = os.getenv("SWITCHBOT_TOKEN")
    secret = os.getenv("SWITCHBOT_SECRET")
    return token, secret

def create_headers(token, secret):
    nonce = str(uuid.uuid4()) # Get Random identifier for request
    timestamp = str(int(time.time() * 1000)) # Required for SwitchBot (13-digit timestamp in ms)

    string_to_sign = token + timestamp + nonce

    # Cryptographic Signature
    signature = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).digest()
    ).decode("utf-8")

    headers = {
        "Authorization": token,
        "sign": signature,
        "nonce": nonce,
        "t": timestamp,
    }
    return headers

def get_device_data(token, secret):
    
    headers = create_headers(token, secret)
    # Actual internet communication
    response = requests.get(
        "https://api.switch-bot.com/v1.1/devices",
        headers=headers
    )

    print("HTTP status:", response.status_code)

    data = response.json()

    print("API status:", data["statusCode"])
    print("Message:", data["message"])

    print("\nDevices:")
    for device in data["body"]["deviceList"]:
        print(f"  Name: {device['deviceName']}")
        print(f"  Type: {device['deviceType']}")
        print(f"  ID:   {device['deviceId']}")
        print()
        if device["deviceType"] == "AI Art Frame":
            device_id = device["deviceId"]
            return device
    print("Could not find an AI Art Frame.")
    return None

def get_frame_status(token, secret, device_id):
    headers = create_headers(token, secret)
    status_url = f"https://api.switch-bot.com/v1.1/devices/{device_id}/status"
    print(status_url)
    response = requests.get(
        status_url,
        headers=headers
    )
    data = response.json()
    print(data)
    return data

if __name__ == "__main__":
    token, secret = get_env_credentials()
    device_data = get_device_data(token, secret)
    device_id = device_data["deviceId"]
    print(f"Found AI Art Frame: {device_id}")
    get_frame_status(token, secret, device_id)