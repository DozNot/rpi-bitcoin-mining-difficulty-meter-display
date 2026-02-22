#!/usr/bin/env python3
"""
RPi Bitcoin Mining Difficulty Meter Display
Real-time accepted share difficulties dashboard with rarity colors, session best highlights, and Bitcoin network stats for home miners.

Key Features:
- Gamified rarity color system for accepted shares: Poor → Common → Uncommon → Rare → Epic → Legendary (+ ✦ when exceeding network difficulty)
- Live list of recent shares (> configurable threshold) with miner name, time ago, and color-coded rarity
- Session best difficulty highlighted with “➊” trophy marker and miner name
- Aggregated local miner stats: total hashrate, best difficulty, connected/active counts with color-coded global health indicator
- Real-time BTC price with 24h change via Binance primary + Kraken fallback WebSockets
- Bitcoin network stats from mempool.space: recommended fees (sat/vB), block height, latest mining pool, network hashrate (EH/s), current difficulty
- Optimized for Raspberry Pi: software rendering, logical surface, data-hash skip redraw, default 8 FPS cap (ultra-low CPU)
- Automatic reconnection with exponential backoff, thread-safe shared state, configurable via JSON
- Auto-detect mode: fullscreen Pi (TFT/HDMI) or windowed desktop

Developed and tested with:
  - Raspberry Pi 3B+, 4, 5
  - Waveshare 3.5" TFT touchscreen (480×320, XPT2046 controller)
  - Standard HDMI monitors (auto-scaled with preserved aspect ratio)
  - Desktop/PC (Linux)
"""
import os
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import sys
import logging
from logging.handlers import RotatingFileHandler
import threading
import signal
from pathlib import Path
import pygame
import argparse

# Signal handling for clean exit
def signal_handler(sig, frame):
    pygame.quit()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Raspberry Pi detection
def is_raspberry_pi() -> bool:
    """Detect if running on a real Raspberry Pi (used only for mode validation)."""
    try:
        with open('/proc/device-tree/model', 'r', encoding='utf-8') as f:
            return 'Raspberry' in f.read()
    except Exception:
        return False

# Custom usage message
USAGE_MESSAGE = """
RPi Bitcoin Mining Difficulty Meter Display
───────────────────────────────────────────
Usage:
  python3 app.py --mode pi       # Raspberry Pi mode (fullscreen, auto-scaling for TFT or HDMI)
  python3 app.py --mode desktop  # Desktop/PC mode (windowed 480×320, for Linux/Windows/Mac)
""".strip()

# Parse arguments with full control
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="RPi Bitcoin Mining Difficulty Meter Display",
        add_help=False,
        usage=argparse.SUPPRESS
    )
    parser.add_argument(
        "--mode",
        choices=["pi", "desktop"],
        required=False
    )
    args, unknown = parser.parse_known_args()
    return args, unknown

args, unknown = parse_arguments()

if '--help' in sys.argv or '-h' in sys.argv or unknown or args.mode is None:
    print(USAGE_MESSAGE)
    sys.exit(0 if '--help' in sys.argv or '-h' in sys.argv else 1)

if (args.mode == "desktop" and is_raspberry_pi()) or (args.mode == "pi" and not is_raspberry_pi()):
    print(USAGE_MESSAGE)
    sys.exit(1)

# Global flag for rendering mode
IS_DESKTOP_MODE = (args.mode == "desktop")

import src.constants
src.constants.IS_DESKTOP_MODE = IS_DESKTOP_MODE

# Set RPi-specific environment variables ONLY in pi mode
if not IS_DESKTOP_MODE:
    os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
    os.environ["SDL_FBDEV"] = "/dev/fb0"

# Early pygame init
pygame.init()

# Import modules
from src.constants import MINER_IPS
from src.websockets import (
    websocket_listener,
    run_binance_websocket,
    run_kraken_websocket,
    fetch_initial_prices,
)
from src.miners import run_miners_polling
from src.mempool import mempool_polling_thread
from src.rendering import main_render_loop
from src.data import state

# Logging setup
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"
LOG_DIR.mkdir(exist_ok=True)

log_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=2 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)-8s | %(threadName)s | %(message)s",
    handlers=[
        log_handler,
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# Fetch initial prices
fetch_initial_prices(state)

# Start background threads (daemons)
threading.Thread(target=mempool_polling_thread, daemon=True, name="MempoolPoller").start()

for ip in MINER_IPS:
    threading.Thread(
        target=websocket_listener,
        args=(ip,),
        daemon=True,
        name=f"WS-{ip.split('.')[-1]}",
    ).start()

threading.Thread(
    target=run_binance_websocket, args=(state,), daemon=True, name="BinanceWS"
).start()

threading.Thread(
    target=run_kraken_websocket, args=(state,), daemon=True, name="KrakenWS"
).start()

threading.Thread(
    target=run_miners_polling, daemon=True, name="MinersPoller"
).start()

logger.info(f"Starting application in {'desktop' if IS_DESKTOP_MODE else 'Raspberry Pi'} mode...")
main_render_loop(state)
