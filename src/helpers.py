# src/helpers.py
"""
Helper functions for formatting and visuals.
"""

import math
from typing import Optional, Tuple

from .constants import COLOR_POOR, COLOR_COMMON, COLOR_UNCOMMON, COLOR_RARE, COLOR_EPIC, COLOR_LEGENDARY

def format_hashrate(th: float) -> str:
    return f"{th:.2f} TH/s"

def format_difficulty(diff: float) -> str:
    if diff <= 0: return "0"
    units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
    exponent = math.floor(math.log10(diff) / 3) if diff > 0 else 0
    scaled = diff / (1000 ** exponent)
    unit = units[min(exponent, len(units)-1)]
    if scaled == int(scaled):
        return f"{int(scaled)} {unit}"
    return f"{scaled:.2f} {unit}"

def format_compact_threshold(value: float) -> str:
    if value <= 0: return "0"
    units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
    exponent = math.floor(math.log10(value) / 3) if value > 0 else 0
    scaled = value / (1000 ** exponent)
    unit = units[min(exponent, len(units)-1)]
    if scaled == int(scaled):
        return f"{int(scaled)} {unit}"
    return f"{scaled:.2f} {unit}"

def format_share_diff(diff: float) -> str:
    if diff <= 0: return " 0 "
    units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
    exponent = math.floor(math.log10(diff) / 3) if diff > 0 else 0
    scaled = diff / (1000 ** exponent)
    unit = units[min(exponent, len(units)-1)]
    num_str = f"{scaled:.2f}" if unit else f"{int(scaled)}"
    return f"{num_str:>7} {unit}"

def get_rarity_color_and_prefix(diff: float, net_diff: Optional[float] = None) -> Tuple[Tuple[int, int, int], str]:
    prefix = ""
    if diff < 1_000_000:
        color = COLOR_POOR
    elif diff < 50_000_000:
        color = COLOR_COMMON
    elif diff < 1_000_000_000:
        color = COLOR_UNCOMMON
    elif diff < 500_000_000_000:
        color = COLOR_RARE
    elif diff < 1_000_000_000_000:
        color = COLOR_EPIC
    else:
        color = COLOR_LEGENDARY
        if net_diff is not None and diff > net_diff:
            prefix = " ✦ "
    return color, prefix

def time_ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds:02d} sec ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    days = hours // 24
    if days < 365:
        day_word = "day" if days == 1 else "days"
        return f"{days} {day_word} ago"
    years = days // 365
    return f"{years} y ago"

def format_diff_for_network(diff: Optional[float]) -> str:
    if diff is None: return "?"
    if diff <= 0: return "0"
    units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
    exponent = math.floor(math.log10(diff) / 3) if diff > 0 else 0
    scaled = diff / (1000 ** exponent)
    unit = units[min(exponent, len(units)-1)]
    if scaled == int(scaled):
        return f"{int(scaled)} {unit}"
    return f"{scaled:.2f} {unit}"

def format_network_hashrate(hr_eh: Optional[float]) -> str:
    if hr_eh is None or hr_eh <= 0:
        return "?"
    hr_hps = hr_eh * 1e18
    exponent = math.floor(math.log10(max(hr_hps, 1)) / 3)
    scaled = hr_hps / (1000 ** exponent)
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s", "YH/s"]
    unit = units[min(exponent, len(units) - 1)]
    prec = 2 if exponent >= 6 else 2
    return f"{scaled:.{prec}f} {unit}"
