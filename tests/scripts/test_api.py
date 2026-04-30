"""Test StealthMark FastAPI endpoints."""
import sys
import os

sys.path.insert(0, r"D:\work\code\stealthmark\src")
sys.path.insert(0, r"D:\work\code\stealthmark")

from fastapi.testclient import TestClient
from stealthmark.api import app

client = TestClient(app)

TEST_PNG = r"D:\work\code\stealthmark\tests\fixtures\test.png"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["handlers"] > 0
    print("[OK] /health  handlers:", data["handlers"])


def test_info():
    r = client.get("/info")
    assert r.status_code == 200
    data = r.json()
    assert "handlers" in data
    assert "formats" in data
    print("[OK] /info  handlers:", data["handlers"])
    for cat, exts in data["formats"].items():
        print(f"     {cat}: {exts}")


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    print("[OK] /  ", r.json())


def test_embed():
    if not os.path.exists(TEST_PNG):
        print(f"[SKIP] {TEST_PNG} not found")
        return
    with open(TEST_PNG, "rb") as f:
        files = {"file": ("test.png", f, "image/png")}
        data = {"watermark": "API-Test-2026"}
        r = client.post("/embed", files=files, data=data)
    assert r.status_code == 200
    result = r.json()
    assert result["success"], f"embed failed: {result['message']}"
    print(f"[OK] /embed  watermark: {result['watermark']}  message: {result['message']}")


def test_verify():
    if not os.path.exists(TEST_PNG):
        print(f"[SKIP] {TEST_PNG} not found")
        return
    with open(TEST_PNG, "rb") as f:
        files = {"file": ("test.png", f, "image/png")}
        data = {"watermark": "StealthMark-Test-2026"}
        r = client.post("/verify", files=files, data=data)
    assert r.status_code == 200
    result = r.json()
    print(f"[OK] /verify  match={result['match']}  score={result['match_score']}")
    print(f"     expected: {result['expected']}  extracted: {result['extracted']}")


if __name__ == "__main__":
    test_root()
    test_health()
    test_info()
    test_embed()
    test_verify()
    print("\nAll API tests passed!")
