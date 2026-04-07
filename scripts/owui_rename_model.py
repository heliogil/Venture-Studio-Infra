"""
Renomear modelo assistente-vs → Jarvis Candango no Open WebUI.
"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:3000"
EMAIL = "heliogil@gmail.com"
PASSWORD = "Gracindo0!"


def req(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# Login
_, resp = req("POST", "/api/v1/auths/signin", {"email": EMAIL, "password": PASSWORD})
token = resp["token"]
print(f"Login OK | role={resp['role']}")

# Update model name
status, resp = req(
    "POST",
    "/api/v1/models/assistente-vs/update",
    {"name": "Jarvis Candango"},
    token,
)
print(f"Rename (update): {status} | {str(resp)[:150]}")

if status not in (200, 201):
    # Try PUT
    status, resp = req(
        "PUT",
        "/api/v1/models/assistente-vs",
        {"name": "Jarvis Candango"},
        token,
    )
    print(f"Rename (PUT): {status} | {str(resp)[:150]}")

# Verify
status, resp = req("GET", "/api/v1/models", token=token)
if isinstance(resp, dict):
    for m in resp.get("data", []):
        if "jarvis" in str(m.get("name", "")).lower() or "assistente" in str(m.get("name", "")).lower():
            print(f"Model: id={m.get('id')} name={m.get('name')}")
