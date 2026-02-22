# src/constants.py
"""
Global constants and configuration loading.
"""

import json
import os
import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config.json')

DEFAULT_CONFIG = {
    "miner_ips": [],
    "ip_to_name": {},
    "btc_logo_path": "logos/btc.png",
    "min_diff_threshold": 75000,
    "min_active_hashrate_th": 0.25,
    "data_timeout_sec": 60.0,
    "num_diffs_to_keep": 20,
    "max_lines_on_screen": 6,
    "screen_width": 480,
    "screen_height": 320,
    "target_fps": 8,
    "mempool_update_every": 30.0
}

try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG: Dict[str, Any] = json.load(f)
    logger.info("Config loaded successfully")
except FileNotFoundError as e:
    logger.warning(f"Config file not found: {e}. Using default configuration.")
    CONFIG = DEFAULT_CONFIG
except json.JSONDecodeError as e:
    logger.warning(f"Invalid JSON in config file: {e}. Using default configuration.")
    CONFIG = DEFAULT_CONFIG

MINER_IPS = CONFIG['miner_ips']
IP_TO_NAME = CONFIG['ip_to_name']
NUM_MINERS = len(MINER_IPS)
NUM_DIFFS_TO_KEEP = CONFIG['num_diffs_to_keep']
MAX_LINES_ON_SCREEN = CONFIG['max_lines_on_screen']
SCREEN_WIDTH = CONFIG['screen_width']
SCREEN_HEIGHT = CONFIG['screen_height']
TARGET_FPS = CONFIG['target_fps']
MEMPOOL_UPDATE_EVERY = CONFIG['mempool_update_every']
MIN_DIFF_THRESHOLD = CONFIG['min_diff_threshold']
MIN_ACTIVE_HASHRATE_TH = CONFIG['min_active_hashrate_th']
DATA_TIMEOUT_SEC = CONFIG['data_timeout_sec']
BTC_LOGO_PATH = os.path.join(PROJECT_ROOT, CONFIG['btc_logo_path'])

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

COLOR_POOR = (157, 157, 157)
COLOR_COMMON = (255, 255, 255)
COLOR_UNCOMMON = (21, 158, 16)
COLOR_RARE = (0, 112, 221)
COLOR_EPIC = (163, 53, 238)
COLOR_LEGENDARY = (255, 128, 0)
INDICATOR_GREEN = (21, 158, 16)
INDICATOR_ORANGE = (255, 165, 0)
INDICATOR_RED = (255, 0, 0)
COLOR_PRICE_UP = (21, 158, 16)
COLOR_PRICE_DOWN = (255, 0, 0)
COLOR_HASHRATE_UP = (100, 180, 255)

LINE_HEIGHT = 28
BASE_HEIGHT = 320
MAX_LINES_ON_SCREEN = min(CONFIG['max_lines_on_screen'], 21)
LOGICAL_HEIGHT = BASE_HEIGHT + max(0, (MAX_LINES_ON_SCREEN - 6) * LINE_HEIGHT)

IS_DESKTOP_MODE: bool = False
