# Verve Paywall API — a pay-per-call API using x402

A vending machine for the internet's robots. Each endpoint costs USDC, paid
automatically via the [x402 protocol](https://x402.org) — no accounts, no
signup forms, no KYC. Call it → get `402 Payment Required` → the caller's
wallet pays → retry → get data. The money lands in **your** wallet.

## Endpoints & prices

| Endpoint | Price | What it does |
|---|---|---|
| `GET /api/crypto/price?coin=bitcoin` | $0.01 | Live price, 24h change, market cap (CoinGecko) |
| `GET /api/crypto/signal?coin=solana` | $0.02 | Buy/Sell/Hold momentum signal |
| `POST /api/analyze/text` | $0.02 | Word count, reading level, sentiment |
| `POST /api/course/module` | $0.10 | Course module outline (template, or AI with `OPENAI_API_KEY`) |
| `POST /api/summarize` | $0.05 | TL;DR summarizer (extractive, no key needed) |

## Quick start

```bash
# 1. Create venv + install deps (also done automatically by start.bat)
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe x402 fastapi uvicorn httpx "x402[evm]"

# 2. Start the server
start.bat
# or: .venv/Scripts/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Verify the paywall (no wallet needed — proves the coin slot works)
.venv/Scripts/python.exe verify_paywall.py
# → paid endpoints return 402 Payment Required ✅
```

## Going live with real (testnet first) payments

The live community facilitator (`https://x402.org/facilitator`) supports the
`exact` scheme on **Base Sepolia testnet** (`eip155:84532`). Base mainnet
(`eip155:8453`) needs a facilitator that supports mainnet — either the
community facilitator adds it, or you self-host one.

### Step-by-step

1. **Get a wallet** — MetaMask or any EVM wallet. Your address is your
   "bank account" for the API.
2. **Set your receiving address** — in `main.py` (or better, an env var):
   ```
   set WALLET_ADDRESS=0xYourWalletAddressHere
   ```
3. **Get free testnet USDC** — switch MetaMask to Base Sepolia network
   (chain ID 84532), grab testnet ETH from a Base Sepolia faucet, then
   testnet USDC (search "Base Sepolia USDC faucet").
4. **Restart the server** and test the full loop with a funded wallet:
   ```
   set PAYER_PRIVATE_KEY=0xYourPayerWalletPrivateKey
   .venv/Scripts/python.exe test_client.py paid
   ```
   You should see status 200 with live data — the whole pay → verify →
   serve flow working.

5. **Go to mainnet** when a mainnet-capable facilitator is available:
   ```
   set NETWORK=eip155:8453
   set FACILITATOR_URL=<mainnet facilitator>
   ```
   (USDC on Base mainnet is the same token you'd get from an exchange.)

## How the money moves (the 2-second flow)

1. Caller hits a paid endpoint → server returns `402 Payment Required`
   with price + your wallet in the `payment-required` header.
2. Caller's x402 client signs a USDC transfer on Base, sends it to the
   facilitator (free, community-run).
3. Facilitator verifies + settles on-chain → returns a receipt.
4. Caller retries with the receipt → server verifies → serves the data.

**Economics:** USDC on Base ~$0.001/tx, facilitator free → you keep ~90% of
every call. Compare Stripe's 2.9% + $0.30 — for micropayments there's no
better option.

## Project layout

```
main.py            # FastAPI app + x402 paywall + 5 paid endpoints
x402_client.py     # httpx transport that auto-pays x402 walls
test_client.py     # free-mode (paywall check) + paid-mode (full loop) demo
verify_paywall.py  # quick paywall verification script
paid_loop_test.py  # end-to-end loop test with a throwaway wallet
start.bat          # Windows launcher (auto-creates venv)
```

## Exposing it publicly

For instant public URL (testing): `cloudflared tunnel --url http://localhost:8000`

For production: run on a VPS behind systemd, set `WALLET_ADDRESS` +
`NETWORK`, and optionally put it behind your own domain.

## Notes

- `OPENAI_API_KEY` env var unlocks AI-generated course outlines (uses
  `LLM_MODEL` env, default `gpt-4o-mini`). Without it, `/api/course/module`
  returns a solid template — both work.
- The `payment-required` header is the "coin slot": any x402-compatible
  client (Binance Agent OS, Coinbase for Agents, OpenClaw agents, etc.) can
  pay it automatically.
