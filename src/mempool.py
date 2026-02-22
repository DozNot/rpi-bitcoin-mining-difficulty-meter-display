# src/mempool.py
"""
Polling for mempool data.
"""

import time
import logging
import requests

from .constants import MEMPOOL_UPDATE_EVERY
from .data import state

logger = logging.getLogger(__name__)

def mempool_polling_thread() -> None:
    headers = {"User-Agent": "rpi-bitcoin-mining-difficulty-meter-display/1.0"}
    session = requests.Session()
    while True:
        try:
            r = session.get("https://mempool.space/api/v1/fees/precise", timeout=12, headers=headers)
            fees = float(r.json().get("halfHourFee", None))

            r = session.get("https://mempool.space/api/blocks/tip/height", timeout=10, headers=headers)
            height = int(r.text) if r.text.isdigit() else None

            pool_name = "Unknown"
            net_difficulty = None
            block_ts = None
            if height:
                r = session.get(f"https://mempool.space/api/block-height/{height}", timeout=10, headers=headers)
                blk_hash = r.text.strip()
                if blk_hash:
                    r = session.get(f"https://mempool.space/api/v1/block/{blk_hash}", timeout=12, headers=headers)
                    data = r.json()
                    pool_name = data.get("extras", {}).get("pool", {}).get("name", "Unknown")
                    net_difficulty = data.get("difficulty")
                    block_ts = data.get("timestamp")

            r = session.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=12, headers=headers)
            current_hr = r.json().get("currentHashrate")
            hr_eh = (current_hr / 1e18) if current_hr is not None else None

            with state.mempool_lock:
                state.mempool_data.update({
                    "fees_sats_vb": fees,
                    "block_height": height,
                    "mining_pool": pool_name,
                    "network_hashrate_eh": hr_eh,
                    "network_difficulty": net_difficulty,
                    "block_timestamp": block_ts,
                })
        except Exception as e:
            logger.error("Mempool API error: %s", e)
            with state.mempool_lock:
                state.mempool_data.update({
                    "fees_sats_vb": None,
                    "block_height": None,
                    "mining_pool": None,
                    "network_hashrate_eh": None,
                    "network_difficulty": None,
                    "block_timestamp": None,
                })
        time.sleep(MEMPOOL_UPDATE_EVERY)
