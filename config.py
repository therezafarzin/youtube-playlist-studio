from __future__ import annotations

import logging
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOWNLOADS = ROOT / "downloads"
BROKEN = DOWNLOADS / "broken"
LOGS = ROOT / "logs"
DB_PATH = ROOT / "library.db"  # kept in place to preserve the existing library
COOKIE_PATH = ROOT / "cookies.txt"  # deliberately never served by Flask
HOST, PORT = "127.0.0.1", int(os.getenv("YPS_PORT", "8787"))
COOKIE_BROWSER = os.getenv("YTDLP_BROWSER", "chrome")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_SAFE_LIMIT = 49 * 1024 * 1024

def prepare_paths() -> None:
    for path in (DATA, DOWNLOADS, BROKEN, LOGS): path.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(filename=LOGS / "app.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
