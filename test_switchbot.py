import os
import time
import uuid
import hmac
import hashlib
import base64

import requests
from dotenv import load_dotenv


load_dotenv()

token = os.getenv("SWITCHBOT_TOKEN")
secret = os.getenv("SWITCHBOT_SECRET")

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