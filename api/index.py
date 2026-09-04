"""Vercel serverless entry point for the Verve Paywall API (FastAPI/ASGI)."""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
os.chdir(_root)

from main import app  # noqa: E402

# Vercel's Python runtime looks for `app` (ASGI)
