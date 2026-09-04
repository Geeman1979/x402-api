#!/usr/bin/env python3
"""Verify paywall + free endpoints against the running server."""
import json
import httpx

BASE = "http://127.0.0.1:8000"

print("=" * 64)
print("1) ROOT (free) — should show API info + pricing catalog")
print("=" * 64)
r = httpx.get(BASE + "/")
print("status:", r.status_code)
body = r.json()
print("name:", body.get("name"))
for path, info in body.get("endpoints", {}).items():
    print(f"   {path:30s} {info.get('price','?'):8s} {info.get('description','')[:50]}")

print()
print("=" * 64)
print("2) HEALTH (free)")
print("=" * 64)
r = httpx.get(BASE + "/health")
print("status:", r.status_code, "body:", r.json())

print()
print("=" * 64)
print("3) PAID ENDPOINT WITHOUT PAYMENT — expect 402")
print("=" * 64)
r = httpx.get(BASE + "/api/crypto/price?coin=bitcoin")
print("status:", r.status_code)
if r.status_code == 402:
    print("✅ PAYWALL ACTIVE — server demands payment first")
    print("headers:")
    for k, v in r.headers.items():
        if "payment" in k.lower() or k.lower().startswith("x-") or k == "www-authenticate":
            print(f"   {k}: {v[:120]}")
else:
    print("body:", r.text[:400])

print()
print("=" * 64)
print("4) POST paid endpoint without payment — expect 402")
print("=" * 64)
r = httpx.post(BASE + "/api/analyze/text", json={"text": "hello world"})
print("status:", r.status_code)
if r.status_code == 402:
    print("✅ PAYWALL ACTIVE on POST routes too")
