import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone
import pytz

# ==========================================
# SIVUN ASETUKSET
# ==========================================
st.set_page_config(
    page_title="ST0 Market Scout v3.5",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# YHTIÖANKKURIT, TASELUOKAT (FORT/SELF/DEBT) & TIER-PROFIILIT (21 KOHDETTA — APEX v7.0.2)
# ==========================================
TICKERS = {
    # KORI 1: Core Compounders
    "GOOG":    {"yf": ["GOOG"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "FORT", "dna_ma": 200, "kw": ["alphabet", "google", "waymo", "gemini", "tpu", "youtube", "sundar", "doj"]},
    "AMZN":    {"yf": ["AMZN"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "SELF", "dna_ma": 100, "kw": ["amazon", "aws", "amzn", "jassy", "prime", "trainium", "anthropic"]},
    "TTWO":    {"yf": ["TTWO"],          "bucket": "K1:Core",  "tier": "CYC",  "bs": "SELF", "dna_ma": 200, "kw": ["take-two", "gta", "rockstar", "ttwo", "zynga", "2k"]},
    "AAPL":    {"yf": ["AAPL"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "FORT", "dna_ma": 200, "kw": ["apple", "iphone", "ipad", "mac", "tim cook", "aapl", "foxconn"]},
    "META":    {"yf": ["META"],          "bucket": "K1:Core",  "tier": "CORE", "bs": "FORT", "dna_ma": 100, "kw": ["meta", "zuckerberg", "instagram", "whatsapp", "llama", "threads"]},
    # KORI 2: AI & Semi Stack
    "AVGO":    {"yf": ["AVGO"],          "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "dna_ma": 50,  "kw": ["broadcom", "avgo", "vmware", "hock tan", "custom chip", "xpu", "tomahawk"]},
    "NVDA":    {"yf": ["NVDA"],          "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "dna_ma": 50,  "kw": ["nvidia", "nvda", "blackwell", "rubin", "jensen", "kress", "colette", "geforce", "cuda"]},
    "AMD":     {"yf": ["AMD"],           "bucket": "K2:Semi",  "tier": "BETA", "bs": "SELF", "dna_ma": 200, "kw": ["amd", "advanced micro", "lisa su", "instinct", "epyc", "ryzen"]},
    "MU":      {"yf": ["MU"],            "bucket": "K2:Semi",  "tier": "CYC",  "bs": "FORT", "dna_ma": 100, "kw": ["micron", "hbm", "dram", "nand", "sanjay", "memory"]},
    "TSM":     {"yf": ["TSM"],           "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "dna_ma": 50,  "kw": ["tsmc", "taiwan semi", "cowos", "foundry", "wafer"]},
    "ASML":    {"yf": ["ASML"],          "bucket": "K2:Semi",  "tier": "CORE", "bs": "FORT", "dna_ma": 200, "kw": ["asml", "euv", "lithography", "fouquet", "bookings", "soxx"]},
    # KORI 3: High-Beta & Frontier
    "SPCX":    {"yf": ["SPCX", "DXYZ"],  "bucket": "K3:Beta",  "tier": "CYC",  "bs": "DEBT", "dna_ma": 50,  "kw": ["spacex", "starlink", "starship", "falcon", "spcx", "dxyz"]},
    "MSTR":    {"yf": ["MSTR"],          "bucket": "K3:Beta",  "tier": "CYC",  "bs": "DEBT", "dna_ma": 50,  "kw": ["microstrategy", "strategy", "saylor", "mstr", "msci"]},
    # KORI 4: Suomi / EUR
    "WRT1V":   {"yf": ["WRT1V.HE"],      "bucket": "K4:Suomi", "tier": "CORE", "bs": "FORT", "dna_ma": 100, "kw": ["wärtsilä", "wartsila", "agnevall", "marine", "energy storage", "engine"]},
    "FRAMERY": {"yf": ["FRAMERY.HE"],    "bucket": "K4:Suomi", "tier": "CYC",  "bs": "SELF", "dna_ma": 50,  "kw": ["framery", "hlt", "office pod"]},
    # SEURANTALISTA (Watchlist)
    "ANET":    {"yf": ["ANET"],          "bucket": "WATCH",    "tier": "CORE", "bs": "FORT", "dna_ma": 50,  "kw": ["arista", "anet", "ethernet", "switch", "ullal", "networking"]},
    "KLAC":    {"yf": ["KLAC"],          "bucket": "WATCH",    "tier": "CORE", "bs": "FORT", "dna_ma": 100, "kw": ["kla", "klac", "metrology", "inspection", "wafer", "wallace"]},
    "NBIS":    {"yf": ["NBIS"],          "bucket": "WATCH",    "tier": "CYC",  "bs": "DEBT", "dna_ma": 50,  "kw": ["nebius", "nbis", "arkady", "toloka", "avride"]},
    "NOKIA":   {"yf": ["NOKIA.HE"],      "bucket": "WATCH",    "tier": "CYC",  "bs": "SELF", "dna_ma": 200, "kw": ["nokia", "lundmark", "hotard", "infinera", "5g", "telecom"]},
    "BTC-USD": {"yf": ["BTC-USD"],       "bucket": "WATCH",    "tier": "BTC",  "bs": "DEBT", "dna_ma": 50,  "kw": ["bitcoin", "btc", "crypto", "ibit", "etf"]},
    "TSLA":    {"yf": ["TSLA"],          "bucket": "WATCH",    "tier": "BETA", "bs": "SELF", "dna_ma": 200, "kw": ["tesla", "tsla", "musk", "cybercab", "robotaxi", "megapack", "fsd"]},
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
    "these 3 stocks", "3 stocks", "2 stocks", "top stocks", "stocks to watch"
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

def is_clean_headline(title):
    if not title or len(title) < 15:
        return False
    t_low = title.lower()
    return not any(bad in t_low for bad in NOISE_PHRASES)

def is_fresh_news(item, now_dt, max_hours=96.0):
    try:
        pub_ts = item.get("providerPublishTime")
        if pub_ts:
            age_h = (now_dt.timestamp() - float(pub_ts)) / 3600.0
            return -2.0 <= age_h <= max_hours
        pub_str = item.get("content", {}).get("pubDate") or item.get("content", {}).get("displayTime")
        if pub_str:
            pub_dt = datetime.fromisoformat(str(pub_str).replace("Z", "+00:00"))
            age_h = (now_dt.astimezone(timezone.utc) - pub_dt.astimezone(timezone.utc)).total_seconds() / 3600.0
            return -2.0 <= age_h <= max_hours
    except Exception:
        pass
    return True

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

    # TUOREET MAKRO- & SEKTORIUUTISET (96h ikäraja)
    for name in MACRO_NEWS_PRIORITY:
        if len(macro_news) >= 3:
            break
        t_obj = macro_objs.get(name)
        if not t_obj:
            continue
        try:
            raw_m_news = t_obj.news or []
            added_for_src = 0
            for item in raw_m_news[:6]:
                title = item.get("title") or item.get("content", {}).get("title", "")
                if is_clean_headline(title) and is_fresh_news(item, now_dt, 96.0) and title not in seen_titles:
                    seen_titles.add(title)
                    macro_news.append(f"- MAKRO ({name}): {title[:115]}")
                    added_for_src += 1
                    if added_for_src >= 2 or len(macro_news) >= 3:
                        break
        except Exception:
            pass

    for name in SECTOR_NEWS_PRIORITY:
        if len(sector_news) >= 3:
            break
        t_obj = macro_objs.get(name)
        if not t_obj:
            continue
        try:
            raw_s_news = t_obj.news or []
            added_for_src = 0
            for item in raw_s_news[:6]:
                title = item.get("title") or item.get("content", {}).get("title", "")
                if is_clean_headline(title) and is_fresh_news(item, now_dt, 96.0) and title not in seen_titles:
                    seen_titles.add(title)
                    sector_news.append(f"- SEKTORI ({name}): {title[:115]}")
                    added_for_src += 1
                    if added_for_src >= 2 or len(sector_news) >= 3:
                        break
        except Exception:
            pass

    # 2. YHTIÖDATA + TASELUOKITUS + KORJATTU F:P/E + U-CURVE pRVOL
    rows = []
    company_news = []

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
            val_str = "-"
            quality_human_str = "- / - / -"
            quality_ai_str = f"-/-/-/{bs_tier}"
            bs_human_str = BS_HUMAN_LABELS.get(bs_tier, bs_tier)
            next_q_str = "-"
            earnings_soon = False
            op_m_val = None
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

                if f_pe_valid:
                    parts.append(f"F:{round(float(f_pe),1)}x")
                if t_pe and 2.0 < float(t_pe) < 250.0 and (not f_pe_valid or not valid_ev):
                    parts.append(f"T:{round(float(t_pe),1)}x")

                if valid_ev:
                    parts.append(f"EV:{round(float(ev_ebitda),1)}x")
                elif valid_pb and len(parts) < 2:
                    parts.append(f"PB:{round(float(pb),1)}x")

                if parts:
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

                nc_tag_ai = bs_tier
                nc_tag_human = BS_HUMAN_LABELS.get(bs_tier, bs_tier)
                if (t_cash is not None or t_debt is not None) and mcap and float(mcap) > 0 and same_currency:
                    net_c_pct = ((float(t_cash or 0.0) - float(t_debt or 0.0)) / float(mcap)) * 100.0
                    if -150.0 < net_c_pct < 100.0:
                        nc_int = int(round(net_c_pct))
                        nc_tag_ai = f"{bs_tier}({nc_int:+d}%)"
                        nc_tag_human = f"{BS_HUMAN_LABELS.get(bs_tier, bs_tier)} ({nc_int:+d}%)"

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

            rows.append({
                "Ticker": ticker_disp,
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
                "Signaali": status_flag
            })

            try:
                raw_news = t.news
                if raw_news:
                    keywords = cfg.get("kw", [sym.lower()])
                    max_news_age_h = 336.0 if ".HE" in used_yf else 168.0
                    matched_title = None
                    for item in raw_news[:8]:
                        title = item.get("title") or item.get("content", {}).get("title", "")
                        if is_clean_headline(title) and is_fresh_news(item, now_dt, max_news_age_h) and title not in seen_titles:
                            t_low = title.lower()
                            if any(k in t_low for k in keywords):
                                matched_title = title
                                break
                    if matched_title:
                        seen_titles.add(matched_title)
                        company_news.append(f"- **{sym}:** {matched_title[:115]}")
            except Exception:
                pass

        except Exception:
            continue

    df = pd.DataFrame(rows)
    return now_str, macro_info, df, macro_news, sector_news, company_news

# ==========================================
# MOOTTORI 1: 100 % AI-OPTIMOITU MARKDOWN GOOGLE DRIVEEN (TIIVIS, NOLLA EMOJIA)
# ==========================================
def format_ai_md_table(sub_df):
    if sub_df.empty:
        return "Ei kohteita.\n"
    header = "| Ticker | Kori | Hinta | Ses | Muutos | Low-High | pRVOL | 52w% | Arvostus | Rev/OpM/FCF/Tase | RSI | SMA50 | SMA200 | ADR | RS(1d/20d) | Dyn Tuki | Dyn Trim | Q-Tila | Signaali |\n"
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = ""
    for _, r in sub_df.iterrows():
        body += (
            f"| {r['Ticker']} | {r['Kori']} | {r['Hinta']} | {r['Sessio']} | {r['Muutos %']}% | {r['Day Low-High']} | {r['pRVOL']} | "
            f"{r['52w %']}% | {r['Arvostus']} | {r['Rev/OpM/FCF/Tase']} | {r['RSI(14)']} | {r['SMA50%']}% | "
            f"{r['SMA200%']}% | {r['ADR%']}% | {r['RS(1d/20d)']} | {r['Dyn Tuki']} | {r['Dyn Trim']} | {r['Q-Tila']} | {r['Signaali']} |\n"
        )
    return header + sep + body

def build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news):
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

    vxn_str = f"{vxn.get('price', 0.0):.2f} ({vxn.get('chg_pct', 0.0):+.2f}%)" if vxn.get("price", 0.0) > 0 else "N/A"
    active_df = df[df["Signaali"] != "OK"] if not df.empty else pd.DataFrame()
    inactive_df = df[df["Signaali"] == "OK"] if not df.empty else pd.DataFrame()
    loaded_cnt = len(df)
    total_cnt = len(TICKERS)

    md = "# ST0_LIVE_MARKET_FEED — AI SCOUT REPORT (v3.5 DUAL-ENGINE — APEX v7.0.2)\n"
    md += f"AIKALEIMA: {now_str} (LIVE_USER_FEED: 0-3min)\n"
    md += (
        f"MAKRO, DISPERSIO & KORKOTILA: VIX: {vix.get('price', 0.0):.2f} ({vix.get('chg_pct', 0.0):+.2f}%) | "
        f"VXN: {vxn_str} | Semi-Spread(SMH-SPY): {semi_sp:+.2f}pp | "
        f"US10Y: {us10y.get('price', 0.0):.2f}% (1d {us10y.get('bps_1d', 0):+d}bps / 20d {us10y.get('bps_20d', 0):+d}bps => {rate_reg}) | "
        f"NQ-Fut(24h): {nq_f.get('chg_pct', 0.0):+.2f}% | ES-Fut(24h): {es_f.get('chg_pct', 0.0):+.2f}% | "
        f"SMH: 1d {smh.get('chg_pct', 0.0):+.2f}% / 20d {smh.get('chg_20d', 0.0):+.1f}% | "
        f"QQQ: 1d {qqq.get('chg_pct', 0.0):+.2f}% / 20d {qqq.get('chg_20d', 0.0):+.1f}% | "
        f"SPY: 1d {spy.get('chg_pct', 0.0):+.2f}% / 20d {spy.get('chg_20d', 0.0):+.1f}% | EUR/USD: {fx.get('price', 0.0):.3f}\n"
    )

    if macro_news or sector_news:
        md += "## 1. MAKRO- & SEKTORITUTKA (TOP-DOWN)\n"
        for mn in macro_news:
            md += f"{mn}\n"
        for sn in sector_news:
            md += f"{sn}\n"

    md += f"## 2. KOKO SALKKU & SEURANTALISTA ({total_cnt} KOHDETTA)\n"
    md += f"### A. AKTIIVISET SIGNAALIT & POIKKEAMAT ({len(active_df)} kpl)\n"
    md += format_ai_md_table(active_df)

    md += f"### B. EI AKTIIVISIA SIGNAALEJA — NEUTRAALIT ({len(inactive_df)} kpl)\n"
    md += format_ai_md_table(inactive_df)

    if company_news:
        md += "## 3. YHTIOKOHTAISET UUTISET (24H)\n"
        clean_c_news = [cn.replace("**", "") for cn in company_news[:21]]
        md += "\n".join(clean_c_news) + "\n"

    md += f"[EOF: {loaded_cnt}/{total_cnt} OK]\n"
    return md

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

def push_to_google_drive_webhook(markdown_text, webhook_url):
    if not webhook_url:
        return False, "Ei Webhook-URLia asetuksissa"
    try:
        resp = requests.post(webhook_url, json={"content": markdown_text}, timeout=10)
        if resp.status_code == 200 and "OK" in resp.text:
            return True, "✅ AI-optimoitu raportti päivitetty automaattisesti Google Driveen (ST0_LIVE_MARKET_FEED)!"
        return False, f"Webhook vastasi koodilla {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, f"Yhteysvirhe: {str(e)}"

# ==========================================
# KÄYTTÖLIITTYMÄ (UI) — IHMISEN OHJAAMO
# ==========================================
st.title("📡 ST0 Market Scout v3.5 — Salkun Live-Ohjaamo")
st.caption("Kaksijakoinen moottori: Google Driveen lähetetään 100 % AI-optimoitu v7.0.2-syöte, ja tämä sivu on muotoiltu nopeaan silmäilyyn.")

if st.button("🔄 Päivitä Live-Kurssit & Lähetä AI-Syöte Driveen", type="primary", use_container_width=True):
    st.cache_data.clear()

now_str, macro_info, df, macro_news, sector_news, company_news = fetch_all_market_data()
ai_report_md = build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news)

webhook_url = get_webhook_url()
ok, msg = push_to_google_drive_webhook(ai_report_md, webhook_url)

if ok:
    st.success(f"{msg} ({now_str}) — {len(ai_report_md)} merkkiä ([EOF: {len(df)}/{len(TICKERS)} OK]). Avaa Gemini ja käytä taitoa **@st0-osakesijoittaja-apex-v7-0-2**!")
else:
    st.warning(f"🕒 Ladattu: {now_str} | {msg}")

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

with st.expander("📋 VARAVAIHTOEHTO / TARKISTA AI-SYÖTE: Kopioi raaka AI-raportti leikepöydälle", expanded=not ok):
    st.code(ai_report_md, language="markdown")

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
