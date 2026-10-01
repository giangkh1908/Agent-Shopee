"""Cấu hình + nạp .env (không cần dependency ngoài)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path | None = None) -> None:
    p = path or (ROOT / ".env")
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


load_env()

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "").strip()
APIFY_ACTOR_ID = os.environ.get("APIFY_ACTOR_DETAIL", "zen-studio~shopee-product-detail-scraper").strip()
APIFY_BASE = "https://api.apify.com/v2"

# CommandCode Gemini 3.8 Flash config
COMMANDCODE_API_KEY = os.environ.get("COMMANDCODE_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "google/gemini-3.8-flash").strip()
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.commandcode.ai/provider/v1").strip()

# Basic auth cho bản deploy public; không đặt APP_PASSWORD = tắt auth (local).
APP_USER = os.environ.get("APP_USER", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()

# Có PG_DSN (vd Neon) thì dùng Postgres, không thì SQLite local.
PG_DSN = os.environ.get("PG_DSN", "").strip()
DB_PATH = Path(os.environ.get("AGENT_SHOPEE_DB", ROOT / "data" / "agent_shopee.db"))
WEB_DIR = ROOT / "web"

MONTHLY_PROVIDER_BUDGET_USD = float(os.environ.get("MONTHLY_PROVIDER_BUDGET_USD", "30"))
