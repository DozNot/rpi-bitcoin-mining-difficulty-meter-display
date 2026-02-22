# src/miners.py
"""
Polling for miner stats.
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

from .constants import MINER_IPS, MIN_ACTIVE_HASHRATE_TH
from .data import state

def fetch_miner_stats(ip: str) -> Tuple[float, float]:
    try:
        resp = requests.get(f"http://{ip}/api/system/info", timeout=4,
                            headers={"User-Agent": "rpi-bitcoin-mining-difficulty-meter-display/1.0"})
        data = resp.json()
        hr_gh = data.get("hashRate", 0.0)
        hr_th = hr_gh / 1000.0
        diff = data.get("bestDiff", 0.0)
        return (hr_th, diff) if hr_th > 0.05 else (0.0, diff)
    except Exception:
        return 0.0, 0.0

def run_miners_polling() -> None:
    with ThreadPoolExecutor(max_workers=16) as executor:
        while True:
            futures = {executor.submit(fetch_miner_stats, ip): ip for ip in MINER_IPS}
            total_hr = 0.0
            best_diff = 0.0
            active_count = 0
            for future in as_completed(futures):
                hr, diff = future.result()
                total_hr += hr
                best_diff = max(best_diff, diff)
                if hr > MIN_ACTIVE_HASHRATE_TH:
                    active_count += 1
            with state.miners_lock:
                state.miner_stats["total_hashrate_th"] = total_hr
                state.miner_stats["best_difficulty"] = best_diff
                state.miner_stats["active_count"] = active_count
            time.sleep(10)
