"""
Display rendering module
"""
import os
import sys
import time
import pygame
import logging
from typing import Optional
from .constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    LOGICAL_HEIGHT,
    TARGET_FPS,
    BTC_LOGO_PATH,
    COLOR_HASHRATE_UP,
    INDICATOR_GREEN,
    INDICATOR_ORANGE,
    INDICATOR_RED,
    COLOR_PRICE_UP,
    COLOR_PRICE_DOWN,
    NUM_MINERS,
    MIN_DIFF_THRESHOLD,
    MAX_LINES_ON_SCREEN,
    IP_TO_NAME,
    IS_DESKTOP_MODE,
)
from .helpers import (
    format_hashrate,
    format_difficulty,
    format_compact_threshold,
    get_rarity_color_and_prefix,
    time_ago,
    format_network_hashrate,
    format_diff_for_network,
    format_share_diff,
)
from .data import state, AppState

logger = logging.getLogger(__name__)

# Display variables
screen: Optional[pygame.Surface] = None
logical_screen: Optional[pygame.Surface] = None
scale: float = 1.0
scaled_w: int = SCREEN_WIDTH
scaled_h: int = LOGICAL_HEIGHT if IS_DESKTOP_MODE else SCREEN_HEIGHT
offset_x: int = 0
offset_y: int = 0
last_render_data_hash: Optional[int] = None

MIN_WINDOW_W = 520
MIN_WINDOW_H = 380

# ====================== INITIALISATION ======================
if IS_DESKTOP_MODE:
    os.environ['SDL_VIDEO_CENTERED'] = '1'

    initial_scale = 1.5
    initial_w = int(SCREEN_WIDTH * initial_scale)
    initial_h = int(LOGICAL_HEIGHT * initial_scale)

    screen = pygame.display.set_mode((initial_w, initial_h), pygame.RESIZABLE)
    pygame.display.set_caption("Bitcoin Mining Difficulty Meter - Desktop Mode")
    logical_screen = pygame.Surface((SCREEN_WIDTH, LOGICAL_HEIGHT))

    scale = initial_scale
    scaled_w = initial_w
    scaled_h = initial_h
    offset_x = 0
    offset_y = 0
    pygame.mouse.set_visible(True)
    logger.info(f"Desktop scale: {MAX_LINES_ON_SCREEN} lines → {initial_w}×{initial_h}px (width max, ratio ok)")
else:
    info = pygame.display.Info()
    pw, ph = info.current_w, info.current_h
    screen = pygame.display.set_mode((pw, ph), pygame.FULLSCREEN)
    logical_screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    scale_x = pw / SCREEN_WIDTH
    scale_y = ph / SCREEN_HEIGHT
    scale = min(scale_x, scale_y)
    scaled_w = int(SCREEN_WIDTH * scale)
    scaled_h = int(SCREEN_HEIGHT * scale)
    offset_x = (pw - scaled_w) // 2
    offset_y = (ph - scaled_h) // 2
    pygame.mouse.set_visible(False)
    logger.info(f"RPi fullscreen – logical {SCREEN_WIDTH}×{SCREEN_HEIGHT} → physical {pw}×{ph}")

clock = pygame.time.Clock()

# Fonts & logo
FONT_TOP_TITLE = pygame.font.SysFont("dejavusans", 16)
FONT_TITLE = pygame.font.SysFont("dejavusans", 15, bold=True)
FONT_BTC_PRICE = pygame.font.SysFont("dejavusans", 21)
FONT_HASHRATE = pygame.font.SysFont("dejavusansmedium", 31)
FONT_NETWORK = pygame.font.SysFont("dejavusans", 16)
FONT_DIFF = pygame.font.SysFont("dejavusansmono", 20, bold=True)
FONT_SMALL = pygame.font.SysFont("dejavusans", 20)

btc_logo: Optional[pygame.Surface] = None
if os.path.isfile(BTC_LOGO_PATH):
    try:
        logo_raw = pygame.image.load(BTC_LOGO_PATH).convert_alpha()
        scale_factor = 28 / logo_raw.get_height()
        new_size = (int(logo_raw.get_width() * scale_factor), 28)
        btc_logo = pygame.transform.smoothscale(logo_raw, new_size)
        logger.info("Bitcoin logo loaded")
    except Exception as e:
        logger.error("BTC logo load failed: %s", e)

def main_render_loop(app_state: AppState) -> None:
    global last_render_data_hash, scale, scaled_w, scaled_h, offset_x, offset_y

    line_height = 28
    y_start = 120

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if IS_DESKTOP_MODE and event.type == pygame.VIDEORESIZE:
                win_w = max(MIN_WINDOW_W, event.w)
                win_h = max(MIN_WINDOW_H, event.h)

                scale_x = win_w / SCREEN_WIDTH
                scale_y = win_h / LOGICAL_HEIGHT

                scale = scale_x
                if LOGICAL_HEIGHT * scale > win_h:
                    scale = scale_y

                scaled_w = int(SCREEN_WIDTH * scale)
                scaled_h = int(LOGICAL_HEIGHT * scale)

                offset_x = (win_w - scaled_w) // 2
                offset_y = 0

                last_render_data_hash = None
                logger.debug(f"Desktop resize → {win_w}×{win_h} | scale={scale:.3f} | {MAX_LINES_ON_SCREEN} visible lines")

        # === DATA SNAPSHOTS ===
        now = time.time()
        with app_state.ticker_lock:
            binance_fresh = app_state.binance.is_fresh(now)
            kraken_fresh = app_state.kraken.is_fresh(now)
            ticker = app_state.binance if binance_fresh else app_state.kraken if kraken_fresh else None
            ticker_price = ticker.price if ticker else None
            ticker_change = ticker.change_24h if ticker else 0.0
            ticker_source = ticker.source if ticker else "none"
        with app_state.connected_lock:
            connected_count = len(app_state.connected_miners)
        with app_state.mempool_lock:
            mempool_snapshot = app_state.mempool_data.copy()
            network_difficulty = mempool_snapshot.get("network_difficulty")
        with app_state.miners_lock:
            miner_stats_snapshot = app_state.miner_stats.copy()
            total_hashrate = miner_stats_snapshot["total_hashrate_th"]
            session_best_diff_global = miner_stats_snapshot["best_difficulty"]
            active_miner_count = miner_stats_snapshot["active_count"]
        with app_state.recent_lock:
            recent_diffs_snapshot = list(app_state.recent_diffs)
            session_best_ts = app_state.session_best_ts
            session_best_diff = app_state.session_best_diff
            session_best_ip = app_state.session_best_ip

        # Network string & hash check
        network_parts = [
            f"{mempool_snapshot['fees_sats_vb']:.1f} sats/vB" if mempool_snapshot['fees_sats_vb'] is not None else "?",
            str(mempool_snapshot['block_height']) if mempool_snapshot['block_height'] is not None else "?",
            mempool_snapshot['mining_pool'] or "?",
            format_network_hashrate(mempool_snapshot['network_hashrate_eh']),
            format_diff_for_network(network_difficulty)
        ]
        network_str = " | ".join(network_parts)
        miners_connected_str = f"MINERS: {connected_count}/{NUM_MINERS}"
        recent_for_hash = recent_diffs_snapshot[-MAX_LINES_ON_SCREEN:]
        time_sensitive_hash = sum(max(0, int(now - ts)) for ts, _, _ in recent_for_hash)
        current_hash = hash((
            network_str, miners_connected_str, connected_count, len(recent_diffs_snapshot),
            recent_diffs_snapshot[-1][1] if recent_diffs_snapshot else 0.0,
            ticker_price or 0.0, ticker_change, ticker_source,
            total_hashrate, session_best_diff_global, active_miner_count, time_sensitive_hash,
        ))

        if current_hash == last_render_data_hash:
            clock.tick(TARGET_FPS)
            continue
        last_render_data_hash = current_hash

        logical_screen.fill((0, 0, 0))

        # === DRAWING ===
        if btc_logo:
            logo_x, logo_y = 20, 13
            logical_screen.blit(btc_logo, (logo_x, logo_y))
            btc_text = FONT_BTC_PRICE.render("BTC:", True, (255, 255, 255))
            btc_text_x = logo_x + btc_logo.get_width() + 8
            btc_text_y = logo_y + (btc_logo.get_height() - btc_text.get_height()) // 2
            logical_screen.blit(btc_text, (btc_text_x, btc_text_y))
            if ticker_price is not None:
                price_str = f"${ticker_price:,.2f}"
                price_color = COLOR_PRICE_UP if ticker_change >= 0 else COLOR_PRICE_DOWN
                price_surf = FONT_BTC_PRICE.render(price_str, True, price_color)
                price_x = btc_text_x + btc_text.get_width() + 5
                price_y = logo_y + (btc_logo.get_height() - price_surf.get_height()) // 2
                logical_screen.blit(price_surf, (price_x, price_y))

        miner_status_y = 19
        miner_surf = FONT_TOP_TITLE.render(miners_connected_str, True, (255, 255, 255))
        miner_x = SCREEN_WIDTH - miner_surf.get_width() - 35
        logical_screen.blit(miner_surf, (miner_x, miner_status_y))
        conn_color = (INDICATOR_GREEN if connected_count == NUM_MINERS else
                      INDICATOR_ORANGE if connected_count > 0 else INDICATOR_RED)
        circle_x = miner_x + miner_surf.get_width() + 10
        circle_y = miner_status_y + miner_surf.get_height() // 2
        pygame.draw.circle(logical_screen, conn_color, (circle_x, circle_y), 4)

        max_net_width = SCREEN_WIDTH - 40
        font_size = 16
        net_font = pygame.font.SysFont("dejavusans", font_size)
        net_surf = net_font.render(network_str, True, (180, 180, 180))
        while net_surf.get_width() > max_net_width and font_size > 9:
            font_size -= 1
            net_font = pygame.font.SysFont("dejavusans", font_size)
            net_surf = net_font.render(network_str, True, (180, 180, 180))
        net_y = 57
        net_x = 20 + (max_net_width - net_surf.get_width()) // 2
        logical_screen.blit(net_surf, (net_x, net_y))

        threshold_color, _ = get_rarity_color_and_prefix(MIN_DIFF_THRESHOLD, network_difficulty)
        title_fixed = FONT_TITLE.render("LAST SHARES > ", True, (255, 255, 255))
        threshold_text = FONT_TITLE.render(format_compact_threshold(MIN_DIFF_THRESHOLD), True, threshold_color)
        title_y = 90
        logical_screen.blit(title_fixed, (20, title_y))
        logical_screen.blit(threshold_text, (20 + title_fixed.get_width(), title_y))

        hr_str = format_hashrate(total_hashrate)
        best_diff_str = format_difficulty(session_best_diff_global)
        combined_str = f"{hr_str} - {best_diff_str}"
        all_connected = connected_count == NUM_MINERS
        all_active = active_miner_count == NUM_MINERS
        has_activity = connected_count > 0 and active_miner_count > 0
        hr_color = (COLOR_HASHRATE_UP if all_connected and all_active else
                    INDICATOR_ORANGE if has_activity else INDICATOR_RED)
        combined_surf = FONT_HASHRATE.render(combined_str, True, hr_color)
        logical_screen.blit(combined_surf, (SCREEN_WIDTH - combined_surf.get_width() - 20, 87))

        pygame.draw.line(logical_screen, (70, 70, 70), (20, 112), (SCREEN_WIDTH - 20, 112), 1)

        shown_shares = list(reversed(recent_diffs_snapshot))[:MAX_LINES_ON_SCREEN]
        has_session_best = session_best_diff > 0
        name_texts = []
        if has_session_best:
            name_texts.append("SESSION BEST:")
        for _, _, ip in shown_shares:
            miner_name = IP_TO_NAME.get(ip, ip.rsplit(".", 1)[-1] if ip else "Unknown")
            name_texts.append("→ " + miner_name)
        max_name_width = max(
            FONT_SMALL.render(text, True, (255, 255, 255)).get_width() for text in name_texts
        ) if name_texts else 0
        gap = 2 if has_session_best else 0
        list_start_y = y_start + (line_height + gap if has_session_best else 0)
        name_x = 20
        diff_x = name_x + max_name_width + 20
        time_x_end = SCREEN_WIDTH - 20

        if shown_shares or has_session_best:
            if has_session_best:
                y_pos = y_start
                pygame.draw.rect(logical_screen, (21, 21, 21), (20, y_pos, SCREEN_WIDTH - 40, line_height))
                color, prefix = get_rarity_color_and_prefix(session_best_diff, network_difficulty)
                best_miner = IP_TO_NAME.get(session_best_ip, session_best_ip.rsplit(".", 1)[-1] if session_best_ip else "Unknown")
                name_surf = FONT_SMALL.render(f"➊ {best_miner} ", True, color)
                logical_screen.blit(name_surf, (name_x, y_pos + (line_height - name_surf.get_height()) // 2))
                diff_text = prefix + format_share_diff(session_best_diff)
                diff_surf = FONT_DIFF.render(diff_text, True, color)
                logical_screen.blit(diff_surf, (diff_x, y_pos + (line_height - diff_surf.get_height()) // 2))
                ago_text = time_ago(now - session_best_ts)
                ago_surf = FONT_SMALL.render(ago_text, True, color)
                logical_screen.blit(ago_surf, (time_x_end - ago_surf.get_width(), y_pos + (line_height - ago_surf.get_height()) // 2))

            for i, (ts, diff, ip) in enumerate(shown_shares):
                y_pos = list_start_y + i * line_height
                color, prefix = get_rarity_color_and_prefix(diff, network_difficulty)
                miner_name = IP_TO_NAME.get(ip, ip.rsplit(".", 1)[-1])
                name_surf = FONT_SMALL.render("→ " + miner_name, True, color)
                logical_screen.blit(name_surf, (name_x, y_pos + (line_height - name_surf.get_height()) // 2))
                diff_text = prefix + format_share_diff(diff)
                diff_surf = FONT_DIFF.render(diff_text, True, color)
                logical_screen.blit(diff_surf, (diff_x, y_pos + (line_height - diff_surf.get_height()) // 2))
                ago_text = time_ago(now - ts)
                ago_surf = FONT_SMALL.render(ago_text, True, color)
                logical_screen.blit(ago_surf, (time_x_end - ago_surf.get_width(), y_pos + (line_height - ago_surf.get_height()) // 2))
        else:
            waiting_surf = FONT_SMALL.render("Waiting for first shares...", True, (140, 140, 140))
            logical_screen.blit(waiting_surf, ((SCREEN_WIDTH - waiting_surf.get_width()) // 2, 185))

        # Final blit
        scaled_surface = pygame.transform.smoothscale(logical_screen, (scaled_w, scaled_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled_surface, (offset_x, offset_y))
        pygame.display.flip()
        clock.tick(TARGET_FPS)
