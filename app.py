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
    page_title="ST0 Market Scout v3.7 Triple-Doc Cloud Quant",
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
# ALGORITMI E (PILVI): SALKKU-, UNIT-NAV-, HÄLYTYS- JA HORIZON-SHIFT-LASKURI (DOC 3: ST0_LIVE_PORTFOLIO_QUANT)
# ==========================================
DEFAULT_PORTFOLIO_STATE = {
    "cash_ost_eur": 8797.12,
    "cash_aot_eur": 10.00,
    "housing_reservation_eur": 4000.00,
    "tied_buy_orders_eur": 0.00,
    "ost_cumulative_pnl_eur": -3975.71,
    "baseline_nov01_eur": 45763.73,
    "anchor_equity_eur": 45224.25,
    "anchor_unit_nav_eur": 45.22425,
    "anchor_total_units": 1000.000,
    "positions": [
        {"ticker": "GOOG",    "account": "OST", "bucket": "K1:Core",  "bs": "FORT", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "USD", "shares": 27.0,  "avg_price": 308.77, "lower_alert": 272.00, "buy_alert": 275.00, "trim_target": "Hold H3 (HOT P/E yli 28x)", "kill": "Search-kasvu negatiivinen tai OpM alle 26%"},
        {"ticker": "AMZN",    "account": "OST", "bucket": "K1:Core",  "bs": "SELF", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "USD", "shares": 16.0,  "avg_price": 260.17, "lower_alert": 255.00, "buy_alert": 256.94, "trim_target": "Hold H3 (HOT P/E yli 35x)", "kill": "AWS-kasvu alle 12% tai OpM alle 10%"},
        {"ticker": "AVGO",    "account": "OST", "bucket": "K2:Semi",  "bs": "FORT", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "USD", "shares": 18.0,  "avg_price": 354.66, "lower_alert": 296.31, "buy_alert": 299.64, "trim_target": "Hold H3 (HOT P/E yli 38x)", "kill": "XPU-sopimusmenetys tai OpM alle 40%"},
        {"ticker": "TSM",     "account": "OST", "bucket": "K2:Semi",  "bs": "FORT", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "USD", "shares": 12.0,  "avg_price": 364.88, "lower_alert": 365.49, "buy_alert": 370.00, "trim_target": "Hold H3 (HOT P/E yli 28x)", "kill": "Kuukausimyynti alle +20% YoY tai Taiwan-eskalaatio"},
        {"ticker": "NVDA",    "account": "OST", "bucket": "K2:Semi",  "bs": "FORT", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "USD", "shares": 20.0,  "avg_price": 177.91, "lower_alert": 158.49, "buy_alert": 160.39, "trim_target": "200-240 USD (H1-erä 178.14 USD)", "kill": "DC-bruttokate alle 70% tai Q3-ohjeistuspettymys"},
        {"ticker": "MU",      "account": "OST", "bucket": "K2:Semi",  "bs": "FORT", "q_tier": "Q2", "sleeve": "H2", "shift_ok": False, "ccy": "USD", "shares": 3.0,   "avg_price": 867.08, "lower_alert": 725.00, "buy_alert": 665.00, "trim_target": "865-910 USD (100% exit RSI yli 68)", "kill": "HBM-hinnat laskuun tai SMA200 murtuma pRVOL yli 1.5x"},
        {"ticker": "ASML",    "account": "OST", "bucket": "K2:Semi",  "bs": "FORT", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "USD", "shares": 1.0,   "avg_price": 1013.80, "lower_alert": 1384.96, "buy_alert": 1415.00, "trim_target": "Ei myyntikattoa (alipaino 2.93%)", "kill": "Tilauskertymä alle 2.5 mrd EUR kahdesti"},
        {"ticker": "SPCX",    "account": "OST", "bucket": "K3:Beta",  "bs": "DEBT", "q_tier": "Q3", "sleeve": "H1", "shift_ok": False, "ccy": "USD", "shares": 29.0,  "avg_price": 138.08, "lower_alert": 135.00, "buy_alert": 0.00,   "trim_target": "140.69-147.30 USD (tai vaihto ANT IPO)", "kill": "Starship-lentokielto tai BB-Low 127.09 murtuma"},
        {"ticker": "MSTR",    "account": "OST", "bucket": "K3:Beta",  "bs": "DEBT", "q_tier": "Q3", "sleeve": "H1", "shift_ok": False, "ccy": "USD", "shares": 16.0,  "avg_price": 139.55, "lower_alert": 108.25, "buy_alert": 0.00,   "trim_target": "116.00-120.95 USD (2/2 strikes exit)", "kill": "BTC viikkopäätös alle 72k USD + MSCI 30.11. poisto (2/2)"},
        {"ticker": "WRT1V",   "account": "OST", "bucket": "K4:Suomi", "bs": "FORT", "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,  "ccy": "EUR", "shares": 106.0, "avg_price": 27.36,  "lower_alert": 24.51,  "buy_alert": 24.80,  "trim_target": "29.50-31.00 EUR (HOT P/E yli 22.5x)", "kill": "Tilauskertymän lasku 2 kvartaalia tai alle 24.51 EUR"},
        {"ticker": "FRAMERY", "account": "OST", "bucket": "K4:Suomi", "bs": "SELF", "q_tier": "Q2", "sleeve": "H2", "shift_ok": False, "ccy": "EUR", "shares": 230.0, "avg_price": 8.69,   "lower_alert": 6.79,   "buy_alert": 6.86,   "trim_target": "7.90-7.95 EUR (RSI 71.5 yliostettu)", "kill": "Putoaminen takaisin alle SMA200 6.79 EUR"}
    ],
    "orders": [
        {"ticker": "FRAMERY", "action": "SELL_LIMIT_OMXH_MA_0945", "shares": 230.0, "limit_price": 7.95,   "ccy": "EUR", "note": "Uusitaan ma 16.11. klo 09:45 (RSI 71.5 TRIM)"},
        {"ticker": "SPCX",    "action": "SELL_LIMIT_US_EXT_1100",  "shares": 29.0,  "limit_price": 140.69, "ccy": "USD", "note": "Dyn Trim -0.25x ADR (vapautus kohti ANT IPO)"},
        {"ticker": "MSTR",    "action": "SELL_LIMIT_2OF2_EXIT",    "shares": 16.0,  "limit_price": 120.95, "ccy": "USD", "note": "2/2 strikes exit pomppuun (suoja 108.25 USD)"}
    ]
}

def calc_one_way_nordnet_sell_eur(shares, price, ccy, eur_usd):
    if ccy == "EUR":
        gross = round(float(shares) * float(price), 2)
        fee = round(max(5.0, gross * 0.001), 2)
        return gross, fee, round(gross - fee, 2)
    gross = round((float(shares) * float(price)) / float(eur_usd), 2)
    fee = round(15.0 + gross * 0.0025, 2)
    return gross, fee, round(gross - fee, 2)

def extract_portfolio_state_from_doc3_text(doc3_text):
    if not doc3_text or "PORTFOLIO_STATE_JSON:" not in doc3_text:
        return None
    try:
        after = doc3_text.split("PORTFOLIO_STATE_JSON:", 1)[1]
        for line in after.splitlines():
            s = line.strip()
            if s.startswith("{") and s.endswith("}"):
                raw = json.loads(s)
                if "positions" in raw:
                    return raw
                # Laajenna tiivis muoto ("p" ja "o") täydeksi tilaksi
                base = json.loads(json.dumps(DEFAULT_PORTFOLIO_STATE))
                base["cash_ost_eur"] = float(raw.get("c_ost", base["cash_ost_eur"]))
                base["cash_aot_eur"] = float(raw.get("c_aot", base["cash_aot_eur"]))
                base["housing_reservation_eur"] = float(raw.get("h_res", base["housing_reservation_eur"]))
                base["tied_buy_orders_eur"] = float(raw.get("t_buy", base["tied_buy_orders_eur"]))
                default_by_t = {x["ticker"]: x for x in base["positions"]}
                if "p" in raw and isinstance(raw["p"], list):
                    new_pos = []
                    for item in raw["p"]:
                        tk = str(item[0])
                        tmpl = dict(default_by_t.get(tk, {
                            "ticker": tk, "account": "OST", "bucket": "K1:Core", "bs": "FORT",
                            "q_tier": "Q1", "sleeve": "H3", "shift_ok": True,
                            "ccy": "EUR" if tk in ("WRT1V", "FRAMERY", "NOKIA") else "USD",
                            "trim_target": "-", "kill": "-"
                        }))
                        tmpl["shares"] = float(item[1])
                        tmpl["avg_price"] = float(item[2])
                        tmpl["sleeve"] = str(item[3])
                        tmpl["lower_alert"] = float(item[4])
                        tmpl["buy_alert"] = float(item[5])
                        new_pos.append(tmpl)
                    base["positions"] = new_pos
                if "o" in raw and isinstance(raw["o"], list):
                    base["orders"] = [
                        {"ticker": str(x[0]), "action": str(x[1]), "shares": float(x[2]), "limit_price": float(x[3]), "ccy": str(x[4]), "note": ""}
                        for x in raw["o"]
                    ]
                return base
    except Exception:
        return None
    return None

def load_cloud_portfolio_state(webhook_url):
    if "portfolio_state" in st.session_state and isinstance(st.session_state["portfolio_state"], dict):
        return st.session_state["portfolio_state"]
    loaded_state = None
    if webhook_url:
        try:
            resp = requests.post(webhook_url, json={"action": "get_portfolio_state"}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                raw_json = data.get("portfolio_state_json", "")
                if raw_json:
                    loaded_state = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                elif data.get("doc3_text"):
                    loaded_state = extract_portfolio_state_from_doc3_text(data.get("doc3_text", ""))
        except Exception:
            loaded_state = None
    if not isinstance(loaded_state, dict) or "positions" not in loaded_state:
        loaded_state = json.loads(json.dumps(DEFAULT_PORTFOLIO_STATE))
    st.session_state["portfolio_state"] = loaded_state
    return loaded_state

def build_ai_portfolio_quant_report(now_str, macro_info, df, p_state=None):
    """Algoritmi E pilvessä: tuottaa Doc 3 (ST0_LIVE_PORTFOLIO_QUANT) tekstin (alle 7 500 merkkiä, SYNTAX_LOCK_CLEAN) ja UI-metriikat."""
    if not isinstance(p_state, dict) or "positions" not in p_state:
        p_state = json.loads(json.dumps(DEFAULT_PORTFOLIO_STATE))

    fx_val = float((macro_info.get("EURUSD") or {}).get("price", 1.103)) or 1.103
    meta_r = macro_info.get("META_REGIME", {})
    rate_reg = meta_r.get("rate_regime", "RATE_ELEVATED")
    clock_str = meta_r.get("clock_status", "-")
    quant_rows = macro_info.get("QUANT_ROWS", [])

    live_map = {}
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            sym_k = str(r.get("_sym") or r.get("Ticker") or "").split("(")[0].strip()
            live_map[sym_k] = r

    spot4_map = {str(q.get("Ticker", "")).split("(")[0].strip(): q for q in (quant_rows or [])}

    cash_ost = float(p_state.get("cash_ost_eur", 8797.12))
    cash_aot = float(p_state.get("cash_aot_eur", 10.00))
    cash_total = round(cash_ost + cash_aot, 2)
    housing_res = float(p_state.get("housing_reservation_eur", 4000.00))
    tied_buys = float(p_state.get("tied_buy_orders_eur", 0.00))
    free_dry_powder = round(cash_total - housing_res - tied_buys, 2)
    ost_cum_pnl = float(p_state.get("ost_cumulative_pnl_eur", -3975.71))
    base_nov01 = float(p_state.get("baseline_nov01_eur", 45763.73))
    anchor_eq = float(p_state.get("anchor_equity_eur", 45224.25))
    anchor_nav = float(p_state.get("anchor_unit_nav_eur", 45.22425))
    anchor_units = float(p_state.get("anchor_total_units", 1000.0))

    pos_records = []
    tot_mkt_eur = 0.0
    tot_open_pnl_eur = 0.0
    bucket_eur = {"K1:Core": 0.0, "K2:Semi": 0.0, "K3:Beta": 0.0, "K4:Suomi": 0.0}
    horizon_eur = {"H1": 0.0, "H2": 0.0, "H3": 0.0}

    for pos in p_state.get("positions", []):
        t = str(pos.get("ticker", "")).strip()
        sh = float(pos.get("shares", 0.0))
        if sh <= 0:
            continue
        avg_p = float(pos.get("avg_price", 0.0))
        ccy = str(pos.get("ccy", "USD")).strip()
        b_col = str(pos.get("bucket", "K1:Core")).strip()
        bs = str(pos.get("bs", "FORT")).strip()
        qt = str(pos.get("q_tier", "Q1")).strip()
        slv = str(pos.get("sleeve", "H3")).strip()
        shift_ok = bool(pos.get("shift_ok", qt == "Q1"))

        lrow = live_map.get(t)
        if lrow is not None:
            cur_p = float(lrow.get("Hinta", avg_p))
            chg_1d = float(lrow.get("Muutos %", 0.0))
            day_lh = str(lrow.get("Day Low-High", f"{cur_p:.2f}-{cur_p:.2f}"))
            lh_parts = day_lh.split("-")
            d_low = float(lh_parts[0]) if len(lh_parts) == 2 else cur_p
            rsi_v = float(lrow.get("RSI(14)", 50.0))
            prvol_v = float(lrow.get("pRVOL_num", 1.0))
            sma200_v = float(lrow.get("SMA200%", 0.0))
            adr_v = float(lrow.get("ADR%", 3.5))
            val_str = str(lrow.get("Arvostus", "-"))
            sup_str = str(lrow.get("Dyn Tuki", "-"))
            sup_p = float(sup_str.split("(")[0]) if "(" in sup_str else cur_p
            trim_str = str(lrow.get("Dyn Trim", "-"))
            trim_p = float(trim_str.split("(")[0]) if "(" in trim_str else cur_p
            sig_str = str(lrow.get("Signaali", "OK"))
            dd_str = "HIGH" if bool(lrow.get("_has_fresh_24h_news", True)) else "LOW_HUMAN_EDGE"
        else:
            cur_p = avg_p
            chg_1d = 0.0
            day_lh = f"{cur_p:.2f}-{cur_p:.2f}"
            d_low = cur_p
            rsi_v = 50.0
            prvol_v = 1.0
            sma200_v = 0.0
            adr_v = 3.5
            val_str = "-"
            sup_str = "-"
            sup_p = cur_p
            trim_str = "-"
            trim_p = cur_p
            sig_str = "OK"
            dd_str = "HIGH"

        fx_div = 1.0 if ccy == "EUR" else fx_val
        val_e = (sh * cur_p) / fx_div
        pnl_e = ((cur_p - avg_p) * sh) / fx_div
        pnl_p = ((cur_p / avg_p) - 1.0) * 100.0 if avg_p > 0 else 0.0
        dist_sup = ((cur_p / sup_p) - 1.0) * 100.0 if sup_p > 0 else 0.0

        tot_mkt_eur += val_e
        tot_open_pnl_eur += pnl_e
        if b_col in bucket_eur:
            bucket_eur[b_col] += val_e
        if slv in horizon_eur:
            horizon_eur[slv] += val_e

        pos_records.append({
            **pos,
            "has_live": lrow is not None,
            "live_price": cur_p,
            "chg_1d": chg_1d,
            "day_lh": day_lh,
            "day_low": d_low,
            "rsi": rsi_v,
            "prvol": prvol_v,
            "sma200_pct": sma200_v,
            "adr_pct": adr_v,
            "val_dna": val_str,
            "sup_str": sup_str,
            "sup_price": sup_p,
            "dist_sup_pct": dist_sup,
            "trim_str": trim_str,
            "trim_price": trim_p,
            "signal": sig_str,
            "data_density": dd_str,
            "val_eur": val_e,
            "pnl_eur": pnl_e,
            "pnl_pct": pnl_p,
            "shift_ok": shift_ok,
        })

    tot_eq_eur = round(tot_mkt_eur + cash_total, 2)
    ost_eq_eur = round(tot_mkt_eur + cash_ost, 2)
    for pr in pos_records:
        pr["weight_pct"] = round((pr["val_eur"] / tot_eq_eur) * 100.0, 2) if tot_eq_eur > 0 else 0.0

    unit_nav = tot_eq_eur / anchor_units if anchor_units > 0 else 0.0
    twr_pct = ((unit_nav / anchor_nav) - 1.0) * 100.0 if anchor_nav > 0 else 0.0
    nov01_pct = ((tot_eq_eur / base_nov01) - 1.0) * 100.0 if base_nov01 > 0 else 0.0
    units_redeemed = housing_res / unit_nav if unit_nav > 0 else 0.0
    rem_units = anchor_units - units_redeemed

    # Hälytykset, myyntijono, Exit Drift ja Stale-Bid
    alerts_list = []
    sell_queue_lines = []
    stale_bid_lines = []
    pending_sells_net_eur = 0.0
    pos_by_t = {pr["ticker"]: pr for pr in pos_records}

    for o in p_state.get("orders", []):
        ot = str(o.get("ticker", "")).strip()
        osh = float(o.get("shares", 0.0))
        olp = float(o.get("limit_price", 0.0))
        occy = str(o.get("ccy", "USD")).strip()
        if osh > 0 and olp > 0:
            g_e, f_e, n_e = calc_one_way_nordnet_sell_eur(osh, olp, occy, fx_val)
            pending_sells_net_eur = round(pending_sells_net_eur + n_e, 2)
            pr_match = pos_by_t.get(ot)
            drift_tag = "EXIT_OK"
            if pr_match and pr_match["trim_price"] > 0:
                diff_vs_trim = ((olp / pr_match["trim_price"]) - 1.0) * 100.0
                if olp > pr_match["trim_price"] * 1.001:
                    drift_tag = f"EXIT_DRIFT (+{diff_vs_trim:.1f}% yli {pr_match['trim_str']})"
                else:
                    drift_tag = f"EXIT_OK ({diff_vs_trim:+.1f}% vs {pr_match['trim_str']})"
            sell_queue_lines.append(
                f"- MYYNTI {ot} ({int(osh)} kpl @ {olp:.2f} {occy}): {g_e:.2f} - kulu {f_e:.2f} = +{n_e:.2f} EUR netto [{drift_tag}]"
            )

    for pr in pos_records:
        t = pr["ticker"]
        lp = pr["live_price"]
        dl = pr["day_low"]
        low_al = float(pr.get("lower_alert", 0.0) or 0.0)
        buy_al = float(pr.get("buy_alert", 0.0) or 0.0)
        if pr.get("has_live") and pr["sup_price"] > 0 and (dl <= pr["sup_price"] * 1.005 or pr["dist_sup_pct"] <= 1.6):
            alerts_list.append(
                f"- {t} [SUPPORT_TEST]: Live {lp:.2f} {pr['ccy']} (Low {dl:.2f}) tuki {pr['sup_str']} ({pr['dist_sup_pct']:+.2f}%, RSI {pr['rsi']:.1f}, pRVOL {pr['prvol']:.2f}x)"
            )
        if pr.get("has_live") and -1.5 <= pr["sma200_pct"] <= 1.0:
            alerts_list.append(
                f"- {t} [SMA200_TEST]: Live {lp:.2f} {pr['ccy']} SMA200-tasolla ({pr['sma200_pct']:+.1f}%, pRVOL {pr['prvol']:.2f}x)"
            )
        if low_al > 0 and (dl <= low_al or lp <= low_al * 1.012):
            alerts_list.append(
                f"- {t} [LOWER_ALERT_HIT]: Low {dl:.2f} / Live {lp:.2f} {pr['ccy']} vs alahalytys {low_al:.2f} {pr['ccy']}"
            )
        if pr["rsi"] >= 68.0 or "TRIM" in pr["signal"]:
            alerts_list.append(
                f"- {t} [OVERBOUGHT_TRIM]: RSI {pr['rsi']:.1f} ({pr['signal']}), kotiuta vastukseen ({pr.get('trim_target', pr['trim_str'])})"
            )
        if buy_al > 0 and pr["adr_pct"] > 0:
            gap_pct = ((lp - buy_al) / lp) * 100.0
            adr_mult = gap_pct / pr["adr_pct"]
            if adr_mult > 2.0:
                stale_bid_lines.append(
                    f"- {t} [STALE_BID]: Osto-alert {buy_al:.2f} {pr['ccy']} (-{gap_pct:.1f}% / {adr_mult:.2f}x ADR), pida puhelinhalytyksena"
                )

    # Clean-Slate Top 3 (pl. TRIM-kohteet)
    clean_candidates = []
    for q in (quant_rows or []):
        qt_sym = str(q.get("Ticker", "")).split("(")[0].strip()
        lrow = live_map.get(qt_sym)
        if lrow is not None and ("TRIM" in str(lrow.get("Signaali", "")) or float(lrow.get("RSI(14)", 50.0)) >= 68.0):
            continue
        ev_str = str(q.get("EV_Str", "0%/+0e"))
        ev_val = float(ev_str.split("/")[1].replace("e", "").replace("+", "")) if "/" in ev_str else 0.0
        clean_candidates.append((ev_val, qt_sym, q))
    clean_candidates.sort(key=lambda x: x[0], reverse=True)
    top3_cs_str = ", ".join(
        f"{sym} ({q.get('EV_Str', '+0e')}, R:R {q.get('RR_Days_Str', '-')} @ {str(q.get('Buy_Limit_Str', '-')).split('(')[0]})"
        for _, sym, q in clean_candidates[:3]
    ) or "AVGO (+239e)"
    best_cs_sym = clean_candidates[0][1] if clean_candidates else "AVGO"
    best_cs_ev = clean_candidates[0][0] if clean_candidates else 239.0

    # Rakenna Doc 3 Markdown (SYNTAX_LOCK_CLEAN: ei $, ~, <, > merkkejä!)
    r1_h1 = f"{round(tot_eq_eur*0.008)}-{round(tot_eq_eur*0.012)} EUR"
    r1_h2 = f"{round(tot_eq_eur*0.012)}-{round(tot_eq_eur*0.020)} EUR"
    r1_h3 = f"{round(tot_eq_eur*0.020)}-{round(tot_eq_eur*0.035)} EUR"

    p_md = "# ST0_LIVE_PORTFOLIO_QUANT — ALGORITMI E (v3.7 TRIPLE-DOC — APEX v7.1.0)\n"
    p_md += f"AIKALEIMA: {now_str} | EUR/USD: {fx_val:.3f} | KORKO & KELLO: {rate_reg} | {clock_str}\n"

    p_md += "## 1. LIVE-SALKKU, OST+AOT KASSA, UNIT-NAV TWR% & ASUNTOVARAUS\n"
    p_md += f"- KOKONAISPAAOMA: {tot_eq_eur:.2f} EUR (OST {ost_eq_eur:.2f} + AOT {cash_aot:.2f} | 01.11. {base_nov01:.2f} EUR, {nov01_pct:+.2f}%)\n"
    p_md += f"- OSAKKEET ({len(pos_records)} rivia): {tot_mkt_eur:.2f} EUR ({(tot_mkt_eur/tot_eq_eur)*100:.2f}%) | Avoin PnL: {tot_open_pnl_eur:+.2f} EUR | OST kumul. PnL: {ost_cum_pnl:+.2f} EUR (100% verovapaa nosto)\n"
    p_md += f"- KASSA: {cash_total:.2f} EUR ({(cash_total/tot_eq_eur)*100:.2f}%) | Asuntovaraus: {housing_res:.2f} EUR | Ostopilkit: {tied_buys:.2f} EUR | DRY POWDER: {free_dry_powder:.2f} EUR ({(free_dry_powder/tot_eq_eur)*100:.2f}%)\n"
    p_md += f"- UNIT-NAV & TWR%: {unit_nav:.5f} EUR/osuus ({twr_pct:+.2f}% yli 09.11. ankkurin {anchor_nav:.5f} EUR / {anchor_units:.1f} osuutta)\n"
    p_md += f"- ASUNTOVARAUS (4000 EUR): A) Nosto lunastaa {units_redeemed:.3f} osuutta (jaa {rem_units:.3f} osuutta, NAV {unit_nav:.5f} EUR = 0.00% TWR-vaaristymä) | B) Vapautus nostaa vapaan kassan {cash_total:.2f} EUR\n"
    p_md += f"- MYYNTIJONON NETTO: +{pending_sells_net_eur:.2f} EUR netto (vapaa kassa {free_dry_powder + pending_sells_net_eur:.2f} EUR / B: {cash_total + pending_sells_net_eur:.2f} EUR ke 18.11. ANT OST-IPOon)\n"

    p_md += "## 2. 4-KORIN (K1-K4) VAPAA KAPASITEETTI & 3-HORISONTIN (H1-H3) 1R-BUDJETIT\n"
    b_caps = [("K1:Core", 25.0, 40.0), ("K2:Semi", 30.0, 42.0), ("K3:Beta", 0.0, 18.0), ("K4:Suomi", 8.0, 20.0)]
    for bk, b_fl, b_cp in b_caps:
        bv = bucket_eur.get(bk, 0.0)
        bp = (bv / tot_eq_eur) * 100.0 if tot_eq_eur > 0 else 0.0
        rem_e = (tot_eq_eur * (b_cp / 100.0)) - bv
        rem_p = b_cp - bp
        st_lbl = "ALIPAINO" if (b_fl > 0 and bp < b_fl) else ("YLITETTY!" if bp > b_cp else "OK")
        p_md += f"- {bk}: {bv:.2f} EUR ({bp:.2f}% / katto {b_cp:.0f}%) | Vapaa: {rem_e:+.2f} EUR ({rem_p:+.2f} pp) [{st_lbl}]\n"
    p_md += (
        f"- HORISONTIT & 1R: H1 (2pv-4vk, AI 80/20, 1R {r1_h1}): {horizon_eur['H1']:.2f} EUR ({(horizon_eur['H1']/tot_eq_eur)*100:.2f}%) | "
        f"H2 (1-12kk, AI 50/50, 1R {r1_h2}): {horizon_eur['H2']:.2f} EUR ({(horizon_eur['H2']/tot_eq_eur)*100:.2f}%) | "
        f"H3 (1-5v, Human 65/35, 1R {r1_h3}): {horizon_eur['H3']:.2f} EUR ({(horizon_eur['H3']/tot_eq_eur)*100:.2f}%)\n"
    )

    p_md += "## 3. 11 AKTIIVISEN SALKKUPOSITION REAALIAIKAINEN MATRIISI\n"
    p_md += "|Ticker|Tase:Q:H|Kpl|Kh|Live(1d%)|ArvoEUR(Paino%)|PnLEUR(%)|Arvostus|RSI/pRVOL|Tuki(Et.)|DynTrim|Data|Signaali|\n"
    p_md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    for pr in pos_records:
        p_md += (
            f"|{pr['ticker']}|{pr['bs']}:{pr['q_tier']}:{pr['sleeve']}|{int(pr['shares'])}|{pr['avg_price']:.2f}|"
            f"{pr['live_price']:.2f} {pr['ccy']}({pr['chg_1d']:+.2f}%)|{pr['val_eur']:.0f}e({pr['weight_pct']:.2f}%)|"
            f"{pr['pnl_eur']:+.0f}e({pr['pnl_pct']:+.2f}%)|{pr['val_dna']}|{pr['rsi']:.1f}/{pr['prvol']:.2f}x|"
            f"{pr['sup_str']}({pr['dist_sup_pct']:+.1f}%)|{pr['trim_str']}|{pr['data_density']}|{pr['signal']}|\n"
        )

    p_md += "## 4. LAUENNEET KURSSIHALYTYKSET, 1-SUUNNAN MYYNTIJONO, EXIT DRIFT & STALE-BID\n"
    for al in alerts_list:
        p_md += f"{al}\n"
    for sq in sell_queue_lines:
        p_md += f"{sq}\n"
    for sb in stale_bid_lines:
        p_md += f"{sb}\n"

    p_md += "## 5. TAPPIOLLISTEN RIVIEN 4-PORTTINEN HORIZON_SHIFT_GATE & CLEAN-SLATE TESTI\n"
    p_md += f"- CLEAN-SLATE TOP 3 (SPOT-4): {top3_cs_str}\n"
    losing_recs = sorted([pr for pr in pos_records if pr["pnl_eur"] < 0], key=lambda x: x["pnl_eur"])
    for lr in losing_recs:
        lt = lr["ticker"]
        lqt = lr["q_tier"]
        lsl = lr["sleeve"]
        s4_item = spot4_map.get(lt)
        own_ev_str = s4_item.get("EV_Str", "-") if s4_item else "ei H1-sign."
        if lqt == "Q3" or (not lr["shift_ok"] and lsl == "H1"):
            verdict = "KIELLETTY(Ulysses_Q3_DEBT_H1)"
        elif lqt == "Q2" and lsl == "H2":
            verdict = "EI_SIIRTOA_H3(Q2_raja_H2)"
        else:
            verdict = "PASS(Q1_H3_ydin)"
        p_md += (
            f"- {lt} ({lr['pnl_eur']:+.0f}e / {lr['pnl_pct']:+.2f}%, {lqt}/{lsl}, Data:{lr['data_density']}): "
            f"{verdict} | SPOT4: {own_ev_str} vs {best_cs_sym}(+{best_cs_ev:.0f}e) | Kill: {lr.get('kill', '-')}\n"
        )

    # Tiivis koneluettava salkkutila Doc 3:n loppuun (~600 merkkiä) ja täysi JSON PropertiesServiceen
    doc3_compact_state = {
        "c_ost": round(cash_ost, 2),
        "c_aot": round(cash_aot, 2),
        "h_res": round(housing_res, 2),
        "t_buy": round(tied_buys, 2),
        "p": [
            [
                x["ticker"],
                round(float(x["shares"]), 4),
                round(float(x["avg_price"]), 2),
                str(x.get("sleeve", "H3")),
                round(float(x.get("lower_alert", 0.0) or 0.0), 2),
                round(float(x.get("buy_alert", 0.0) or 0.0), 2),
            ]
            for x in p_state.get("positions", [])
        ],
        "o": [
            [
                str(o.get("ticker", "")),
                str(o.get("action", "SELL")),
                round(float(o.get("shares", 0.0)), 4),
                round(float(o.get("limit_price", 0.0)), 2),
                str(o.get("ccy", "USD")),
            ]
            for o in p_state.get("orders", [])
        ],
    }
    doc3_json_str = json.dumps(doc3_compact_state, ensure_ascii=False, separators=(",", ":"))
    full_state_json_str = json.dumps(
        {
            "cash_ost_eur": round(cash_ost, 2),
            "cash_aot_eur": round(cash_aot, 2),
            "housing_reservation_eur": round(housing_res, 2),
            "tied_buy_orders_eur": round(tied_buys, 2),
            "ost_cumulative_pnl_eur": round(ost_cum_pnl, 2),
            "baseline_nov01_eur": round(base_nov01, 2),
            "anchor_equity_eur": round(anchor_eq, 2),
            "anchor_unit_nav_eur": round(anchor_nav, 5),
            "anchor_total_units": round(anchor_units, 3),
            "positions": p_state.get("positions", []),
            "orders": p_state.get("orders", []),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    p_md += "## 6. PORTFOLIO_STATE_JSON (PILVIMUISTI)\n"
    p_md += f"PORTFOLIO_STATE_JSON: {doc3_json_str}\n"
    p_md += f"[EOF_3: PORTFOLIO {len(pos_records)}/{len(pos_records)} OK]\n"

    # Varmista syntaksilukko Doc 3:ssa (korvaa mahdolliset raa'at <, >, $, ~ merkit)
    p_md = p_md.replace("$", "USD ").replace("~", "noin ").replace("<=", "enintaan ").replace(">=", "vahintaan ").replace("<", "alle ").replace(">", "yli ")

    summary_meta = {
        "total_equity_eur": tot_eq_eur,
        "ost_equity_eur": ost_eq_eur,
        "mkt_val_eur": round(tot_mkt_eur, 2),
        "open_pnl_eur": round(tot_open_pnl_eur, 2),
        "cash_total_eur": cash_total,
        "free_dry_powder_eur": free_dry_powder,
        "unit_nav": round(unit_nav, 5),
        "twr_pct": round(twr_pct, 2),
        "pending_sells_net_eur": pending_sells_net_eur,
        "alerts_list": alerts_list,
        "sell_queue_lines": sell_queue_lines,
        "stale_bid_lines": stale_bid_lines,
        "pos_records": pos_records,
        "losing_recs": losing_recs,
        "bucket_eur": bucket_eur,
        "horizon_eur": horizon_eur,
        "state_json_str": full_state_json_str,
    }
    return p_md, summary_meta

def build_ai_triple_markdown_reports(now_str, macro_info, df, macro_news, sector_news, company_news, p_state=None):
    q_md, n_md = build_ai_dual_markdown_reports(now_str, macro_info, df, macro_news, sector_news, company_news)
    p_md, p_meta = build_ai_portfolio_quant_report(now_str, macro_info, df, p_state)
    return q_md, n_md, p_md, p_meta

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

def push_to_google_drive_webhook(quant_md, news_md, webhook_url, portfolio_md=None, portfolio_state_json=None):
    if not webhook_url:
        return False, "Ei Webhook-URLia asetuksissa"
    try:
        payload = {"content": quant_md, "news_content": news_md}
        if portfolio_md:
            payload["portfolio_content"] = portfolio_md
        if portfolio_state_json:
            payload["portfolio_state_json"] = portfolio_state_json
        resp = requests.post(webhook_url, json=payload, timeout=14)
        if resp.status_code == 200 and "OK" in resp.text:
            if portfolio_md:
                return True, f"✅ Kaikki 3 AI-raporttia lähetetty Driveen! (Doc 1 Quant: {len(quant_md)} m | Doc 2 News: {len(news_md)} m | Doc 3 Portfolio: {len(portfolio_md)} m)"
            return True, f"✅ Molemmat AI-raportit lähetetty Driveen! (Doc 1 Quant: {len(quant_md)} merkkiä | Doc 2 News: {len(news_md)} merkkiä)"
        return False, f"Webhook vastasi koodilla {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, f"Yhteysvirhe: {str(e)}"

# ==========================================
# KÄYTTÖLIITTYMÄ (UI) — IHMISEN OHJAAMO + MOBIILISALKKULASKURI (TRIPLE-DOC v3.7)
# ==========================================
st.title("📡 ST0 Market Scout v3.7 Triple-Doc Cloud Quant — Salkun Live-Ohjaamo")
st.caption("Kolmen dokumentin pilvimoottori: Google Driveen (ja NotebookLM-linkkeihin) päivittyy yhdellä napilla Doc 1 (Kvantti & EV), Doc 2 (Uutiset) ja Doc 3 (Algoritmi E: Salkkulaskuri, Hälytykset & Horizon-Shift).")

webhook_url = get_webhook_url()
p_state_active = load_cloud_portfolio_state(webhook_url)

if st.button("🔄 Päivitä Live-Kurssit & Lähetä Kaikki 3 AI-Syötettä Driveen", type="primary", use_container_width=True):
    st.cache_data.clear()

now_str, macro_info, df, macro_news, sector_news, company_news = fetch_all_market_data()
ai_quant_md, ai_news_md, ai_portfolio_md, p_meta = build_ai_triple_markdown_reports(
    now_str, macro_info, df, macro_news, sector_news, company_news, p_state_active
)

ok, msg = push_to_google_drive_webhook(
    ai_quant_md, ai_news_md, webhook_url, ai_portfolio_md, p_meta["state_json_str"]
)

if ok:
    st.success(f"{msg} ({now_str}) — [EOF 1-3 OK]. Avaa Gemini puhelimella ja käytä taitoa **@st0-osakesijoittaja-apex**!")
else:
    st.warning(f"🕒 Ladattu: {now_str} | Doc 1: {len(ai_quant_md)} m | Doc 2: {len(ai_news_md)} m | Doc 3: {len(ai_portfolio_md)} m | {msg}")

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

# SALKKULASKURIN PIKAMITTARIT & MOBIILIMUOKKAIN (ALGORITMI E PILVESSÄ)
p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("💼 Kokonaispääoma", f"{p_meta['total_equity_eur']:,.2f} €", f"Avoin PnL {p_meta['open_pnl_eur']:+,.0f} €")
p2.metric("📈 Unit-NAV (TWR)", f"{p_meta['unit_nav']:.4f} €", f"{p_meta['twr_pct']:+.2f} % vs ankkuri")
p3.metric("💶 Vapaa Sijoituskassa", f"{p_meta['free_dry_powder_eur']:,.2f} €", f"Käteinen yht. {p_meta['cash_total_eur']:,.0f} €")
p4.metric("🎯 Myyntijono Netto", f"+{p_meta['pending_sells_net_eur']:,.2f} €", f"ANT-kassa {p_meta['free_dry_powder_eur']+p_meta['pending_sells_net_eur']:,.0f} €")
p5.metric("🔔 Aktiiviset Hälytykset", f"{len(p_meta['alerts_list'])} kpl", f"Tappiorivejä {len(p_meta['losing_recs'])} kpl")

with st.expander("💼 SALKKULASKURI, HÄLYTYKSET & MOBIILIMUOKKAUS (Algoritmi E — Tallentuu Driveen Doc 3)", expanded=False):
    ptab1, ptab2 = st.tabs(["📊 Live-Salkku, Hälytykset & Horizon-Shift", "✏️ Muokkaa Salkkua, Käteistä tai Pilkkejä Puhelimella"])
    with ptab1:
        if p_meta["alerts_list"]:
            st.markdown("#### 🔔 Lauenneet ja testissä olevat kurssihälytykset")
            for al_line in p_meta["alerts_list"]:
                st.markdown(al_line)
        if p_meta["sell_queue_lines"]:
            st.markdown("#### 🎯 Myyntijonon 1-suuntaiset nettokassalaskelmat & Exit Drift")
            for sq_line in p_meta["sell_queue_lines"]:
                st.markdown(sq_line)
        if p_meta["pos_records"]:
            st.markdown("#### 📋 11 Salkkuposition Reaaliaikainen Matriisi")
            pos_ui_df = pd.DataFrame([
                {
                    "Ticker": r["ticker"],
                    "Tase:Q:H": f"{r['bs']}:{r['q_tier']}:{r['sleeve']}",
                    "Kpl": int(r["shares"]),
                    "Kh": round(r["avg_price"], 2),
                    "Live": f"{r['live_price']:.2f} {r['ccy']} ({r['chg_1d']:+.2f}%)",
                    "Arvo €": round(r["val_eur"], 0),
                    "Paino %": round(r["weight_pct"], 2),
                    "PnL €": round(r["pnl_eur"], 0),
                    "PnL %": round(r["pnl_pct"], 2),
                    "Arvostus": r["val_dna"],
                    "Tuki (Et.)": f"{r['sup_str']} ({r['dist_sup_pct']:+.1f}%)",
                    "Dyn Trim": r["trim_str"],
                    "Signaali": r["signal"],
                }
                for r in p_meta["pos_records"]
            ])
            st.dataframe(pos_ui_df, use_container_width=True, hide_index=True)
    with ptab2:
        st.caption("Muokkaa salkun kappalemääriä, keskihintoja, käteissaldoja tai myyntipilkkejä suoraan puhelimella. Kun painat **Tallenna Pilveen**, muutokset tallentuvat Google Driveen (`Doc 3` + Apps Script -muisti).")
        c_col1, c_col2, c_col3 = st.columns(3)
        new_cash_ost = c_col1.number_input("OST Käteinen (EUR)", value=float(p_state_active.get("cash_ost_eur", 8797.12)), step=50.0, format="%.2f")
        new_cash_aot = c_col2.number_input("AOT Käteinen (EUR)", value=float(p_state_active.get("cash_aot_eur", 10.00)), step=10.0, format="%.2f")
        new_housing = c_col3.number_input("Asuntovaraus (EUR)", value=float(p_state_active.get("housing_reservation_eur", 4000.00)), step=100.0, format="%.2f")

        st.markdown("**Osakepositiot (muokkaa Kpl, Kh tai Horisontti):**")
        edited_pos_df = st.data_editor(
            pd.DataFrame(p_state_active.get("positions", [])),
            use_container_width=True,
            num_rows="dynamic",
            key="mobile_pos_editor"
        )
        st.markdown("**Aktiiviset Myynti-/Ostopilkit (`01`):**")
        edited_ord_df = st.data_editor(
            pd.DataFrame(p_state_active.get("orders", [])),
            use_container_width=True,
            num_rows="dynamic",
            key="mobile_ord_editor"
        )
        if st.button("💾 Tallenna Salkkumuutokset & Päivitä Kaikki 3 Drive-Dokumenttia", type="primary", use_container_width=True):
            updated_state = {
                **p_state_active,
                "cash_ost_eur": round(float(new_cash_ost), 2),
                "cash_aot_eur": round(float(new_cash_aot), 2),
                "housing_reservation_eur": round(float(new_housing), 2),
                "positions": edited_pos_df.to_dict(orient="records"),
                "orders": edited_ord_df.to_dict(orient="records"),
            }
            st.session_state["portfolio_state"] = updated_state
            q_md2, n_md2, p_md2, p_meta2 = build_ai_triple_markdown_reports(
                now_str, macro_info, df, macro_news, sector_news, company_news, updated_state
            )
            ok2, msg2 = push_to_google_drive_webhook(
                q_md2, n_md2, webhook_url, p_md2, p_meta2["state_json_str"]
            )
            if ok2:
                st.success(f"Salkkumuutokset tallennettu pilveen! {msg2}")
            else:
                st.warning(f"Tallennettu istuntoon ({msg2})")

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

with st.expander(
    f"📋 TARKISTA AI-SYÖTTEET (Doc 1 Quant: {len(ai_quant_md)} m | Doc 2 News: {len(ai_news_md)} m | Doc 3 Portfolio: {len(ai_portfolio_md)} m)",
    expanded=not ok
):
    t1, t2, t3 = st.tabs([
        "📊 Doc 1: ST0_LIVE_MARKET_FEED",
        "📰 Doc 2: ST0_LIVE_NEWS_FEED",
        "💼 Doc 3: ST0_LIVE_PORTFOLIO_QUANT (Algoritmi E)"
    ])
    with t1:
        st.code(ai_quant_md, language="markdown")
    with t2:
        st.code(ai_news_md, language="markdown")
    with t3:
        st.code(ai_portfolio_md, language="markdown")

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
