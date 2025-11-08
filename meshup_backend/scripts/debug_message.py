import json
import uuid

import requests

BASE_URL = "http://localhost:8000/api/v1"

def main() -> None:
    email = f"debug_{uuid.uuid4().hex[:8]}@meshup.test"
    password = "Meshup!123"
    username = f"debug_{uuid.uuid4().hex[:6]}"

    requests.post(
        f"{BASE_URL}/auth/register/",
        json={
            "email": email,
            "username": username,
            "password": password,
            "password_confirm": password,
        },
    )
    login = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"email": email, "password": password},
    )
    print("login", login.status_code)
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access']}"}

    server = requests.post(
        f"{BASE_URL}/servers/",
        json={
            "name": "Debug Server",
            "description": "",
            "region": "us-east",
            "is_public": False,
            "verification_level": 0,
        },
        headers=headers,
    )
    print("server", server.status_code)
    print(server.text)
    server_id = server.json()["id"]

    channel = requests.post(
        f"{BASE_URL}/channels/{server_id}/",
        json={"name": "debug", "description": "", "channel_type": "text"},
        headers=headers,
    )
    print("channel", channel.status_code)
    print(channel.text)
    channel_id = channel.json()["id"]

    message = requests.post(
        f"{BASE_URL}/messages/channels/{channel_id}/",
        json={"content": "hello"},
        headers=headers,
    )
    print("message", message.status_code)
    with open("error.html", "w", encoding="utf-8") as fh:
        fh.write(message.text)
    print("error.html written with response body")


if __name__ == "__main__":
    main()
