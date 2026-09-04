"""
Verve Paywall API — a pay-per-call API using the x402 protocol.

Endpoints sell for USDC on Base L2. Payment is automatic via x402:
client gets 402 → pays → retries with receipt → gets data.

Run:  .venv/Scripts/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
"""
import os
import random
import re
from datetime import datetime, timezone

# Load .env if present (wallet address etc.) — optional but recommended
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from x402 import x402ResourceServer
from x402.http.facilitator_client import HTTPFacilitatorClient
from x402.http.facilitator_client_base import FacilitatorConfig
from x402.http.middleware.fastapi import payment_middleware
from x402.mechanisms.evm.exact import ExactEvmServerScheme
import warnings as _warnings
from x402.extensions.bazaar import declare_discovery_extension
from x402.extensions.bazaar.resource_service import OutputConfig

# ──────────────────────────────────────────────────────────────
# CONFIG — set these in a .env file (see README)
# ──────────────────────────────────────────────────────────────
PAY_TO = os.environ.get("WALLET_ADDRESS", "0x0000000000000000000000000000000000000000")
# Live community facilitator supports "exact" on Base Sepolia testnet (eip155:84532).
# USDC on Base mainnet (eip155:8453) requires a facilitator that supports mainnet —
# swap NETWORK when one is available or when self-hosting a facilitator.
NETWORK = os.environ.get("NETWORK", "eip155:84532")
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://x402.org/facilitator")
# Public URL of this API (used in the /.well-known/x402 manifest).
# MUST be the real public HTTPS URL when deployed — localhost only for local dev.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000")

app = FastAPI(title="Verve Paywall API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["payment-required", "payment-response", "PAYMENT-REQUIRED", "PAYMENT-RESPONSE"],
)

# ──────────────────────────────────────────────────────────────
# x402 setup — the "coin slot" on the vending machine
# ──────────────────────────────────────────────────────────────
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
server = x402ResourceServer(facilitator)
server.register("eip155:*", ExactEvmServerScheme())

ROUTES = {
    # ── Crypto signals ──
    "GET /api/crypto/price": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": "$0.01",
            "network": NETWORK,
        },
        "description": "Live price for a coin (BTC, ETH, SOL...) via CoinGecko",
        "mimeType": "application/json",
        "serviceName": "Verve Paywall API",
        "tags": ["crypto", "price", "market-data"],
        "extensions": {
            **declare_discovery_extension(
                input={"coin": "bitcoin"},
                input_schema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "CoinGecko coin id, e.g. bitcoin, ethereum, solana"}
                    },
                    "required": ["coin"],
                },
                output=OutputConfig(example={"coin": "bitcoin", "price_usd": 76685, "change_24h_pct": -1.67,
                                "market_cap_usd": 1539730364549.5, "source": "CoinGecko",
                                "timestamp": "2026-09-02T12:56:32Z"}),
            )
        },
    },
    "GET /api/crypto/signal": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": "$0.02",
            "network": NETWORK,
        },
        "description": "Simple sentiment/trend signal: 24h change, momentum, volatility",
        "mimeType": "application/json",
        "serviceName": "Verve Paywall API",
        "tags": ["crypto", "signal", "trading"],
        "extensions": {
            **declare_discovery_extension(
                input={"coin": "solana"},
                input_schema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "CoinGecko coin id"}
                    },
                    "required": ["coin"],
                },
                output=OutputConfig(example={"coin": "solana", "signal": "BUY", "strength": "moderate",
                                "change_24h_pct": 2.31, "price_usd": 187.2,
                                "note": "Simple momentum signal. Not financial advice."}),
            )
        },
    },
    # ── Content tools (the kind of thing Verve builds for clients) ──
    "POST /api/analyze/text": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": "$0.02",
            "network": NETWORK,
        },
        "description": "Readability, word count, sentiment and reading level of any text",
        "mimeType": "application/json",
        "serviceName": "Verve Paywall API",
        "tags": ["text", "analysis", "nlp"],
        "extensions": {
            **declare_discovery_extension(
                body_type="json",
                input={"text": "Your text here."},
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text to analyze"}
                    },
                    "required": ["text"],
                },
                output=OutputConfig(example={"word_count": 12, "sentence_count": 2, "avg_word_length": 4.1,
                                "avg_sentence_length": 6.0, "reading_level": "easy",
                                "sentiment": "neutral", "characters": 55}),
            )
        },
    },
    "POST /api/course/module": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": "$0.10",
            "network": NETWORK,
        },
        "description": "AI-generated course module outline from a topic (learning design)",
        "mimeType": "application/json",
        "serviceName": "Verve Paywall API",
        "tags": ["education", "course-design", "ai"],
        "extensions": {
            **declare_discovery_extension(
                body_type="json",
                input={"topic": "Introduction to Personal Finance"},
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "The course topic"}
                    },
                    "required": ["topic"],
                },
                output=OutputConfig(example={"topic": "Introduction to Personal Finance",
                                "outline": "# Course Module Outline ...",
                                "generated_by": "template"}),
            )
        },
    },
    "POST /api/summarize": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": "$0.05",
            "network": NETWORK,
        },
        "description": "TL;DR summary of long text (extractive, no AI key needed)",
        "mimeType": "application/json",
        "serviceName": "Verve Paywall API",
        "tags": ["text", "summarize", "nlp"],
        "extensions": {
            **declare_discovery_extension(
                body_type="json",
                input={"text": "Long text to summarize...", "max_sentences": 3},
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text to summarize"},
                        "max_sentences": {"type": "integer", "description": "Max sentences in summary (default 3)"},
                    },
                    "required": ["text"],
                },
                output=OutputConfig(example={"summary": "The key points...", "original_sentences": 12,
                                "method": "extractive (top-scoring sentences)"}),
            )
        },
    },
}

# NOTE: the bazaar SDK warns at declaration time that input lacks 'method',
# but method is auto-injected from the route key at request time (verified
# in live 402 responses) — the warning is a declaration-time false positive.
with _warnings.catch_warnings():
    _warnings.filterwarnings("ignore", message=".*invalid bazaar extension.*")
    x402_mw = payment_middleware(ROUTES, server)


@app.middleware("http")
async def payment_check(request: Request, call_next):
    return await x402_mw(request, call_next)


# ──────────────────────────────────────────────────────────────
# Free endpoints
# ──────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "Verve Paywall API",
        "protocol": "x402",
        "how_it_works": "Call an endpoint → get 402 Payment Required → pay USDC on Base → retry with receipt → get data.",
        "endpoints": {
            path: {
                "price": r["accepts"]["price"],
                "method": path.split()[0],
                "description": r["description"],
            }
            for path, r in ROUTES.items()
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/pay-demo")
async def pay_demo():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(os.path.dirname(__file__), "pay_demo.html"))


@app.get("/.well-known/x402")
async def well_known_x402():
    """x402 discovery manifest per IETF draft-hawkins-x402-dns-discovery.

    kind=resource-server: this host sells x402-gated resources; settlement
    happens via the community facilitator, not on this host.
    """
    from datetime import datetime as _dt
    return {
        "x402Version": 2,
        "kind": "resource-server",
        "name": "Verve Paywall API",
        "description": "Pay-per-call APIs: crypto market data/signals, text analysis, course design. USDC on Base.",
        "resources": [
            {
                "url": f"{PUBLIC_BASE_URL}/api/crypto/price",
                "method": "GET",
                "description": "Live crypto price, 24h change, market cap ($0.01)",
            },
            {
                "url": f"{PUBLIC_BASE_URL}/api/crypto/signal",
                "method": "GET",
                "description": "Crypto momentum signal: BUY/SELL/HOLD ($0.02)",
            },
            {
                "url": f"{PUBLIC_BASE_URL}/api/analyze/text",
                "method": "POST",
                "description": "Text readability, sentiment, stats ($0.02)",
            },
            {
                "url": f"{PUBLIC_BASE_URL}/api/course/module",
                "method": "POST",
                "description": "Course module outline from a topic ($0.10)",
            },
            {
                "url": f"{PUBLIC_BASE_URL}/api/summarize",
                "method": "POST",
                "description": "TL;DR extractive summary ($0.05)",
            },
        ],
        "attestation": {"type": "none"},
        "docs": f"{PUBLIC_BASE_URL}/",
        "contact": os.environ.get("CONTACT_EMAIL", ""),
        "updated": _dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ──────────────────────────────────────────────────────────────
# Paid endpoint 1 — Crypto price (CoinGecko, free API)
# ──────────────────────────────────────────────────────────────
import httpx as _httpx

COINGECKO = "https://api.coingecko.com/api/v3/simple/price"


@app.get("/api/crypto/price")
async def crypto_price(request: Request):
    coin = request.query_params.get("coin", "bitcoin")
    try:
        async with _httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                COINGECKO,
                params={"ids": coin, "vs_currencies": "usd",
                        "include_24hr_change": "true", "include_market_cap": "true"},
            )
            r.raise_for_status()
            data = r.json().get(coin, {})
        if not data:
            return JSONResponse({"error": f"Coin '{coin}' not found. Try 'bitcoin', 'ethereum', 'solana'."}, 404)
        return {
            "coin": coin,
            "price_usd": data.get("usd"),
            "change_24h_pct": data.get("usd_24h_change"),
            "market_cap_usd": data.get("usd_market_cap"),
            "source": "CoinGecko",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return JSONResponse({"error": f"Price lookup failed: {e}"}, 502)


# ──────────────────────────────────────────────────────────────
# Paid endpoint 2 — Crypto signal (computed locally, no keys needed)
# ──────────────────────────────────────────────────────────────
@app.get("/api/crypto/signal")
async def crypto_signal(request: Request):
    coin = request.query_params.get("coin", "bitcoin")
    try:
        async with _httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                COINGECKO,
                params={"ids": coin, "vs_currencies": "usd",
                        "include_24hr_change": "true", "include_market_cap": "true"},
            )
            r.raise_for_status()
            data = r.json().get(coin, {})
        if not data:
            return JSONResponse({"error": f"Coin '{coin}' not found."}, 404)

        change = data.get("usd_24h_change") or 0.0
        price = data.get("usd") or 0.0
        if change >= 5:
            signal, strength = "STRONG BUY", "high"
        elif change >= 1:
            signal, strength = "BUY", "moderate"
        elif change > -1:
            signal, strength = "NEUTRAL / HOLD", "low"
        elif change > -5:
            signal, strength = "SELL", "moderate"
        else:
            signal, strength = "STRONG SELL", "high"

        return {
            "coin": coin,
            "signal": signal,
            "strength": strength,
            "change_24h_pct": round(change, 2),
            "price_usd": price,
            "note": "Simple momentum signal from 24h price action. Not financial advice.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return JSONResponse({"error": f"Signal lookup failed: {e}"}, 502)


# ──────────────────────────────────────────────────────────────
# Paid endpoint 3 — Text analysis (pure Python, no keys)
# ──────────────────────────────────────────────────────────────
@app.post("/api/analyze/text")
async def analyze_text(request: Request):
    try:
        body = await request.json()
        text = (body.get("text") or "").strip()
    except Exception:
        return JSONResponse({"error": "Send JSON with a 'text' field"}, 400)

    if not text:
        return JSONResponse({"error": "No text provided"}, 400)

    words = re.findall(r"\S+", text)
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
    avg_word_len = sum(len(w.strip(".,!?;:")) for w in words) / len(words) if words else 0
    avg_sentence_len = len(words) / sentences

    # Simple readability estimate (Flesch-ish)
    if avg_word_len < 4.5 and avg_sentence_len < 15:
        level = "easy"
    elif avg_word_len > 6.5 or avg_sentence_len > 25:
        level = "advanced"
    else:
        level = "moderate"

    # Tiny lexicon sentiment
    positive = {"good", "great", "excellent", "amazing", "love", "best", "win", "profit", "bullish", "growth"}
    negative = {"bad", "terrible", "awful", "hate", "worst", "loss", "crash", "bearish", "risk", "fail"}
    lower = text.lower()
    pos_hits = sum(1 for w in positive if re.search(rf"\b{w}\b", lower))
    neg_hits = sum(1 for w in negative if re.search(rf"\b{w}\b", lower))
    sentiment = "positive" if pos_hits > neg_hits else ("negative" if neg_hits > pos_hits else "neutral")

    return {
        "word_count": len(words),
        "sentence_count": sentences,
        "avg_word_length": round(avg_word_len, 1),
        "avg_sentence_length": round(avg_sentence_len, 1),
        "reading_level": level,
        "sentiment": sentiment,
        "characters": len(text),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────
# Paid endpoint 4 — Course module outline (template-based, works with
# or without an LLM key; add OPENAI_API_KEY to unlock AI generation)
# ──────────────────────────────────────────────────────────────
COURSE_TEMPLATE = """# {topic} — Course Module Outline

## Module 1: Foundations of {topic}
- 1.1 What {topic} is and why it matters
- 1.2 Key concepts and vocabulary
- 1.3 Common misconceptions
- 1.4 Checkpoint quiz (5 questions)

## Module 2: Core Skills in {topic}
- 2.1 Step-by-step workflow
- 2.2 Hands-on practice activity
- 2.3 Real-world examples
- 2.4 Peer review / reflection task

## Module 3: Applying {topic}
- 3.1 Case study analysis
- 3.2 Project brief with deliverables
- 3.3 Common pitfalls and how to avoid them
- 3.4 Final assessment (10 questions)

## Module 4: Next Steps
- 4.1 Further reading and resources
- 4.2 Advanced topics preview
- 4.3 Feedback and improvement loop"""


@app.post("/api/course/module")
async def course_module(request: Request):
    try:
        body = await request.json()
        topic = (body.get("topic") or "").strip()
    except Exception:
        return JSONResponse({"error": "Send JSON with a 'topic' field"}, 400)

    if not topic:
        return JSONResponse({"error": "No topic provided"}, 400)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a learning designer. Create a structured course module outline with objectives, modules, activities and assessments."},
                    {"role": "user", "content": f"Create a course outline for: {topic}"},
                ],
                max_tokens=800,
            )
            return {"topic": topic, "outline": resp.choices[0].message.content,
                    "generated_by": "LLM", "timestamp": datetime.now(timezone.utc).isoformat()}
        except Exception:
            pass  # fall through to template

    return {"topic": topic, "outline": COURSE_TEMPLATE.format(topic=topic),
            "generated_by": "template", "note": "Add OPENAI_API_KEY to .env for AI-generated outlines.",
            "timestamp": datetime.now(timezone.utc).isoformat()}


# ──────────────────────────────────────────────────────────────
# Paid endpoint 5 — Summarizer (extractive, no keys needed)
# ──────────────────────────────────────────────────────────────
@app.post("/api/summarize")
async def summarize(request: Request):
    try:
        body = await request.json()
        text = (body.get("text") or "").strip()
        max_sentences = int(body.get("max_sentences", 3))
    except Exception:
        return JSONResponse({"error": "Send JSON with a 'text' field"}, 400)

    if not text:
        return JSONResponse({"error": "No text provided"}, 400)

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= max_sentences:
        summary = text
        method = "short text (returned as-is)"
    else:
        # Score sentences: length + keyword frequency (simple extractive)
        words = re.findall(r"\b\w{4,}\b", text.lower())
        from collections import Counter
        freq = Counter(words)
        top_words = {w for w, _ in freq.most_common(10)}

        def score(s):
            sw = re.findall(r"\b\w{4,}\b", s.lower())
            return sum(1 for w in sw if w in top_words) + min(len(sw) / 20, 1)

        scored = sorted(sentences, key=score, reverse=True)[:max_sentences]
        summary = " ".join(sentences[sentences.index(s)] for s in sorted(scored, key=sentences.index))
        method = "extractive (top-scoring sentences)"

    return {
        "summary": summary,
        "original_sentences": len(sentences),
        "method": method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
