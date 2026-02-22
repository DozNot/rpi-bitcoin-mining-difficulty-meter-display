# src/websockets.py
"""
WebSocket connections for miners and exchanges.
"""

import time
import logging
import websocket
import json
import requests

from .constants import MIN_DIFF_THRESHOLD, ANSI_ESCAPE, IP_TO_NAME
from .helpers import format_diff_for_network
from .data import state

logger = logging.getLogger(__name__)

def parse_miner_log_line(line: str, source_ip: str) -> None:
    if "asic_result" not in line:
        return
    try:
        if "diff " in line:
            after_diff = line.split("diff ", 1)[1]
            if " of " in after_diff:
                diff_str = after_diff.split(" of ", 1)[0]
            elif "/" in after_diff:
                diff_str = after_diff.split("/", 1)[0]
            else:
                return
        elif "diff=" in line:
            diff_str = line.split("diff=", 1)[1].split()[0].rstrip(",")
        else:
            return
        diff_val = float(diff_str.strip())
        if diff_val < MIN_DIFF_THRESHOLD:
            return
        ts = time.time()
        with state.recent_lock:
            state.recent_diffs.append((ts, diff_val, source_ip))
            if diff_val > state.session_best_diff:
                state.session_best_ts = ts
                state.session_best_diff = diff_val
                state.session_best_ip = source_ip
                logger.info(
                    "New session best! %s → %s",
                    IP_TO_NAME.get(source_ip, source_ip),
                    format_diff_for_network(diff_val)
                )
        logger.debug(
            "Accepted share %s → %s",
            IP_TO_NAME.get(source_ip, source_ip),
            format_diff_for_network(diff_val)
        )
    except (IndexError, ValueError, TypeError) as e:
        logger.debug("Parse failed: %s → %s", line, e)

def websocket_listener(ip: str) -> None:
    ws_url = f"ws://{ip}/api/ws"
    reconnect_delay = 5.0
    ws = None
    while True:
        try:
            ws = websocket.create_connection(ws_url, timeout=15)
            logger.info("WS connected → %s", ip)
            with state.connected_lock:
                state.connected_miners.add(ip)
            while True:
                try:
                    message = ws.recv()
                    if isinstance(message, bytes):
                        continue
                    for raw_line in message.splitlines():
                        clean_line = ANSI_ESCAPE.sub('', raw_line).strip()
                        if clean_line:
                            parse_miner_log_line(clean_line, ip)
                except UnicodeDecodeError:
                    continue
                except websocket.WebSocketConnectionClosedException:
                    break
                except Exception as e:
                    logger.warning("WS receive error (%s): %s", ip, e)
                    break
        except Exception as e:
            logger.warning("WS connection failed (%s): %s", ip, e)
        finally:
            with state.connected_lock:
                state.connected_miners.discard(ip)
            if ws:
                try:
                    ws.close()
                except:
                    pass
            ws = None
        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 1.5, 60.0)

def run_binance_websocket(state) -> None:
    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("s", "").lower() != "btcusdt":
                return
            price = float(data["c"])
            change_pct = float(data["P"])
            with state.ticker_lock:
                state.binance.update(price, change_pct)
        except Exception as e:
            logger.warning("Binance parse error: %s", e)

    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://stream.binance.com:9443/ws/btcusdt@ticker",
                on_message=on_message
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            logger.error("Binance WS error: %s", e)
        time.sleep(5)

def run_kraken_websocket(state) -> None:
    def on_message(ws, message):
        try:
            msg = json.loads(message)
            if not isinstance(msg, list) or msg[2] != "ticker":
                return
            _, ticker_data, _, pair = msg
            if pair != "XBT/USD":
                return
            price = float(ticker_data["c"][0])
            open_24h = float(ticker_data["o"][1])
            change_pct = ((price - open_24h) / open_24h * 100) if open_24h > 0 else 0.0
            with state.ticker_lock:
                state.kraken.update(price, change_pct)
        except Exception as e:
            logger.warning("Kraken parse error: %s", e)

    def on_open(ws):
        ws.send(json.dumps({
            "event": "subscribe",
            "pair": ["XBT/USD"],
            "subscription": {"name": "ticker"}
        }))

    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://ws.kraken.com/",
                on_message=on_message,
                on_open=on_open
            )
            ws.run_forever(ping_interval=25, ping_timeout=10)
        except Exception as e:
            logger.error("Kraken WS error: %s", e)
        time.sleep(5)

def fetch_initial_prices(state) -> None:
    headers = {"User-Agent": "rpi-bitcoin-mining-difficulty-meter-display/1.0"}
    # Binance
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=5, headers=headers)
        if r.status_code == 200:
            data = r.json()
            price = float(data["lastPrice"])
            change_pct = float(data["priceChangePercent"])
            with state.ticker_lock:
                state.binance.update(price, change_pct)
    except Exception as e:
        logger.warning("Binance initial fetch failed: %s", e)
    # Kraken
    try:
        r = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5, headers=headers)
        if r.status_code == 200:
            data = r.json()["result"]["XXBTZUSD"]
            price = float(data["c"][0])
            open_24h = float(data["o"])
            change_pct = ((price - open_24h) / open_24h * 100) if open_24h > 0 else 0.0
            with state.ticker_lock:
                state.kraken.update(price, change_pct)
    except Exception as e:
        logger.warning("Kraken initial fetch failed: %s", e)
