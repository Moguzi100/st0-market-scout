import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
import os
import tempfile
from datetime import datetime, timezone
import pytz

# ==========================================
# SIVUN ASETUKSET
# ==========================================
st.set_page_config(
    page_title="ST0 Market Scout v3.6 Quant",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# YHTIÖANKKURIT, TASELUOKAT (FORT/SELF/DEBT), Q-LAATULUOKAT (Q1/Q2/Q3), DNA-RAJAT & VERROKIT (21 KOHDETTA — APEX v7.1.0)
# ==========================================
TICKERS = {
    # KORI 1: Core Compounders
    "GOOG":    {"yf": ["GOOG"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 19.5, "hot_min": 28.0, "peers": ["META", "AMZN"],  "dna_ma": 200, "kw": ["alphabet", "google", "waymo", "gemini", "tpu", "youtube", "sundar", "doj"]},
    "AMZN":    {"yf": ["AMZN"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "SELF", "q_tier": "Q1", "val_m": "PE", "cheap_max": 25.0, "hot_min": 35.0, "peers": ["GOOG", "META"],  "dna_ma": 100, "kw": ["amazon", "aws", "amzn", "jassy", "prime", "trainium", "anthropic"]},
    "TTWO":    {"yf": ["TTWO"],          "bucket": "K1:Core",  "tier": "CYC",  "bs": "SELF", "q_tier": "Q2", "val_m": "PE", "cheap_max": 22.0, "hot_min": 30.0, "peers": ["AAPL", "AMZN"],  "dna_ma": 200, "kw": ["take-two", "gta", "rockstar", "ttwo", "zynga", "2k"]},
    "AAPL":    {"yf": ["AAPL"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 27.0, "hot_min": 33.5, "peers": ["GOOG", "META"],  "dna_ma": 200, "kw": ["apple", "iphone", "ipad", "mac", "tim cook", "aapl", "foxconn"]},
    "META":    {"yf": ["META"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 20.0, "hot_min": 29.0, "peers": ["GOOG", "AMZN"],  "dna_ma": 100, "kw": ["meta", "zuckerberg", "instagram", "whatsapp", "llama", "threads"]},
    # KORI 2: AI & Semi Stack
    "AVGO":    {"yf": ["AVGO"],          "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 24.0, "hot_min": 38.0, "peers": ["NVDA", "ANET"],  "dna_ma": 50,  "kw": ["broadcom", "avgo", "vmware", "hock tan", "custom chip", "xpu", "tomahawk"]},
    "NVDA":    {"yf": ["NVDA"],          "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 28.0, "hot_min": 50.0, "peers": ["AVGO", "AMD"],   "dna_ma": 50,  "kw": ["nvidia", "nvda", "blackwell", "rubin", "jensen", "kress", "colette", "geforce", "cuda"]},
    "AMD":     {"yf": ["AMD"],           "bucket": "K2:Semi",  "tier": "BETA", "bs": "SELF", "q_tier": "Q2", "val_m": "PE", "cheap_max": 26.0, "hot_min": 45.0, "peers": ["NVDA", "AVGO"],  "dna_ma": 200, "kw": ["amd", "advanced micro", "lisa su", "instinct", "epyc", "ryzen"]},
    "MU":      {"yf": ["MU"],            "bucket": "K2:Semi",  "tier": "CYC",  "bs": "FORT", "q_tier": "Q2", "val_m": "PE", "cheap_max": 12.0, "hot_min": 24.0, "peers": ["TSM", "NVDA"],   "dna_ma": 100, "kw": ["micron", "hbm", "dram", "nand", "sanjay", "memory"]},
    "TSM":     {"yf": ["TSM"],           "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 18.0, "hot_min": 28.0, "peers": ["ASML", "NVDA"],  "dna_ma": 50,  "kw": ["tsmc", "taiwan semi", "cowos", "foundry", "wafer"]},
    "ASML":    {"yf": ["ASML"],          "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 27.0, "hot_min": 42.0, "peers": ["TSM", "KLAC"],   "dna_ma": 200, "kw": ["asml", "euv", "lithography", "fouquet", "bookings", "soxx"]},
    # KORI 3: High-Beta & Frontier
    "SPCX":    {"yf": ["SPCX", "DXYZ"],  "bucket": "K3:Beta",  "tier": "CYC",  "bs": "DEBT", "q_tier": "Q3", "val_m": "PE", "cheap_max": 35.0, "hot_min": 65.0, "peers": ["TSLA", "NBIS"],  "dna_ma": 50,  "kw": ["spacex", "starlink", "starship", "falcon", "spcx", "dxyz"]},
    "MSTR":    {"yf": ["MSTR"],          "bucket": "K3:Beta",  "tier": "CYC",  "bs": "DEBT", "q_tier": "Q3", "val_m": "PB", "cheap_max": 1.10, "hot_min": 2.50, "peers": ["BTC-USD", "NBIS"], "dna_ma": 50, "kw": ["microstrategy", "strategy", "saylor", "mstr", "msci"]},
    # KORI 4: Suomi / EUR
    "WRT1V":   {"yf": ["WRT1V.HE"],      "bucket": "K4:Suomi", "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 19.0, "hot_min": 22.5, "peers": ["NOKIA", "FRAMERY"], "dna_ma": 100, "kw": ["wärtsilä", "wartsila", "agnevall", "marine", "energy storage", "engine"]},
    "FRAMERY": {"yf": ["FRAMERY.HE"],    "bucket": "K4:Suomi", "tier": "CYC",  "bs": "SELF", "q_tier": "Q2", "val_m": "PE", "cheap_max": 12.5, "hot_min": 16.5, "peers": ["WRT1V", "NOKIA"], "dna_ma": 50,  "kw": ["framery", "hlt", "office pod"]},
    # SEURANTALISTA (Watchlist)
    "ANET":    {"yf": ["ANET"],          "bucket": "WATCH",    "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 27.0, "hot_min": 40.0, "peers": ["AVGO", "NVDA"],  "dna_ma": 50,  "kw": ["arista", "anet", "ethernet", "switch", "ullal", "networking"]},
    "KLAC":    {"yf": ["KLAC"],          "bucket": "WATCH",    "tier": "CORE", "bs": "FORT", "q_tier": "Q1", "val_m": "PE", "cheap_max": 21.0, "hot_min": 29.0, "peers": ["ASML", "TSM"],   "dna_ma": 100, "kw": ["kla", "klac", "metrology", "inspection", "wafer", "wallace"]},
    "NBIS":    {"yf": ["NBIS"],          "bucket": "WATCH",    "tier": "CYC",  "bs": "DEBT", "q_tier": "Q3", "val_m": "PE", "cheap_max": 30.0, "hot_min": 60.0, "peers": ["AMD", "SPCX"],   "dna_ma": 50,  "kw": ["nebius", "nbis", "arkady", "toloka", "avride"]},
    "NOKIA":   {"yf": ["NOKIA.HE"],      "bucket": "WATCH",    "tier": "CYC",  "bs": "SELF", "q_tier": "Q2", "val_m": "PE", "cheap_max": 12.0, "hot_min": 16.5, "peers": ["WRT1V", "FRAMERY"], "dna_ma": 200, "kw": ["nokia", "lundmark", "hotard", "infinera", "5g", "telecom"]},
    "BTC-USD": {"yf": ["BTC-USD"],       "bucket": "WATCH",    "tier": "BTC",  "bs": "DEBT", "q_tier": "Q3", "val_m": "NONE", "cheap_max": 0.0, "hot_min": 999.0, "peers": ["MSTR", "TSLA"], "dna_ma": 50,  "kw": ["bitcoin", "btc", "crypto", "ibit", "etf"]},
    "TSLA":    {"yf": ["TSLA"],          "bucket": "WATCH",    "tier": "BETA", "bs": "SELF", "q_tier": "Q2", "val_m": "PE", "cheap_max": 55.0, "hot_min": 120.0, "peers": ["SPCX", "NVDA"], "dna_ma": 200, "kw": ["tesla", "tsla", "musk", "cybercab", "robotaxi", "megapack", "fsd"]},
}

MACRO_TICKERS = {
    "VIX": "^VIX",
    "VXN": "^VXN",
    "US10Y": "^TNX",
    "NQ_FUT": "NQ=F",
    "ES_FUT": "ES=F",
    "QQQ": "QQQ",
    "SMH": "SMH",
    "SPY": "SPY",
    "EURUSD": "EURUSD=X"
}

MACRO_NEWS_PRIORITY = ["SPY", "US10Y", "ES_FUT", "VIX"]
SECTOR_NEWS_PRIORITY = ["SMH", "QQQ", "NQ_FUT"]

BS_HUMAN_LABELS = {
    "FORT": "🛡️ Linnoitus",
    "SELF": "⚙️ Tulorahoitus",
    "DEBT": "⚠️ Korkoherkkä"
}

NOISE_PHRASES = [
    "stocks to buy", "stock to buy", "if you invested", "motley fool",
    "why this stock", "millionaire-maker", "retirees", "dividend stocks",
    "these 3 stocks", "3 stocks", "2 stocks", "top stocks", "stocks to watch",
    "years ago", "what is it worth", "invested in each", "biggest winner"
]

# ==========================================
# LASKENTAFUNKTIOT: WILDER RSI, U-CURVE pRVOL, KORKOMATRIISI & UUTISET
# ==========================================
def calc_wilder_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def calc_pace_rvol(raw_vol, avg_vol_20, market_session, used_yf, sym, now_fi, now_ny, has_today_vol):
    if avg_vol_20 <= 0:
        return 1.0
    if market_session != "LIVE" or sym == "BTC-USD" or not has_today_vol:
        return round(raw_vol / avg_vol_20, 2)

    if ".HE" in used_yf:
        open_dt = now_fi.replace(hour=10, minute=0, second=0, microsecond=0)
        total_min = 510.0
        elapsed = (now_fi - open_dt).total_seconds() / 60.0
    else:
        open_dt = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
        total_min = 390.0
        elapsed = (now_ny - open_dt).total_seconds() / 60.0

    if elapsed <= 0:
        return round(raw_vol / avg_vol_20, 2)
    if elapsed >= total_min:
        return round(raw_vol / avg_vol_20, 2)

    eff_min = max(15.0, elapsed)
    f = eff_min / total_min
    # Monotoninen U-käyrä: painottaa avaus- ja päätöstunnin korkeaa instituutiovolyymia
    expected_share = max(0.06, min(1.0, f + 0.09 * float(np.sin(2.0 * np.pi * f))))
    return round((raw_vol / avg_vol_20) / expected_share, 2)

def classify_rate_regime(us10y_info):
    p = float(us10y_info.get("price", 0.0))
    bps_1d = int(us10y_info.get("bps_1d", 0))
    bps_20d = int(us10y_info.get("bps_20d", 0))
    if p >= 5.35 or bps_20d >= 20 or bps_1d >= 8:
        return "RATE_SHOCK"
    if p >= 5.15:
        return "RATE_ELEVATED"
    return "RATE_CALM"

def classify_dna_valuation_zone(cfg, f_pe_valid, f_pe, t_pe, valid_pb, pb, high_growth_quality):
    """Algoritmi B: Luokittelee arvostuksen suoraan DNA-rajoihin ([CHEAP] / [FAIR] / [HOT])."""
    val_m = cfg.get("val_m", "PE")
    if val_m == "NONE":
        return ""
    cheap_max = float(cfg.get("cheap_max", 0.0))
    hot_min = float(cfg.get("hot_min", 999.0))
    metric_val = None
    if val_m == "PB" and valid_pb and pb is not None:
        metric_val = float(pb)
    elif val_m == "PE":
        if f_pe_valid and f_pe is not None:
            metric_val = float(f_pe)
        elif high_growth_quality and t_pe is not None and 2.0 < float(t_pe) < 250.0:
            metric_val = float(t_pe)
    if metric_val is None or metric_val <= 0:
        return ""
    if metric_val <= cheap_max:
        return "[CHEAP]"
    if metric_val >= hot_min:
        return "[HOT]"
    return "[FAIR]"

def compute_nordnet_clock_status(now_fi):
    """Algoritmi A: Laskee Nordnetin kaupankäynti-ikkunat (OMXH 10-18:30, USA PRE 11-16:30, USA LIVE 16:30-23:00)."""
    wd = now_fi.weekday()
    mins_now = now_fi.hour * 60 + now_fi.minute
    if wd >= 5:
        return "VIIKONLOPPU (OMXH & USA suljettu, BTC 24/7) | ILTAMOODI: TASO 0 (Lepo)"
    # OMXH: 10:00 (600) - 18:30 (1110)
    if mins_now < 600:
        omxh_s = f"SULJETTU (avaukseen {(600 - mins_now) // 60}h {(600 - mins_now) % 60}min klo 10:00)"
    elif mins_now <= 1110:
        rem = 1110 - mins_now
        omxh_s = f"LIVE (sulkuun {rem // 60}h {rem % 60}min klo 18:30)"
    else:
        omxh_s = "SULJETTU (klo 18:30 päätös)"
    # USA Nordnet: PRE 11:00 (660) - 16:30 (990), LIVE 16:30 (990) - 23:00 (1380)
    if mins_now < 660:
        usa_s = f"YÖSULKU (Aamuportti; Pre-Market klo 11:00 {(660 - mins_now) // 60}h {(660 - mins_now) % 60}min)"
    elif mins_now < 990:
        rem_open = 990 - mins_now
        usa_s = f"PRE-MARKET (klo 16:30 avaukseen {rem_open // 60}h {rem_open % 60}min; Nordnet sulku klo 23:00)"
    elif mins_now <= 1380:
        rem_cls = 1380 - mins_now
        usa_s = f"LIVE (Nordnet klo 23:00 sulkuun {rem_cls // 60}h {rem_cls % 60}min — EI After-Marketia 23 jälkeen!)"
    else:
        usa_s = "SULJETTU NORDNETISSA (klo 23:00 sulkulukko; laajennetut pilkit rauenneet)"
    ilta = "TASO 2 (Pe Power Hour klo 21:00-22:45)" if wd == 4 else "TASO 0 (Oletus nukkumaan klo 21:00-21:30)"
    return f"OMXH: {omxh_s} | USA: {usa_s} | ILTAMOODI: {ilta}"

def compute_nordnet_trade_quant(row, cfg, macro_info):
    """Algoritmi D: Esilaskee Nordnet-rajahinnat (+0.25x ADR / Flush-Trap, -0.25x ADR), kulut, 1R-riskin, Netto R:R:n ja Netto E[V]:n."""
    live_p = float(row["Hinta"])
    adr_pct = max(0.5, float(row["ADR%"]))
    dyn_sup = float(row["_dyn_sup_val"])
    dyn_trim = float(row["_dyn_trim_val"])
    ses = str(row["Sessio"])
    bs_tier = cfg.get("bs", "SELF")
    q_tier = cfg.get("q_tier", "Q2")
    is_he = ".HE" in cfg["yf"][0]
    val_zone = str(row.get("_val_zone", ""))
    rsi_r = float(row["RSI(14)"])
    is_cash_burner = bool(row.get("_is_cash_burner", False))

    meta_r = macro_info.get("META_REGIME", {})
    rate_regime = meta_r.get("rate_regime", "RATE_CALM")
    vix_p = float(macro_info.get("VIX", {}).get("price", 20.0))
    eur_usd = float(macro_info.get("EURUSD", {}).get("price", 1.10) or 1.10)
    if eur_usd <= 0.2:
        eur_usd = 1.10

    buffer_muted = (rate_regime == "RATE_SHOCK") or (vix_p > 28.0) or (rate_regime == "RATE_ELEVATED" and bs_tier == "DEBT")
    buf_pct = 0.0 if buffer_muted else max(0.005, min(0.25 * (adr_pct / 100.0), 0.015))
    sup_buffered = round(dyn_sup * (1.0 + buf_pct), 2)

    if ses == "PRE" and not is_he:
        flush_cap = round(live_p * (1.0 - 0.40 * (adr_pct / 100.0)), 2)
        buy_limit = round(min(sup_buffered, flush_cap), 2)
        buy_tag = "Flush-Trap" if buy_limit < sup_buffered else f"+{round(buf_pct * 100, 1)}%"
    else:
        buy_limit = sup_buffered
        buy_tag = "0%-Puskuri" if buffer_muted else f"+{round(buf_pct * 100, 1)}%"

    sell_buf_pct = max(0.005, min(0.25 * (adr_pct / 100.0), 0.015))
    sell_limit = round(dyn_trim * (1.0 - sell_buf_pct), 2)
    if sell_limit <= buy_limit:
        sell_limit = round(buy_limit * (1.0 + max(0.05, 1.8 * adr_pct / 100.0)), 2)

    curr_label = "EUR" if is_he else "USD"
    if row["Ticker"].startswith("BTC"):
        return None

    if is_he:
        target_eur = 2500.0
        shares = max(1, int(target_eur // max(0.01, buy_limit)))
        order_eur = round(shares * buy_limit, 2)
        fee_eur = round(max(10.0, 0.002 * order_eur), 2)
    else:
        target_usd = 3000.0
        shares = max(1, int(target_usd // max(0.01, buy_limit)))
        order_usd = shares * buy_limit
        order_eur = round(order_usd / eur_usd, 2)
        fee_eur = round(30.0 + 0.005 * order_eur, 2)

    fee_pct = round((fee_eur / max(1.0, order_eur)) * 100.0, 2)
    gross_gain_pct = ((sell_limit / max(0.01, buy_limit)) - 1.0) * 100.0
    net_gain_eur = int(round(order_eur * (gross_gain_pct / 100.0) - fee_eur))

    stop_dist_pct = max(3.5, min(1.25 * adr_pct, 10.0))
    stop_alert = round(buy_limit * (1.0 - stop_dist_pct / 100.0), 2)
    net_risk_eur = int(round(order_eur * (stop_dist_pct / 100.0) + fee_eur))

    net_rr = round(max(0.0, float(net_gain_eur)) / max(1.0, float(net_risk_eur)), 2)
    hold_days = round(gross_gain_pct / max(0.5, adr_pct), 1)

    base_p = 58 if q_tier == "Q1" else (52 if q_tier == "Q2" else 44)
    oversold_lim = 33.0 if cfg.get("tier") == "CORE" else 29.0
    if rsi_r <= oversold_lim:
        base_p += 6
    elif rsi_r <= 40.0:
        base_p += 3
    if val_zone == "[CHEAP]":
        base_p += 4
    elif val_zone == "[HOT]":
        base_p -= 6
    if hold_days <= 3.5:
        base_p += 3
    elif hold_days > 6.5:
        base_p -= 4
    if rate_regime == "RATE_SHOCK" or is_cash_burner:
        base_p -= 8
    base_p = max(30, min(72, base_p))
    net_ev_eur = int(round((base_p / 100.0) * net_gain_eur - ((100 - base_p) / 100.0) * net_risk_eur))

    horiz_tag = "Q1:H1-3" if q_tier == "Q1" else ("Q2:H1-2" if q_tier == "Q2" else "Q3:H1")
    buy_short = "Flush" if buy_tag == "Flush-Trap" else ("0%" if buy_tag == "0%-Puskuri" else buy_tag)
    return {
        "Ticker": row["Ticker"],
        "Q_Horiz": horiz_tag,
        "Peer_Cls": row.get("_peer_cls_str", "-"),
        "Data_Density": row.get("_data_density", "HIGH"),
        "Buy_Limit_Str": f"{buy_limit}({buy_short}/St:{stop_alert})",
        "Sell_Limit_Str": f"{sell_limit}(-{round(sell_buf_pct*100,1)}%)",
        "Lot_Str": f"{shares}kpl/{int(round(order_eur))}e",
        "Fee_Str": f"{fee_eur:.0f}e({fee_pct:.1f}%)",
        "PnL_Risk_Str": f"{net_gain_eur:+d}/-{net_risk_eur}e",
        "RR_Days_Str": f"{net_rr}({hold_days}d)",
        "EV_Str": f"{base_p}%/{net_ev_eur:+d}e",
        "_is_candidate": (row["Signaali"] != "OK") or (float(row.get("_dist_sup_pct", 99.0)) <= 1.8 * adr_pct)
    }

def is_clean_headline(title):
    if not title or len(str(title).strip()) < 15:
        return False
    t_low = str(title).lower()
    return not any(bad in t_low for bad in NOISE_PHRASES)

def clean_and_cap_title(title, max_chars=300):
    clean = " ".join(str(title or "").split())
    if len(clean) <= max_chars:
        return clean
    clipped = clean[: max_chars - 3]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(".,;:- ") + "..."

def extract_news_meta(item, now_dt):
    """Palauttaa (pub_ts, age_h) vain jos uutisella on todennettu aikaleima. Aikaleimattomat hylätään (None)."""
    if not isinstance(item, dict):
        return None
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    pub_ts = item.get("providerPublishTime") or content.get("providerPublishTime")
    if pub_ts is not None:
        try:
            ts_val = float(pub_ts)
            if ts_val > 1e12:
                ts_val /= 1000.0
            age_h = (now_dt.timestamp() - ts_val) / 3600.0
            if age_h >= -2.0:
                return ts_val, age_h
        except Exception:
            pass
    pub_str = (
        content.get("pubDate")
        or content.get("displayTime")
        or item.get("pubDate")
        or item.get("publishTime")
    )
    if pub_str:
        try:
            pub_dt = datetime.fromisoformat(str(pub_str).strip().replace("Z", "+00:00"))
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            ts_val = pub_dt.timestamp()
            age_h = (now_dt.timestamp() - ts_val) / 3600.0
            if age_h >= -2.0:
                return ts_val, age_h
        except Exception:
            pass
    return None

def format_news_timestamp(pub_ts, now_dt, tz_fi, max_fresh_hours=None):
    pub_dt_fi = datetime.fromtimestamp(float(pub_ts), tz=tz_fi)
    age_h = max(0.0, (now_dt.timestamp() - float(pub_ts)) / 3600.0)
    dt_str = pub_dt_fi.strftime("%d.%m. %H:%M EET")
    if max_fresh_hours is not None and age_h > max_fresh_hours:
        days = max(1, int(round(age_h / 24.0)))
        age_str = f"{days}pv ARKISTO"
    elif age_h < 1.0:
        mins = max(1, int(round(age_h * 60.0)))
        age_str = f"{mins}min"
    elif age_h < 48.0:
        age_str = f"{int(round(age_h))}h"
    else:
        days = max(2, int(round(age_h / 24.0)))
        age_str = f"{int(round(age_h))}h / {days}pv"
    return f"[{dt_str} | {age_str}]", age_h

NEWS_CACHE_PATH = os.path.join(tempfile.gettempdir(), "st0_last_verified_news.json")

@st.cache_resource
def get_in_memory_news_store():
    return {}

def load_verified_news_cache():
    mem_store = get_in_memory_news_store()
    disk_store = {}
    try:
        if os.path.exists(NEWS_CACHE_PATH):
            with open(NEWS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    disk_store = data
    except Exception:
        pass
    merged = dict(disk_store)
    for sym, entry in mem_store.items():
        if isinstance(entry, dict) and float(entry.get("pub_ts", 0)) >= float(merged.get(sym, {}).get("pub_ts", 0)):
            merged[sym] = entry
    mem_store.update(merged)
    return merged

def save_verified_news_cache(cache_dict):
    try:
        mem_store = get_in_memory_news_store()
        mem_store.update(cache_dict)
    except Exception:
        pass
    try:
        with open(NEWS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_dict, f, ensure_ascii=False)
    except Exception:
        pass

@st.cache_data(ttl=120)
def fetch_all_market_data():
    tz_fi = pytz.timezone("Europe/Helsinki")
    tz_ny = pytz.timezone("America/New_York")
    now_dt = datetime.now(tz_fi)
    now_ny = now_dt.astimezone(tz_ny)
    now_str = now_dt.strftime("%d.%m.%Y klo %H:%M:%S EET")
    is_us_pre_window_fi = (now_dt.weekday() < 5 and 10 <= now_dt.hour < 17)

    macro_info = {}
    macro_objs = {}
    qqq_chg_1d, qqq_chg_20d = 0.0, 0.0
    spy_chg_1d, spy_chg_20d = 0.0, 0.0
    smh_chg_1d = 0.0
    seen_titles = set()
    macro_news = []
    sector_news = []

    # 1. MAKRODATA + VXN + US10Y (1D & 20D BPS) + SEMI-SPREAD
    for name, yf_sym in MACRO_TICKERS.items():
        try:
            t = yf.Ticker(yf_sym)
            macro_objs[name] = t
            hist = t.history(period="3mo")
            if len(hist) >= 2:
                last_p = float(hist["Close"].iloc[-1])
                prev_p = float(hist["Close"].iloc[-2])
                try:
                    fast_m = t.info
                    curr_m = fast_m.get("regularMarketPrice") or fast_m.get("currentPrice")
                    prev_m = fast_m.get("regularMarketPreviousClose")
                    if curr_m and float(curr_m) > 0:
                        last_p = float(curr_m)
                    if prev_m and float(prev_m) > 0:
                        prev_p = float(prev_m)
                except Exception:
                    pass
                chg_1d = ((last_p / prev_p) - 1) * 100
                p_20d = float(hist["Close"].iloc[-21]) if len(hist) >= 21 else prev_p
                chg_20d = ((last_p / p_20d) - 1) * 100
                bps_1d = int(round((last_p - prev_p) * 100)) if name == "US10Y" else 0
                bps_20d = int(round((last_p - p_20d) * 100)) if name == "US10Y" else 0
                decimals = 3 if name == "EURUSD" else 2
                macro_info[name] = {
                    "price": round(last_p, decimals),
                    "chg_pct": round(chg_1d, 2),
                    "chg_20d": round(chg_20d, 1),
                    "bps_1d": bps_1d,
                    "bps_20d": bps_20d
                }
                if name == "QQQ":
                    qqq_chg_1d, qqq_chg_20d = chg_1d, chg_20d
                elif name == "SPY":
                    spy_chg_1d, spy_chg_20d = chg_1d, chg_20d
                elif name == "SMH":
                    smh_chg_1d = chg_1d
            else:
                macro_info[name] = {"price": 0.0, "chg_pct": 0.0, "chg_20d": 0.0, "bps_1d": 0, "bps_20d": 0}
        except Exception:
            macro_info[name] = {"price": 0.0, "chg_pct": 0.0, "chg_20d": 0.0, "bps_1d": 0, "bps_20d": 0}

    rate_regime = classify_rate_regime(macro_info.get("US10Y", {}))
    semi_spread = round(smh_chg_1d - spy_chg_1d, 2)
    macro_info["META_REGIME"] = {"rate_regime": rate_regime, "semi_spread": semi_spread}

    # TUOREET MAKRO- & SEKTORIUUTISET (96h ikäraja, vain todennetut aikaleimat, uusimmat ensin)
    macro_candidates = []
    for name in MACRO_NEWS_PRIORITY:
        if len(macro_candidates) >= 3:
            break
        t_obj = macro_objs.get(name)
        if not t_obj:
            continue
        try:
            raw_m_news = t_obj.news or []
            src_dated = []
            for item in raw_m_news[:8]:
                title = clean_and_cap_title(item.get("title") or (item.get("content") or {}).get("title", ""), 300)
                if not is_clean_headline(title) or title in seen_titles:
                    continue
                meta = extract_news_meta(item, now_dt)
                if meta is not None and meta[1] <= 96.0:
                    src_dated.append((meta[0], meta[1], title))
            src_dated.sort(key=lambda x: x[1])
            for pub_ts, age_h, title in src_dated[:2]:
                if len(macro_candidates) >= 3 or title in seen_titles:
                    break
                seen_titles.add(title)
                ts_tag, _ = format_news_timestamp(pub_ts, now_dt, tz_fi, max_fresh_hours=96.0)
                macro_candidates.append((age_h, f"- MAKRO ({name}) {ts_tag}: {title}"))
        except Exception:
            pass
    macro_candidates.sort(key=lambda x: x[0])
    macro_news = [entry[1] for entry in macro_candidates]

    sector_candidates = []
    for name in SECTOR_NEWS_PRIORITY:
        if len(sector_candidates) >= 3:
            break
        t_obj = macro_objs.get(name)
        if not t_obj:
            continue
        try:
            raw_s_news = t_obj.news or []
            src_dated = []
            for item in raw_s_news[:8]:
                title = clean_and_cap_title(item.get("title") or (item.get("content") or {}).get("title", ""), 300)
                if not is_clean_headline(title) or title in seen_titles:
                    continue
                meta = extract_news_meta(item, now_dt)
                if meta is not None and meta[1] <= 96.0:
                    src_dated.append((meta[0], meta[1], title))
            src_dated.sort(key=lambda x: x[1])
            for pub_ts, age_h, title in src_dated[:2]:
                if len(sector_candidates) >= 3 or title in seen_titles:
                    break
                seen_titles.add(title)
                ts_tag, _ = format_news_timestamp(pub_ts, now_dt, tz_fi, max_fresh_hours=96.0)
                sector_candidates.append((age_h, f"- SEKTORI ({name}) {ts_tag}: {title}"))
        except Exception:
            pass
    sector_candidates.sort(key=lambda x: x[0])
    sector_news = [entry[1] for entry in sector_candidates]

    # 2. YHTIÖDATA + TASELUOKITUS + KORJATTU F:P/E + U-CURVE pRVOL
    rows = []
    company_news_candidates = []
    verified_news_cache = load_verified_news_cache()

    for sym, cfg in TICKERS.items():
        try:
            t = None
            hist = pd.DataFrame()
            used_yf = cfg["yf"][0]
            for candidate in cfg["yf"]:
                temp_t = yf.Ticker(candidate)
                temp_h = temp_t.history(period="1y")
                if not temp_h.empty and len(temp_h) >= 20:
                    t = temp_t
                    hist = temp_h
                    used_yf = candidate
                    break
            if hist.empty:
                continue

            close_s = hist["Close"].copy()
            vol_s = hist["Volume"]
            last_close = float(close_s.iloc[-1])
            prev_close = float(close_s.iloc[-2]) if len(close_s) >= 2 else last_close
            day_high = float(hist["High"].iloc[-1])
            day_low = float(hist["Low"].iloc[-1])
            high_52w = float(hist["High"].max())
            low_52w = float(hist["Low"].min())
            high_60d = float(hist["High"].tail(60).max())
            low_60d = float(hist["Low"].tail(60).min())
            last_bar_date = hist.index[-1].date()
            exch_today = now_dt.date() if ".HE" in used_yf else now_ny.date()

            avg_vol_20 = float(vol_s.tail(21).iloc[:-1].mean()) if len(vol_s) >= 21 else float(vol_s.mean())
            last_vol = float(vol_s.iloc[-1])
            has_today_vol = (last_bar_date == exch_today)

            live_price = last_close
            market_session = "LIVE" if sym == "BTC-USD" else "CLS"
            bs_tier = cfg.get("bs", "SELF")
            q_tier = cfg.get("q_tier", "Q2")
            val_str = "-"
            val_zone_tag = ""
            quality_human_str = "- / - / -"
            quality_ai_str = f"-/-/-/{bs_tier}:{q_tier}"
            bs_human_str = f"{BS_HUMAN_LABELS.get(bs_tier, bs_tier)} [{q_tier}]"
            next_q_str = "-"
            earnings_soon = False
            op_m_val = None
            rev_g_val = None
            fcf_yield_val = None

            try:
                fast = t.info
                m_state = str(fast.get("marketState", "")).upper()
                pre_p = fast.get("preMarketPrice")
                post_p = fast.get("postMarketPrice")
                curr_p = fast.get("currentPrice") or fast.get("regularMarketPrice")
                reg_prev = fast.get("regularMarketPreviousClose") or prev_close
                info_vol = fast.get("regularMarketVolume") or fast.get("volume")

                info_low = fast.get("dayLow") or fast.get("regularMarketDayLow")
                info_high = fast.get("dayHigh") or fast.get("regularMarketDayHigh")
                if info_low and float(info_low) > 0:
                    day_low = float(info_low)
                if info_high and float(info_high) > 0:
                    day_high = float(info_high)

                is_pre_session = (
                    ".HE" not in used_yf
                    and pre_p and float(pre_p) > 0
                    and (m_state in ("PRE", "PREPRE") or (is_us_pre_window_fi and m_state != "REGULAR"))
                )

                if sym == "BTC-USD":
                    if curr_p and float(curr_p) > 0:
                        live_price = float(curr_p)
                        prev_close = float(reg_prev)
                    market_session = "LIVE"
                elif m_state == "REGULAR":
                    if curr_p and float(curr_p) > 0:
                        live_price = float(curr_p)
                        prev_close = float(reg_prev)
                    market_session = "LIVE"
                    if info_vol and float(info_vol) > 0:
                        last_vol = max(last_vol, float(info_vol)) if has_today_vol else float(info_vol)
                        has_today_vol = True
                elif is_pre_session:
                    live_price = float(pre_p)
                    prev_close = float(curr_p or last_close)
                    market_session = "PRE"
                elif (
                    ".HE" not in used_yf
                    and post_p and float(post_p) > 0
                    and abs(float(post_p) - float(curr_p or last_close)) / float(curr_p or last_close) > 0.0005
                ):
                    live_price = float(post_p)
                    prev_close = float(reg_prev)
                    market_session = "AH"
                elif curr_p and float(curr_p) > 0:
                    live_price = float(curr_p)
                    prev_close = float(reg_prev)
                    market_session = "CLS"

                day_low = min(day_low, live_price)
                day_high = max(day_high, live_price)

                # 1. ZERO-ILLUSION ARVOSTUSSUODATIN v3.5 (Säilyttää AVGO:n aidon F:12-18x kertoimen!)
                t_pe = fast.get("trailingPE")
                f_pe = fast.get("forwardPE")
                ev_ebitda = fast.get("enterpriseToEbitda")
                pb = fast.get("priceToBook")
                op_m = fast.get("operatingMargins")
                rev_g = fast.get("revenueGrowth")
                curr_code = fast.get("currency", "USD")
                fin_curr = fast.get("financialCurrency", curr_code)

                if op_m is not None and -5.0 < float(op_m) < 1.0:
                    op_m_val = float(op_m)
                if rev_g is not None and -1.0 < float(rev_g) < 20.0:
                    rev_g_val = float(rev_g)

                same_currency = (curr_code == fin_curr)
                valid_ev = (ev_ebitda is not None and 2.0 < float(ev_ebitda) < 150.0 and same_currency)
                valid_pb = (pb is not None and 0.2 < float(pb) < 35.0 and same_currency)
                positive_opm = (op_m is None or float(op_m) > 0.01)
                high_growth_quality = (
                    op_m is not None and float(op_m) >= 0.20
                    and rev_g is not None and float(rev_g) >= 0.25
                )

                parts = []
                f_pe_valid = False
                if f_pe and 4.5 < float(f_pe) < 200.0 and positive_opm:
                    f_val = float(f_pe)
                    if not high_growth_quality and t_pe and float(t_pe) > 0 and f_val < float(t_pe) * 0.50 and f_val < 18.0:
                        f_pe_valid = False
                    elif not high_growth_quality and valid_ev and f_val < float(ev_ebitda) * 0.85 and f_val < 18.0:
                        f_pe_valid = False
                    elif high_growth_quality and f_val < 14.0:
                        f_pe_valid = False
                    else:
                        f_pe_valid = True

                val_zone_tag = classify_dna_valuation_zone(
                    cfg, f_pe_valid, f_pe, t_pe, valid_pb, pb, high_growth_quality
                )

                if f_pe_valid:
                    parts.append(f"F:{round(float(f_pe),1)}x")
                if t_pe and 2.0 < float(t_pe) < 250.0 and (not f_pe_valid or not valid_ev):
                    parts.append(f"T:{round(float(t_pe),1)}x")

                if valid_ev:
                    parts.append(f"EV:{round(float(ev_ebitda),1)}x")
                elif valid_pb and len(parts) < 2:
                    parts.append(f"PB:{round(float(pb),1)}x")

                if parts:
                    if val_zone_tag:
                        parts[0] = f"{parts[0]}{val_zone_tag}"
                    val_str = "/".join(parts[:2])

                # 2. LAATU-, KASSAVIRTA- & NETTOKASSAMITTARIT (AI vs. Human eriytetty)
                fcf = fast.get("freeCashflow")
                mcap = fast.get("marketCap")
                t_cash = fast.get("totalCash")
                t_debt = fast.get("totalDebt")

                rev_s = f"{round(float(rev_g) * 100, 1)}%" if rev_g is not None else "-"
                opm_s = f"{round(float(op_m) * 100, 1)}%" if (op_m is not None and -2.0 < float(op_m) < 1.0) else "-"
                fcf_s = "-"
                if fcf is not None and mcap and float(mcap) > 0 and same_currency:
                    fcf_yield = (float(fcf) / float(mcap)) * 100.0
                    if -60.0 < fcf_yield < 50.0:
                        fcf_yield_val = fcf_yield
                        fcf_s = f"{round(fcf_yield, 1)}%"

                nc_tag_ai = f"{bs_tier}:{q_tier}"
                nc_tag_human = f"{BS_HUMAN_LABELS.get(bs_tier, bs_tier)} [{q_tier}]"
                if (t_cash is not None or t_debt is not None) and mcap and float(mcap) > 0 and same_currency:
                    net_c_pct = ((float(t_cash or 0.0) - float(t_debt or 0.0)) / float(mcap)) * 100.0
                    if -150.0 < net_c_pct < 100.0:
                        nc_int = int(round(net_c_pct))
                        nc_tag_ai = f"{bs_tier}:{q_tier}({nc_int:+d}%)"
                        nc_tag_human = f"{BS_HUMAN_LABELS.get(bs_tier, bs_tier)} [{q_tier}] ({nc_int:+d}%)"

                quality_ai_str = f"{rev_s}/{opm_s}/{fcf_s}/{nc_tag_ai}"
                quality_human_str = f"{rev_s} / {opm_s} / {fcf_s}"
                bs_human_str = nc_tag_human

                # 3. TULOSKALENTERI
                e_ts = fast.get("earningsTimestamp") or fast.get("earningsTimestampStart")
                if e_ts:
                    e_dt = datetime.fromtimestamp(int(e_ts), tz=tz_fi)
                    days_diff = (e_dt.date() - now_dt.date()).days
                    date_fmt = e_dt.strftime("%d.%m")
                    if 0 <= days_diff <= 7:
                        next_q_str = f"Q!{date_fmt}({days_diff}d)"
                        earnings_soon = True
                    elif days_diff > 7:
                        next_q_str = f"Q:{date_fmt}({days_diff}d)"
                    else:
                        next_q_str = f"OK:{date_fmt}"
            except Exception:
                pass

            prvol = calc_pace_rvol(
                last_vol, avg_vol_20, market_session, used_yf, sym, now_dt, now_ny, has_today_vol
            )

            # LIVE/PRE-HINNAN SYÖTTÖ TEKNISIIN INDIKAATTOREIHIN
            if market_session == "PRE" and last_bar_date < exch_today:
                close_ta = pd.concat([close_s, pd.Series([live_price])], ignore_index=True)
            else:
                close_ta = close_s.copy()
                close_ta.iloc[-1] = live_price

            chg_1d = ((live_price / prev_close) - 1) * 100
            chg_20d = ((live_price / float(close_s.iloc[-21])) - 1) * 100 if len(close_s) >= 21 else chg_1d
            dd_52w_pct = ((live_price / high_52w) - 1) * 100
            rsi_val = float(calc_wilder_rsi(close_ta).iloc[-1]) if len(close_ta) >= 15 else 50.0
            rsi_r = round(rsi_val, 1)

            sma20 = float(close_ta.rolling(20).mean().iloc[-1])
            std20 = float(close_ta.rolling(20).std().iloc[-1])
            lower_bb = max(0.01, sma20 - 2.0 * std20)
            upper_bb = sma20 + 2.0 * std20

            sma50 = float(close_ta.rolling(50).mean().iloc[-1]) if len(close_ta) >= 50 else live_price
            sma100 = float(close_ta.rolling(100).mean().iloc[-1]) if len(close_ta) >= 100 else live_price
            sma200 = float(close_ta.rolling(200).mean().iloc[-1]) if len(close_ta) >= 200 else live_price

            dist_sma50 = ((live_price / sma50) - 1) * 100
            dist_sma200 = ((live_price / sma200) - 1) * 100

            # ADR% SUOJAUS
            rng_series = (hist["High"] - hist["Low"]) / hist["Low"] * 100.0
            is_intraday_live = (market_session == "LIVE" and sym != "BTC-USD" and last_bar_date == exch_today)
            if is_intraday_live and len(rng_series) > 15 and day_low > 0:
                prev_adr = float(rng_series.iloc[:-1].tail(14).mean())
                today_rng = (day_high - day_low) / day_low * 100.0
                if today_rng >= prev_adr:
                    mod_rng = rng_series.tail(14).copy()
                    mod_rng.iloc[-1] = today_rng
                    adr_pct = float(mod_rng.mean())
                else:
                    adr_pct = prev_adr
            else:
                adr_pct = float(rng_series.tail(14).mean())

            bench_1d = spy_chg_1d if ".HE" in used_yf else qqq_chg_1d
            bench_20d = spy_chg_20d if ".HE" in used_yf else qqq_chg_20d
            rs_1d = round(chg_1d - bench_1d, 2)
            rs_20d = round(chg_20d - bench_20d, 1)

            # EHDOTON TUKITASOLUKKO (Dyn Tuki <= nykyhinta)
            candidates = [
                ("SMA50", sma50),
                ("SMA100", sma100),
                ("SMA200", sma200),
                ("BB-Low", lower_bb),
                ("60d-Low", low_60d),
                ("52w-Low", low_52w)
            ]
            strictly_below = [(name, val) for name, val in candidates if val <= live_price * 0.999]
            if strictly_below:
                support_type, dyn_support_raw = max(strictly_below, key=lambda x: x[1])
                dyn_support = round(dyn_support_raw, 2)
            else:
                dyn_support = round(live_price * (1.0 - (adr_pct / 100.0)), 2)
                support_type = "ADR-Floor"

            # SWING DYN TRIM
            res_candidates = [
                ("SMA50", sma50),
                ("SMA100", sma100),
                ("SMA200", sma200),
                ("BB-High", upper_bb),
                ("60d-High", high_60d),
                ("52w-High", high_52w)
            ]
            min_swing_dist = max(0.03, 0.85 * adr_pct / 100.0)
            above_resistances = [(name, val) for name, val in res_candidates if val >= live_price * (1.0 + min_swing_dist)]
            if above_resistances:
                trim_type, dyn_trim_raw = min(above_resistances, key=lambda x: x[1])
                max_swing_cap = live_price * (1.0 + max(0.22, 4.5 * adr_pct / 100.0))
                if dyn_trim_raw > max_swing_cap:
                    dyn_trim = round(live_price * (1.0 + max(0.10, 2.5 * adr_pct / 100.0)), 2)
                    trim_type = "2.5xADR"
                else:
                    dyn_trim = round(dyn_trim_raw, 2)
            else:
                dyn_trim = round(live_price * (1.0 + (2.0 * adr_pct / 100.0)), 2)
                trim_type = "2.0xADR"

            near_walls = [(name, val) for name, val in res_candidates if live_price * 1.003 <= val <= live_price * 1.022]
            near_wall_hit = min(near_walls, key=lambda x: x[1]) if near_walls else None

            # APEX v7.0.2 SIGNAALIMOOTTORI (2D Korkomatriisi + Tappiollisten DEBT-yhtiöiden suodatus)
            tier = cfg.get("tier", "CORE")
            oversold_lim = 33.0 if tier == "CORE" else (30.0 if tier == "BTC" else 29.0)
            overbought_lim = 68.0 if tier == "CYC" else 72.0
            move_lim = max(3.8, min(1.5 * adr_pct, 5.0))
            dist_to_support_pct = ((live_price / dyn_support) - 1) * 100

            is_cash_burner_debt = (
                bs_tier == "DEBT"
                and sym != "BTC-USD"
                and ((op_m_val is not None and op_m_val < 0.0) or (fcf_yield_val is not None and fcf_yield_val < -4.0))
            )
            buffer_muted = (rate_regime == "RATE_SHOCK") or (rate_regime == "RATE_ELEVATED" and bs_tier == "DEBT")
            sup_touch_lim = max(0.8, min(0.25 * adr_pct, 1.4)) if buffer_muted else max(1.5, min(0.5 * adr_pct, 2.8))

            status_flag = "OK"
            if earnings_soon and rsi_r <= 27.0 and tier == "CORE":
                if dist_to_support_pct <= max(2.2, 0.55 * adr_pct):
                    status_flag = f"BUY: Q!-DISLOCATION (RSI {rsi_r})"
                else:
                    status_flag = f"WATCH: Q!-RSI {rsi_r} (ODOTA TUKEA)"
            elif rsi_r <= oversold_lim:
                prefix = "WATCH: ALATUKI" if is_cash_burner_debt else "BUY: YLIMYYTY"
                status_flag = f"{prefix} (RSI {rsi_r})"
            elif 0.0 <= dist_to_support_pct <= sup_touch_lim and rsi_r <= 46.0:
                prefix = "WATCH: TESTAA" if is_cash_burner_debt else "BUY: TESTAA"
                status_flag = f"{prefix} {support_type}"
            elif rsi_r >= overbought_lim:
                status_flag = f"TRIM: YLIOSTETTU (RSI {rsi_r})"
            elif tier in ("CYC", "BETA") and near_wall_hit is not None and chg_1d >= 1.5 and rsi_r >= 58.0:
                status_flag = f"TRIM: VASTUS {near_wall_hit[0]}"
            elif abs(chg_1d) >= move_lim:
                vol_tag = f" pRVOL:{prvol}x" if prvol >= 1.3 else ""
                status_flag = f"MOVE: {round(chg_1d,1)}%{vol_tag}"
            elif rs_1d >= 3.0 and chg_1d > 0:
                status_flag = f"RS-LEAD (+{round(rs_1d,1)}%)"

            if earnings_soon and "Q!" not in status_flag:
                status_flag = f"WARN: TULOS {next_q_str}" if status_flag == "OK" else f"{status_flag} + {next_q_str}"

            day_range_str = f"{round(day_low, 2)}-{round(day_high, 2)}"
            ticker_disp = sym if used_yf == sym or ".HE" in used_yf else f"{sym}({used_yf})"
            has_fresh_24h_news = False
            newest_news_age_h = 999.0

            try:
                raw_news = t.news or []
                keywords = cfg.get("kw", [sym.lower()])
                max_news_age_h = 336.0 if ".HE" in used_yf else 168.0
                dated_matches = []
                for item in raw_news[:10]:
                    raw_title = item.get("title") or (item.get("content") or {}).get("title", "")
                    title = clean_and_cap_title(raw_title, 300)
                    if not is_clean_headline(title) or title in seen_titles:
                        continue
                    t_low = title.lower()
                    if not any(k in t_low for k in keywords):
                        continue
                    meta = extract_news_meta(item, now_dt)
                    if meta is not None:
                        dated_matches.append((meta[0], title))

                cached_item = verified_news_cache.get(sym)
                if isinstance(cached_item, dict) and cached_item.get("title") and cached_item.get("pub_ts"):
                    c_title = clean_and_cap_title(cached_item.get("title"), 300)
                    c_ts = float(cached_item.get("pub_ts"))
                    if is_clean_headline(c_title) and c_title not in seen_titles:
                        dated_matches.append((c_ts, c_title))

                if dated_matches:
                    # Uusin todennettu aikaleimallinen uutinen voittaa aina; edellistä ei ylikirjoiteta aikaleimattomalla
                    dated_matches.sort(key=lambda x: x[0], reverse=True)
                    best_ts, best_title = dated_matches[0]
                    seen_titles.add(best_title)
                    verified_news_cache[sym] = {"title": best_title, "pub_ts": best_ts}
                    ts_tag, age_h = format_news_timestamp(best_ts, now_dt, tz_fi, max_fresh_hours=max_news_age_h)
                    newest_news_age_h = age_h
                    fresh_lim = 48.0 if ".HE" in used_yf else 24.0
                    has_fresh_24h_news = (age_h <= fresh_lim)
                    company_news_candidates.append((age_h, f"- **{sym}** {ts_tag}: {best_title}"))
                    # Jos kohteessa on aktiivinen signaali ja 2. tuore uutinen (<36h), lisätään sekin Doc 2 -uutissyötteeseen
                    if status_flag != "OK" and len(dated_matches) >= 2:
                        ts2, title2 = dated_matches[1]
                        if title2 not in seen_titles:
                            ts_tag2, age_h2 = format_news_timestamp(ts2, now_dt, tz_fi, max_fresh_hours=max_news_age_h)
                            if age_h2 <= 36.0:
                                seen_titles.add(title2)
                                company_news_candidates.append((age_h2, f"- **{sym}** (2) {ts_tag2}: {title2}"))
            except Exception:
                pass

            rows.append({
                "Ticker": ticker_disp,
                "_sym": sym,
                "Kori": cfg["bucket"],
                "Hinta": round(live_price, 2),
                "Sessio": market_session,
                "Muutos %": round(chg_1d, 2),
                "Day Low-High": day_range_str,
                "pRVOL_num": prvol,
                "pRVOL": f"{prvol}x",
                "52w %": round(dd_52w_pct, 1),
                "Arvostus": val_str,
                "Rev/OpM/FCF/Tase": quality_ai_str,
                "Kasvu / Marg / FCF": quality_human_str,
                "Taseprofiili": bs_human_str,
                "RSI(14)": rsi_r,
                "SMA50%": round(dist_sma50, 1),
                "SMA200%": round(dist_sma200, 1),
                "ADR%": round(adr_pct, 1),
                "RS(1d/20d)": f"{rs_1d}%/{rs_20d}%",
                "Dyn Tuki": f"{dyn_support}({support_type})",
                "Dyn Trim": f"{dyn_trim}({trim_type})",
                "Q-Tila": next_q_str,
                "Signaali": status_flag,
                "_dyn_sup_val": dyn_support,
                "_dyn_trim_val": dyn_trim,
                "_val_zone": val_zone_tag,
                "_is_cash_burner": is_cash_burner_debt,
                "_dist_sup_pct": round(dist_to_support_pct, 2),
                "_op_m_val": op_m_val,
                "_rev_g_val": rev_g_val,
                "_has_fresh_24h_news": has_fresh_24h_news,
                "_newest_news_age_h": round(newest_news_age_h, 1),
                "_move_lim": move_lim
            })

        except Exception:
            continue

    save_verified_news_cache(verified_news_cache)
    company_news_candidates.sort(key=lambda x: x[0])
    company_news = [entry[1] for entry in company_news_candidates]

    # 3. ALGORITMIT A, C & D: VERROKKIEROTIN ([SPOT-2]), DATA-TIHEYS & KAUPPALASKURI ([SPOT-4])
    chg_map = {r["_sym"]: float(r["Muutos %"]) for r in rows}
    quant_rows = []
    fresh_news_cnt = sum(1 for r in rows if r.get("_has_fresh_24h_news"))
    hyper_opms = [float(r["_op_m_val"]) * 100.0 for r in rows if r["_sym"] in ("GOOG", "AMZN", "META") and r.get("_op_m_val") is not None]
    tsm_rev = next((float(r["_rev_g_val"]) * 100.0 for r in rows if r["_sym"] == "TSM" and r.get("_rev_g_val") is not None), None)

    for r in rows:
        sym = r["_sym"]
        cfg = TICKERS.get(sym, {})
        peers = cfg.get("peers", [])
        peer_chgs = [chg_map[p] for p in peers if p in chg_map]
        peer_avg = sum(peer_chgs) / len(peer_chgs) if peer_chgs else 0.0
        peer_spread = round(float(r["Muutos %"]) - peer_avg, 1)
        peer_lbl = "/".join(peers[:2]) if peers else "IDX"

        has_fresh = bool(r.get("_has_fresh_24h_news", False))
        chg_v = float(r["Muutos %"])
        bs_t = cfg.get("bs", "SELF")
        is_cb = bool(r.get("_is_cash_burner", False))

        if is_cb and chg_v <= -3.0:
            cls_tag = "C:RISK"
        elif chg_v <= -2.0 and peer_spread <= -1.5 and bs_t in ("FORT", "SELF"):
            cls_tag = "B:DISL"
        elif chg_v <= -2.0:
            cls_tag = "A:SYMP"
        elif chg_v >= 2.5:
            cls_tag = "LEAD"
        else:
            cls_tag = "NEUT"

        if has_fresh or ( abs(chg_v) < float(r.get("_move_lim", 3.8)) and abs(peer_spread) < 2.0 ):
            data_d = "HIGH"
        else:
            data_d = "LOW!"

        if abs(chg_v) >= float(r.get("_move_lim", 3.8)) and not has_fresh:
            if "[DATA:LOW]" not in r["Signaali"]:
                r["Signaali"] = f"{r['Signaali']} [DATA:LOW]"

        r["_peer_cls_str"] = f"{peer_lbl}{peer_spread:+.1f}p({cls_tag})"
        r["_data_density"] = data_d

        q_res = compute_nordnet_trade_quant(r, cfg, macro_info)
        if q_res is not None:
            quant_rows.append(q_res)

    macro_info["META_REGIME"]["clock_status"] = compute_nordnet_clock_status(now_dt)
    macro_info["META_REGIME"]["fresh_news_cnt"] = fresh_news_cnt
    macro_info["META_REGIME"]["hyper_opm_avg"] = round(sum(hyper_opms) / len(hyper_opms), 1) if hyper_opms else 28.0
    macro_info["META_REGIME"]["tsm_rev_pct"] = round(tsm_rev, 1) if tsm_rev is not None else 50.0
    macro_info["QUANT_ROWS"] = quant_rows

    df = pd.DataFrame(rows)
    return now_str, macro_info, df, macro_news, sector_news, company_news

# ==========================================
# MOOTTORI 1: 100 % AI-OPTIMOITU MARKDOWN GOOGLE DRIVEEN (TIIVIS, NOLLA EMOJIA)
# ==========================================
def format_ai_md_table(sub_df):
    if sub_df.empty:
        return "Ei kohteita.\n"
    header = "|Ticker|Kori|Hinta|Ses|Muutos|Low-High|pRVOL|52w%|Arvostus|Rev/OpM/FCF/Tase|RSI|SMA50|SMA200|ADR|RS(1d/20d)|Dyn Tuki|Dyn Trim|Q-Tila|Signaali|\n"
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = ""
    for _, r in sub_df.iterrows():
        body += (
            f"|{r['Ticker']}|{r['Kori']}|{r['Hinta']}|{r['Sessio']}|{r['Muutos %']}%|{r['Day Low-High']}|{r['pRVOL']}|"
            f"{r['52w %']}%|{r['Arvostus']}|{r['Rev/OpM/FCF/Tase']}|{r['RSI(14)']}|{r['SMA50%']}%|"
            f"{r['SMA200%']}%|{r['ADR%']}%|{r['RS(1d/20d)']}|{r['Dyn Tuki']}|{r['Dyn Trim']}|{r['Q-Tila']}|{r['Signaali']}|\n"
        )
    return header + sep + body

def format_quant_md_table(quant_rows):
    candidates = [q for q in (quant_rows or []) if q.get("_is_candidate")]
    if not candidates:
        candidates = (quant_rows or [])[:6]
    candidates = candidates[:10]
    if not candidates:
        return "Ei aktiivisia kauppalaskelmaehdokkaita.\n"
    header = "|Ticker|Q|Verrokki&Luokka|Data|Osto(Pusk/Stop)|Myynti(-Pusk)|Era(Kpl/EUR)|Kulu|Voitto/Riski|R:R(pv)|P_hit/EV|\n"
    sep = "|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = ""
    for q in candidates:
        body += (
            f"|{q['Ticker']}|{q['Q_Horiz']}|{q['Peer_Cls']}|{q['Data_Density']}|"
            f"{q['Buy_Limit_Str']}|{q['Sell_Limit_Str']}|{q['Lot_Str']}|{q['Fee_Str']}|"
            f"{q['PnL_Risk_Str']}|{q['RR_Days_Str']}|{q['EV_Str']}|\n"
        )
    return header + sep + body

def build_ai_dual_markdown_reports(now_str, macro_info, df, macro_news, sector_news, company_news):
    vix = macro_info.get("VIX", {})
    vxn = macro_info.get("VXN", {})
    us10y = macro_info.get("US10Y", {})
    nq_f = macro_info.get("NQ_FUT", {})
    es_f = macro_info.get("ES_FUT", {})
    qqq = macro_info.get("QQQ", {})
    smh = macro_info.get("SMH", {})
    spy = macro_info.get("SPY", {})
    fx = macro_info.get("EURUSD", {})
    meta_r = macro_info.get("META_REGIME", {})
    rate_reg = meta_r.get("rate_regime", "RATE_CALM")
    semi_sp = meta_r.get("semi_spread", 0.0)
    clock_str = meta_r.get("clock_status", "-")
    fresh_cnt = meta_r.get("fresh_news_cnt", 0)
    hyper_opm = meta_r.get("hyper_opm_avg", 28.0)
    tsm_rev = meta_r.get("tsm_rev_pct", 50.0)
    quant_rows = macro_info.get("QUANT_ROWS", [])

    vix_p = float(vix.get("price", 0.0))
    vxn_p = float(vxn.get("price", 0.0))
    smh_20d = float(smh.get("chg_20d", 0.0))
    qqq_20d = float(qqq.get("chg_20d", 0.0))

    if vix_p >= 30.0:
        regime_auto = "REGIME_3_BEAR"
    elif vix_p > 0 and vix_p < 20.0 and (vxn_p == 0 or vxn_p < 25.0) and smh_20d > 0 and qqq_20d > 0 and rate_reg == "RATE_CALM":
        regime_auto = "REGIME_1_BULL"
    else:
        regime_auto = "REGIME_2_CHOPPY_DISLOCATION"

    if tsm_rev >= 20.0 and hyper_opm >= 22.0:
        ai_cycle_auto = "EXPANSION" if (smh_20d >= 0 and rate_reg == "RATE_CALM") else "DIGESTION (FORT/SELF pelkodipit sallittu)"
    else:
        ai_cycle_auto = "ROLLOVER_CHECK (Tarkista CapEx & OpM)"

    if rate_reg == "RATE_SHOCK":
        rate_rule_auto = "RATE_SHOCK => Kytke +0.25x ADR etupuskuri POIS kaikilta; DEBT-ostot tauolla"
    elif rate_reg == "RATE_ELEVATED":
        rate_rule_auto = "RATE_ELEVATED => FORT & SELF: +0.25x ADR etupuskuri PÄÄLLÄ | DEBT: puskuri POIS ja vaadi Netto R:R >= 2.4"
    else:
        rate_rule_auto = "RATE_CALM => Normaali +0.25x ADR etupuskuri FORT/SELF-kohteille"

    vxn_str = f"{vxn_p:.2f} ({vxn.get('chg_pct', 0.0):+.2f}%)" if vxn_p > 0 else "N/A"
    active_df = df[df["Signaali"] != "OK"] if not df.empty else pd.DataFrame()
    inactive_df = df[df["Signaali"] == "OK"] if not df.empty else pd.DataFrame()
    loaded_cnt = len(df)
    total_cnt = len(TICKERS)

    # DOKUMENTTI 1: KVANTITIIVINEN MARKKINA-, TAULUKKO- JA NETTO-EV-SYÖTE (ST0_LIVE_MARKET_FEED)
    q_md = "# ST0_LIVE_MARKET_FEED — AI QUANT & TABLES (v3.6 DUAL-DOC — APEX v7.1.0)\n"
    q_md += f"AIKALEIMA: {now_str} (LIVE_USER_FEED: 0-3min | PARI: ST0_LIVE_NEWS_FEED)\n"
    q_md += (
        f"MAKRO, DISPERSIO & KORKOTILA: VIX: {vix_p:.2f} ({vix.get('chg_pct', 0.0):+.2f}%) | "
        f"VXN: {vxn_str} | Semi-Spread(SMH-SPY): {semi_sp:+.2f}pp | "
        f"US10Y: {us10y.get('price', 0.0):.2f}% (1d {us10y.get('bps_1d', 0):+d}bps / 20d {us10y.get('bps_20d', 0):+d}bps => {rate_reg}) | "
        f"NQ-Fut(24h): {nq_f.get('chg_pct', 0.0):+.2f}% | ES-Fut(24h): {es_f.get('chg_pct', 0.0):+.2f}% | "
        f"SMH: 1d {smh.get('chg_pct', 0.0):+.2f}% / 20d {smh_20d:+.1f}% | "
        f"QQQ: 1d {qqq.get('chg_pct', 0.0):+.2f}% / 20d {qqq_20d:+.1f}% | "
        f"SPY: 1d {spy.get('chg_pct', 0.0):+.2f}% / 20d {spy.get('chg_20d', 0.0):+.1f}% | EUR/USD: {fx.get('price', 0.0):.3f}\n"
    )
    q_md += "## 0. ESILASKETTU [SPOT-1] MAKRO-, REGIME-, KORKO- & AIKA-ANKKURI\n"
    q_md += f"- REGIME_AUTO: {regime_auto} | AI_CAPEX_AUTO: {ai_cycle_auto} (Hyperscaler OpM ka: {hyper_opm}% | TSM Rev: +{tsm_rev}%)\n"
    q_md += f"- 2D_KORKO_X_TASE_SAANTO: {rate_rule_auto}\n"
    q_md += f"- NORDNET_KELLO_JA_IKKUNA: {clock_str}\n"

    q_md += f"## 1. KOKO SALKKU & SEURANTALISTA ({total_cnt} KOHDETTA — ARVOSTUSVYOHYKE & Q-LAATU)\n"
    q_md += f"### A. AKTIIVISET SIGNAALIT & POIKKEAMAT ({len(active_df)} kpl)\n"
    q_md += format_ai_md_table(active_df)

    q_md += f"### B. EI AKTIIVISIA SIGNAALEJA — NEUTRAALIT ({len(inactive_df)} kpl)\n"
    q_md += format_ai_md_table(inactive_df)

    q_md += "## 2. ESILASKETTU [SPOT-2] VERROKKI- & [SPOT-4] KAUPPA-, PUSKURI-, KULU- JA NETTO-EV-MATRIISI\n"
    q_md += format_quant_md_table(quant_rows)
    q_md += f"[EOF: {loaded_cnt}/{total_cnt} OK | DOC_1_QUANT]\n"

    # DOKUMENTTI 2: TODENNETUT MAKRO-, SEKTORI- JA YHTIÖUUTISET (ST0_LIVE_NEWS_FEED)
    n_md = "# ST0_LIVE_NEWS_FEED — AI VERIFIED NEWS REPORT (v3.6 DUAL-DOC — APEX v7.1.0)\n"
    n_md += f"AIKALEIMA: {now_str} (PARI: ST0_LIVE_MARKET_FEED)\n"
    n_md += (
        f"UUTISTIHEYS ([DATA_DENSITY]): Tuore (<24h / OMXH <48h) todennettu uutinen: {fresh_cnt}/{loaded_cnt} kohteella | "
        f"Uutistyhjiö (>24h => [DATA:LOW]): {max(0, loaded_cnt - fresh_cnt)}/{loaded_cnt} kohteella\n"
    )
    n_md += "## 1. MAKRO- & SEKTORITUTKA (TOP-DOWN, TODENNETUT AIKALEIMAT, MAX 96H)\n"
    if macro_news or sector_news:
        for mn in macro_news:
            n_md += f"{mn}\n"
        for sn in sector_news:
            n_md += f"{sn}\n"
    else:
        n_md += "- Ei tuoreita (<96h) makro- tai sektoriuutisia.\n"

    n_md += "## 2. YHTIOKOHTAISET UUTISET (TODENNETUT AIKALEIMAT, TUOREIMMAT ENSIN)\n"
    if company_news:
        clean_c_news = [cn.replace("**", "") for cn in company_news[:28]]
        n_md += "\n".join(clean_c_news) + "\n"
    else:
        n_md += "- Ei todennettuja yhtiöuutisia.\n"

    n_md += f"[EOF_2: NEWS {loaded_cnt}/{total_cnt} OK]\n"
    return q_md, n_md

def build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news):
    q_md, _ = build_ai_dual_markdown_reports(now_str, macro_info, df, macro_news, sector_news, company_news)
    return q_md

# ==========================================
# MOOTTORI 2: IHMISEN SELKOKIELINEN NÄKYMÄ STREAMLITISSÄ (NUMEERINEN LAJITTELU)
# ==========================================
def build_human_display_df(sub_df):
    if sub_df.empty:
        return pd.DataFrame()
    cols = [
        "Ticker", "Kori", "Hinta", "Muutos %", "Signaali", "Taseprofiili",
        "RSI(14)", "pRVOL_num", "Dyn Tuki", "Dyn Trim", "Arvostus",
        "Kasvu / Marg / FCF", "Day Low-High", "ADR%", "Q-Tila", "Sessio"
    ]
    return sub_df[cols].copy()

HUMAN_COL_CONFIG = {
    "Ticker": st.column_config.TextColumn("Osake"),
    "Kori": st.column_config.TextColumn("Kori"),
    "Hinta": st.column_config.NumberColumn("Hinta", format="%.2f"),
    "Muutos %": st.column_config.NumberColumn("Päivä %", format="%+.2f %%"),
    "Signaali": st.column_config.TextColumn("Tila / Signaali"),
    "Taseprofiili": st.column_config.TextColumn("Tase & Nettokassa"),
    "RSI(14)": st.column_config.NumberColumn("RSI (14)", format="%.1f"),
    "pRVOL_num": st.column_config.NumberColumn("Volyymitahti", format="%.2fx"),
    "Dyn Tuki": st.column_config.TextColumn("Lähin Tuki"),
    "Dyn Trim": st.column_config.TextColumn("Tavoitevastus"),
    "Arvostus": st.column_config.TextColumn("Arvostus"),
    "Kasvu / Marg / FCF": st.column_config.TextColumn("Kasvu / Liikev.% / FCF"),
    "Day Low-High": st.column_config.TextColumn("Päivän Väli"),
    "ADR%": st.column_config.NumberColumn("ADR %", format="%.1f %%"),
    "Q-Tila": st.column_config.TextColumn("Tulos"),
    "Sessio": st.column_config.TextColumn("Istunto")
}

def get_webhook_url():
    try:
        return st.secrets.get("GAS_WEBHOOK_URL", "")
    except Exception:
        return ""

def push_to_google_drive_webhook(quant_md, news_md, webhook_url):
    if not webhook_url:
        return False, "Ei Webhook-URLia asetuksissa"
    try:
        payload = {"content": quant_md, "news_content": news_md}
        resp = requests.post(webhook_url, json=payload, timeout=12)
        if resp.status_code == 200 and "OK" in resp.text:
            return True, f"✅ Molemmat AI-raportit lähetetty Driveen! (Doc 1 Quant: {len(quant_md)} merkkiä | Doc 2 News: {len(news_md)} merkkiä)"
        return False, f"Webhook vastasi koodilla {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, f"Yhteysvirhe: {str(e)}"

# ==========================================
# KÄYTTÖLIITTYMÄ (UI) — IHMISEN OHJAAMO
# ==========================================
st.title("📡 ST0 Market Scout v3.6 Quant — Salkun Live-Ohjaamo (Dual-Doc)")
st.caption("Kaksijakoinen algoritminen moottori: Google Driveen lähetetään 2 merkkirajaturvallista v7.1.0-dokumenttia (Doc 1: Kvantti & EV-laskuri | Doc 2: Todennetut Uutiset).")

if st.button("🔄 Päivitä Live-Kurssit & Lähetä Molemmat AI-Syötteet Driveen", type="primary", use_container_width=True):
    st.cache_data.clear()

now_str, macro_info, df, macro_news, sector_news, company_news = fetch_all_market_data()
ai_quant_md, ai_news_md = build_ai_dual_markdown_reports(now_str, macro_info, df, macro_news, sector_news, company_news)

webhook_url = get_webhook_url()
ok, msg = push_to_google_drive_webhook(ai_quant_md, ai_news_md, webhook_url)

if ok:
    st.success(f"{msg} ({now_str}) — [EOF: {len(df)}/{len(TICKERS)} OK]. Avaa Gemini ja käytä taitoa **@st0-osakesijoittaja-apex**!")
else:
    st.warning(f"🕒 Ladattu: {now_str} | Doc 1 Quant: {len(ai_quant_md)} merkkiä | Doc 2 News: {len(ai_news_md)} merkkiä | {msg}")

# MAKROMITTARIKORTIT IHMISEN SILMÄILYYN
vix = macro_info.get("VIX", {})
vxn = macro_info.get("VXN", {})
us10y = macro_info.get("US10Y", {})
nq_f = macro_info.get("NQ_FUT", {})
smh = macro_info.get("SMH", {})
qqq = macro_info.get("QQQ", {})
spy = macro_info.get("SPY", {})
fx = macro_info.get("EURUSD", {})
meta_r = macro_info.get("META_REGIME", {})
rate_reg = meta_r.get("rate_regime", "RATE_CALM")
semi_sp = meta_r.get("semi_spread", 0.0)

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("S&P 500 VIX", f"{vix.get('price', 0.0):.2f}", f"{vix.get('chg_pct', 0.0):+.2f}%", delta_color="inverse")
m2.metric(
    "Tekno-pelko (VXN)",
    f"{vxn.get('price', 0.0):.2f}" if vxn.get("price", 0.0) > 0 else "-",
    f"{vxn.get('chg_pct', 0.0):+.2f}%" if vxn.get("price", 0.0) > 0 else None,
    delta_color="inverse"
)
m3.metric(
    "US 10v Korko",
    f"{us10y.get('price', 0.0):.2f}%",
    f"1d {us10y.get('bps_1d', 0):+d} / 20d {us10y.get('bps_20d', 0):+d} bps",
    delta_color="inverse"
)
m4.metric("Siruhajonta (SMH − SPY)", f"{semi_sp:+.2f} %-yks.", f"SMH {smh.get('chg_pct', 0.0):+.2f}%")
m5.metric("Nasdaq 24h Futuuri", f"{nq_f.get('chg_pct', 0.0):+.2f}%", f"QQQ 1d {qqq.get('chg_pct', 0.0):+.2f}%")
m6.metric("EUR / USD", f"{fx.get('price', 0.0):.3f}", f"SPY 1d {spy.get('chg_pct', 0.0):+.2f}%")

rate_banner_map = {
    "RATE_CALM": ("🟢 **Korkotila rauhallinen (`RATE_CALM`):** Normaali `+0,25x ADR` ostopuskuri voimassa laatuyhtiöille."),
    "RATE_ELEVATED": ("🟡 **Korkotaso koholla (`RATE_ELEVATED`, ≥ 5,15 % ilman korkoshokkia):** Nettokassa- (`🛡️ Linnoitus`) ja tulorahoitusyhtiöt (`⚙️ Tulorahoitus`) ostokelpoisia normaalilla puskurilla; `⚠️ Korkoherkiltä` puskuri pois."),
    "RATE_SHOCK": ("🔴 **Korkoshokki päällä (`RATE_SHOCK`, jyrkkä korkohyppy):** Kaikki `+0,25x ADR` ostopuskurit väliaikaisesti pois päältä — vaadi suora tukitaso tai `Flush-Trap`.")
}
st.info(rate_banner_map.get(rate_reg, rate_banner_map["RATE_CALM"]))

active_df = df[df["Signaali"] != "OK"] if not df.empty else pd.DataFrame()
inactive_df = df[df["Signaali"] == "OK"] if not df.empty else pd.DataFrame()

st.header(f"📊 Salkku & Seurantalista ({len(df)}/{len(TICKERS)} kohdetta)")

st.subheader(f"🚨 1. Huomiota Vaativat Signaalit ({len(active_df)} kpl)")
if not active_df.empty:
    st.dataframe(
        build_human_display_df(active_df),
        column_config=HUMAN_COL_CONFIG,
        use_container_width=True,
        hide_index=True
    )
else:
    st.caption("Ei aktiivisia signaaleja tällä hetkellä.")

st.subheader(f"🟢 2. Neutraalissa Tilassa Olevat Kohteet ({len(inactive_df)} kpl)")
if not inactive_df.empty:
    st.dataframe(
        build_human_display_df(inactive_df),
        column_config=HUMAN_COL_CONFIG,
        use_container_width=True,
        hide_index=True
    )

with st.expander(f"📋 TARKISTA AI-SYÖTTEET (Doc 1 Quant: {len(ai_quant_md)} merkkiä | Doc 2 News: {len(ai_news_md)} merkkiä)", expanded=not ok):
    t1, t2 = st.tabs(["📊 Doc 1: ST0_LIVE_MARKET_FEED (Kvantti & EV)", "📰 Doc 2: ST0_LIVE_NEWS_FEED (Uutiset)"])
    with t1:
        st.code(ai_quant_md, language="markdown")
    with t2:
        st.code(ai_news_md, language="markdown")

st.divider()

# 3. UUTISOSIO IHMISEN NÄKYMÄSSÄ
st.header("📰 Markkina-, Sektori- & Yhtiöuutiset")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🌐 Makro- & Sektoritutka")
    if macro_news or sector_news:
        for mn in macro_news:
            st.markdown(mn)
        for sn in sector_news:
            st.markdown(sn)
    else:
        st.caption("Ei tuoreita makro-/sektoriuutisia.")

with col2:
    st.subheader(f"🏢 Yhtiökohtaiset Uutiset ({len(company_news)} kpl)")
    if company_news:
        for cn in company_news[:21]:
            st.markdown(cn)
    else:
        st.caption("Ei tuoreita yhtiökohtaisia uutisia.")
