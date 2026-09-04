"""
Test client for the Verve Paywall API.

Two modes:
1. FREE MODE (no wallet needed):  .venv/Scripts/python.exe test_client.py free
   Shows the 402 payment wall — proves the coin slot works.

2. PAID MODE (needs a testnet wallet with USDC on Base Sepolia):
   set PAYER_PRIVATE_KEY env var, then .venv/Scripts/python.exe test_client.py paid
   The client auto-pays and fetches real data. Testnet USDC is free — get it
   from a Base Sepolia faucet.
"""
import os
import sys

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
CHAIN_ID = 84532  # Base Sepolia testnet


# ── Free-mode check: hit an endpoint WITHOUT paying → expect 402 ──
def check_paywall():
    import httpx
    print("=" * 60)
    print("PAYWALL CHECK — no payment attached (expect 402)")
    print("=" * 60)
    for path, label, method in [
        ("/api/crypto/price?coin=bitcoin", "crypto price", "GET"),
        ("/api/analyze/text", "text analysis", "POST"),
    ]:
        try:
            if method == "POST":
                r = httpx.post(BASE + path, json={"text": "This is a test sentence."})
            else:
                r = httpx.get(BASE + path)
            print(f"\n[{label}] status={r.status_code}")
            if r.status_code == 402:
                print("  ✅ Paywall working — server demands payment before serving data")
                print("  Payment headers:")
                for k, v in r.headers.items():
                    if "payment" in k.lower() or k.lower().startswith("x-"):
                        print(f"    {k}: {v[:110]}")
            else:
                print("  Body:", r.text[:300])
        except Exception as e:
            print(f"\n[{label}] ERROR: {e}")


# ── Paid mode: use x402 client with a real payer key ──
def paid_demo():
    key = os.environ.get("PAYER_PRIVATE_KEY", "")
    if not key:
        print("PAID MODE needs PAYER_PRIVATE_KEY env var (a wallet with USDC on Base Sepolia).")
        print("Run:  PAYER_PRIVATE_KEY=0x... python test_client.py paid")
        return

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from x402_client import make_paid_client

    client, payer = make_paid_client(key, chain_id=CHAIN_ID)

    print("=" * 60)
    print("PAID DEMO — full x402 loop (pay → get data)")
    print(f"Paying from: {payer}")
    print("=" * 60)

    for path, label, method in [
        ("/api/crypto/price?coin=solana", "SOL price", "GET"),
        ("/api/analyze/text", "text analysis", "POST"),
    ]:
        print(f"\n--- {label} ---")
        try:
            if method == "POST":
                r = client.post(BASE + path, json={"text": "Bitcoin rallied hard today. Great momentum and strong growth signals."})
            else:
                r = client.get(BASE + path)
            print(f"status={r.status_code}")
            print("body:", r.text[:400])
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "free"
    if mode == "free":
        check_paywall()
    else:
        paid_demo()
