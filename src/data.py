# src/data.py
"""
Shared data structures and global state.
"""

from dataclasses import dataclass
from typing import Optional
from collections import deque
import threading
import time

from .constants import NUM_DIFFS_TO_KEEP, DATA_TIMEOUT_SEC

@dataclass
class TickerData:
    source: str
    price: Optional[float] = None
    change_24h: float = 0.0
    last_update: Optional[float] = None

    def is_fresh(self, now: float) -> bool:
        if self.last_update is None:
            return False
        return now - self.last_update < DATA_TIMEOUT_SEC

    def update(self, price: float, change: float) -> None:
        self.price = price
        self.change_24h = change
        self.last_update = time.time()

class AppState:
    def __init__(self):
        self.binance = TickerData("binance")
        self.kraken = TickerData("kraken")
        self.ticker_lock = threading.Lock()

        self.recent_diffs = deque(maxlen=NUM_DIFFS_TO_KEEP)
        self.recent_lock = threading.Lock()

        self.session_best_ts: float = 0.0
        self.session_best_diff: float = 0.0
        self.session_best_ip: str = ""

        self.connected_miners = set()
        self.connected_lock = threading.Lock()

        self.mempool_data = {
            "fees_sats_vb": None,
            "block_height": None,
            "mining_pool": None,
            "network_hashrate_eh": None,
            "network_difficulty": None,
            "block_timestamp": None,
        }
        self.mempool_lock = threading.Lock()

        self.miner_stats = {
            "total_hashrate_th": 0.0,
            "best_difficulty": 0.0,
            "active_count": 0,
        }
        self.miners_lock = threading.Lock()

state = AppState()
