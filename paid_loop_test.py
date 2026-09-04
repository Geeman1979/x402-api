#!/usr/bin/env python3
"""End-to-end paid loop test using a throwaway testnet wallet.

Generates a fresh local wallet, wires the x402 transport into httpx,
and attempts the full pay → verify → get-data flow against the running
server on Base Sepolia. Without funded USDC the verification step will
fail at the facilitator — that's expected. The point is to prove the
client and server speak the same protocol end to end.
"""
import sys
sys.path.insert(0, ".")  # ensure x402_client.py importable

from eth_account import Account
from x402_client import make_paid_client

BASE = "http://127.0.0.1:8000"

acct = Account.create()
print("Payer address:", acct.address)
print("(throwaway test wallet — no funds needed for this wiring test)")
print()

client, payer = make_paid_client(acct.key.hex(), chain_id=84532)
print("Paid client wired with x402 transport.")
print()

print("=" * 60)
print("TEST 1 — /api/crypto/price?coin=bitcoin (auto-pay attempt)")
print("=" * 60)
try:
    r = client.get(BASE + "/api/crypto/price", params={"coin": "bitcoin"})
    print("status:", r.status_code)
    print("body:", r.text[:400])
except Exception as e:
    print("ERROR:", type(e).__name__, "—", str(e)[:400])

print()
print("=" * 60)
print("TEST 2 — /api/analyze/text (POST, auto-pay attempt)")
print("=" * 60)
try:
    r = client.post(BASE + "/api/analyze/text", json={"text": "Bitcoin rallied hard today. Great momentum and strong growth signals."})
    print("status:", r.status_code)
    print("body:", r.text[:400])
except Exception as e:
    print("ERROR:", type(e).__name__, "—", str(e)[:400])
