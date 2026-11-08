import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

# ==========================================
# SIVUN ASETUKSET
# ==========================================
st.set_page_config(
    page_title="ST0 Market Scout v2.9",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# TARKAT YHTIÖKOHTAISET UUTISANKKURIT (04_TICKER_DNA)
# ==========================================
TICKERS = {
    # KORI 1: Core Compounders
    "GOOG":    {"yf": ["GOOG"],          "bucket": "K1:Core",  "dna_ma": 200, "kw": ["alphabet", "google", "waymo", "gemini", "tpu", "youtube", "sundar", "doj"]},
    "TTWO":    {"yf": ["TTWO"],          "bucket": "K1:Core",  "dna_ma": 200, "kw": ["take-two", "gta", "rockstar", "ttwo", "zynga", "2k"]},
    "AAPL":    {"yf": ["AAPL"],          "bucket": "K1:Core",  "dna_ma": 200, "kw": ["apple", "iphone", "ipad", "mac", "tim cook", "aapl", "foxconn"]},
    "META":    {"yf": ["META"],          "bucket": "K1:Core",  "dna_ma": 100, "kw": ["meta", "zuckerberg", "instagram", "whatsapp", "llama", "threads"]},
    # KORI 2: AI & Semi Stack
    "AVGO":    {"yf": ["AVGO"],          "bucket": "K2:Semi",  "dna_ma": 50,  "kw": ["broadcom", "avgo", "vmware", "hock tan", "custom chip", "xpu"]},
    "NVDA":    {"yf": ["NVDA"],          "bucket": "K2:Semi",  "dna_ma": 50,  "kw": ["nvidia", "nvda", "blackwell", "rubin", "jensen", "geforce", "cuda"]},
    "NBIS":    {"yf": ["NBIS"],          "bucket": "K2:Semi",  "dna_ma": 50,  "kw": ["nebius", "nbis", "arkady", "toloka", "avride"]},
    "MU":      {"yf": ["MU"],            "bucket": "K2:Semi",  "dna_ma": 100, "kw": ["micron", "hbm", "dram", "nand", "sanjay", "memory"]},
    "TSM":     {"yf": ["TSM"],           "bucket": "K2:Semi",  "dna_ma": 50,  "kw": ["tsmc", "taiwan semi", "cowos", "foundry", "wafer"]},
    "ASML":    {"yf": ["ASML"],          "bucket": "K2:Semi",  "dna_ma": 200, "kw": ["asml", "euv", "lithography", "fouquet", "bookings"]},
    # KORI 3: High-Beta & Frontier
    "SPCX":    {"yf": ["SPCX", "DXYZ"],  "bucket": "K3:Beta",  "dna_ma": 50,  "kw": ["spacex", "starlink", "starship", "falcon", "spcx", "dxyz"]},
    "MSTR":    {"yf": ["MSTR"],          "bucket": "K3:Beta",  "dna_ma": 50,  "kw": ["microstrategy", "strategy", "saylor", "mstr"]},
    # KORI 4: Suomi / EUR
    "NOKIA":   {"yf": ["NOKIA.HE"],      "bucket": "K4:Suomi", "dna_ma": 200, "kw": ["nokia", "lundmark", "hotard", "infinera", "5g", "telecom"]},
    "WRT1V":   {"yf": ["WRT1V.HE"],      "bucket": "K4:Suomi", "dna_ma": 100, "kw": ["wärtsilä", "wartsila", "agnevall", "marine", "energy storage"]},
    "FRAMERY": {"yf": ["FRAMERY.HE"],    "bucket": "K4:Suomi", "dna_ma": 50,  "kw": ["framery", "hlt", "office pod"]},
    # SEURANTALISTA (Watchlist)
    "BTC-USD": {"yf": ["BTC-USD"],       "bucket": "WATCH",    "dna_ma": 50,  "kw": ["bitcoin", "btc", "crypto", "ibit", "etf"]},
    "AMZN":    {"yf": ["AMZN"],          "bucket": "WATCH",    "dna_ma": 100, "kw": ["amazon", "aws", "amzn", "jassy", "prime"]},
    "AMD":     {"yf": ["AMD"],           "bucket": "WATCH",    "dna_ma": 200, "kw": ["amd", "advanced micro", "lisa su", "instinct", "epyc", "ryzen"]},
    "ORCL":    {"yf": ["ORCL"],          "bucket": "WATCH",    "dna_ma": 100, "kw": ["oracle", "orcl", "ellison", "oci", "cerner"]},
    "TSLA":    {"yf": ["TSLA"],          "bucket": "WATCH",    "dna_ma": 200, "kw": ["tesla", "tsla", "musk", "cybercab", "robotaxi", "megapack", "fsd"]},
    "NESTE":   {"yf": ["NESTE.HE"],      "bucket": "WATCH",    "dna_ma": 200, "kw": ["neste", "malinen", "saf", "renewable diesel", "porvoo", "rotterdam"]},
}

MACRO_TICKERS = {
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "QQQ": "QQQ",
    "SMH": "SMH",
    "SPY": "SPY",
    "EURUSD": "EURUSD=X"
}

NOISE_PHRASES = [
    "stocks to buy", "stock to buy", "if you invested", "motley fool",
    "why this stock", "millionaire-maker", "retirees", "dividend stocks",
    "these 3 stocks", "3 stocks", "2 stocks", "top stocks", "stocks to watch"
]

# ==========================================
# WILDERIN VIRALLINEN RSI(14)
# ==========================================
def calc_wilder_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def is_clean_headline(title):
    if not title or len(title) < 15:
        return False
    t_low = title.lower()
    return not any(bad in t_low for bad in NOISE_PHRASES)

@st.cache_data(ttl=120)
def fetch_all_market_data():
    tz_fi = pytz.timezone("Europe/Helsinki")
    now_dt = datetime.now(tz_fi)
    now_str = now_dt.strftime("%d.%m.%Y klo %H:%M:%S EET")

    macro_info = {}
    qqq_chg_1d, qqq_chg_20d = 0.0, 0.0
    spy_chg_1d, spy_chg_20d = 0.0, 0.0
    seen_titles = set()
    macro_news = []
    sector_news = []

    # 1. MAKRODATA + 3 MAKROUUTISTA & 3 SEKTORIUUTISTA
    for name, yf_sym in MACRO_TICKERS.items():
        try:
            t = yf.Ticker(yf_sym)
            hist = t.history(period="3mo")
            if len(hist) >= 2:
                last_p = float(hist["Close"].iloc[-1])
                prev_p = float(hist["Close"].iloc[-2])
                chg_1d = ((last_p / prev_p) - 1) * 100
                chg_20d = ((last_p / float(hist["Close"].iloc[-21])) - 1) * 100 if len(hist) >= 21 else chg_1d
                macro_info[name] = {"price": round(last_p, 2), "chg_pct": round(chg_1d, 2), "chg_20d": round(chg_20d, 1)}
                if name == "QQQ":
                    qqq_chg_1d, qqq_chg_20d = chg_1d, chg_20d
                elif name == "SPY":
                    spy_chg_1d, spy_chg_20d = chg_1d, chg_20d

            raw_m_news = t.news
            if raw_m_news:
                for item in raw_m_news[:5]:
                    title = item.get("title") or item.get("content", {}).get("title", "")
                    if is_clean_headline(title) and title not in seen_titles:
                        seen_titles.add(title)
                        if name in ["SPY", "US10Y", "VIX"] and len(macro_news) < 3:
                            macro_news.append(f"- MAKRO ({name}): {title}")
                        elif name in ["SMH", "QQQ"] and len(sector_news) < 3:
                            sector_news.append(f"- SEKTORI ({name}): {title}")
        except Exception:
            macro_info[name] = {"price": 0.0, "chg_pct": 0.0, "chg_20d": 0.0}

    # 2. YHTIÖKOHTAINEN DATA + TARKAT YHTIÖUUTISET
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

            close_s = hist["Close"]
            vol_s = hist["Volume"]
            last_close = float(close_s.iloc[-1])
            prev_close = float(close_s.iloc[-2]) if len(close_s) >= 2 else last_close
            day_high = float(hist["High"].iloc[-1])
            day_low = float(hist["Low"].iloc[-1])
            high_52w = float(hist["High"].max())
            low_52w = float(hist["Low"].min())
            low_60d = float(hist["Low"].tail(60).min())

            avg_vol_20 = float(vol_s.tail(21).iloc[:-1].mean()) if len(vol_s) >= 21 else float(vol_s.mean())
            last_vol = float(vol_s.iloc[-1])
            rvol = round(last_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0

            live_price = last_close
            market_session = "CLS"
            val_str = "-"
            quality_str = "- / - / -"
            next_q_str = "-"
            earnings_soon = False

            try:
                fast = t.info
                pre_p = fast.get("preMarketPrice")
                post_p = fast.get("postMarketPrice")
                curr_p = fast.get("currentPrice") or fast.get("regularMarketPrice")
                reg_prev = fast.get("regularMarketPreviousClose") or prev_close

                info_low = fast.get("dayLow") or fast.get("regularMarketDayLow")
                info_high = fast.get("dayHigh") or fast.get("regularMarketDayHigh")
                if info_low and float(info_low) > 0:
                    day_low = float(info_low)
                if info_high and float(info_high) > 0:
                    day_high = float(info_high)

                if pre_p and pre_p > 0:
                    live_price = float(pre_p)
                    prev_close = float(last_close)
                    market_session = "PRE"
                elif post_p and post_p > 0 and abs(float(post_p) - last_close) / last_close > 0.0005:
                    live_price = float(post_p)
                    prev_close = float(reg_prev)
                    market_session = "AH"
                elif curr_p and curr_p > 0:
                    live_price = float(curr_p)
                    prev_close = float(reg_prev)

                day_low = min(day_low, live_price)
                day_high = max(day_high, live_price)

                # 1. ZERO-ILLUSION ARVOSTUSSUODATIN
                t_pe = fast.get("trailingPE")
                f_pe = fast.get("forwardPE")
                ev_ebitda = fast.get("enterpriseToEbitda")
                pb = fast.get("priceToBook")
                curr_code = fast.get("currency", "USD")
                fin_curr = fast.get("financialCurrency", curr_code)

                same_currency = (curr_code == fin_curr)
                valid_ev = (ev_ebitda is not None and 2.0 < float(ev_ebitda) < 150.0 and same_currency)
                valid_pb = (pb is not None and 0.2 < float(pb) < 35.0 and same_currency)

                parts = []
                f_pe_valid = False
                if f_pe and 4.0 < float(f_pe) < 200.0:
                    f_val = float(f_pe)
                    if t_pe and float(t_pe) > 0 and f_val < float(t_pe) * 0.45 and f_val < 16.0:
                        f_pe_valid = False
                    elif valid_ev and f_val < float(ev_ebitda) * 0.60 and f_val < 16.0:
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

                # 2. P.8 LAATU- JA KASSAVIRTAMITTARIT (Vakio 3-paikkainen: Rev% / OpM% / FCF%)
                rev_g = fast.get("revenueGrowth")
                op_m = fast.get("operatingMargins")
                fcf = fast.get("freeCashflow")
                mcap = fast.get("marketCap")

                rev_s = f"{round(float(rev_g) * 100, 1)}%" if rev_g is not None else "-"
                opm_s = f"{round(float(op_m) * 100, 1)}%" if (op_m is not None and -2.0 < float(op_m) < 1.0) else "-"
                fcf_s = "-"
                if fcf is not None and mcap and float(mcap) > 0 and same_currency:
                    fcf_yield = (float(fcf) / float(mcap)) * 100.0
                    if -50.0 < fcf_yield < 50.0:
                        fcf_s = f"{round(fcf_yield, 1)}%"

                quality_str = f"{rev_s}/{opm_s}/{fcf_s}"

                # 3. TULOSKALENTERIN AIKASUODATIN
                e_ts = fast.get("earningsTimestamp") or fast.get("earningsTimestampStart")
                if e_ts:
                    e_dt = datetime.fromtimestamp(int(e_ts), tz=tz_fi)
                    days_diff = (e_dt.date() - now_dt.date()).days
                    date_fmt = e_dt.strftime("%d.%m")
                    if 0 <= days_diff <= 7:
                        next_q_str = f"⚠️{date_fmt}({days_diff}d)"
                        earnings_soon = True
                    elif days_diff > 7:
                        next_q_str = f"📅{date_fmt}({days_diff}d)"
                    else:
                        next_q_str = f"✅{date_fmt}"
            except Exception:
                pass

            chg_1d = ((live_price / prev_close) - 1) * 100
            chg_20d = ((live_price / float(close_s.iloc[-21])) - 1) * 100 if len(close_s) >= 21 else chg_1d
            dd_52w_pct = ((live_price / high_52w) - 1) * 100
            rsi_val = float(calc_wilder_rsi(close_s).iloc[-1]) if len(close_s) >= 15 else 50.0

            sma20 = float(close_s.rolling(20).mean().iloc[-1])
            std20 = float(close_s.rolling(20).std().iloc[-1])
            lower_bb = max(0.01, sma20 - 2.0 * std20)
            upper_bb = sma20 + 2.0 * std20

            sma50 = float(close_s.rolling(50).mean().iloc[-1]) if len(close_s) >= 50 else last_close
            sma100 = float(close_s.rolling(100).mean().iloc[-1]) if len(close_s) >= 100 else last_close
            sma200 = float(close_s.rolling(200).mean().iloc[-1]) if len(close_s) >= 200 else last_close

            dist_sma50 = ((live_price / sma50) - 1) * 100
            dist_sma200 = ((live_price / sma200) - 1) * 100
            adr_pct = float(((hist["High"] - hist["Low"]) / hist["Low"] * 100).tail(14).mean())

            bench_1d = spy_chg_1d if ".HE" in used_yf else qqq_chg_1d
            bench_20d = spy_chg_20d if ".HE" in used_yf else qqq_chg_20d
            rs_1d = round(chg_1d - bench_1d, 2)
            rs_20d = round(chg_20d - bench_20d, 1)

            # EHDOTON TUKITASOLUKKO (Dyn Tuki on AINA <= nykyhinta!)
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

            above_resistances = [val for _, val in [("SMA50", sma50), ("SMA200", sma200), ("BB-High", upper_bb), ("52w-High", high_52w)] if val >= live_price * 1.03]
            dyn_trim = round(min(above_resistances) if above_resistances else live_price * (1.0 + (2.0 * adr_pct / 100.0)), 2)

            dist_to_support_pct = ((live_price / dyn_support) - 1) * 100
            status_flag = "OK"

            if rsi_val <= 34.0:
                status_flag = f"🟢 YLIMYYTY (RSI {round(rsi_val,1)})"
            elif 0.0 <= dist_to_support_pct <= 2.8 and rsi_val <= 46.0:
                status_flag = f"🟢 TESTAA {support_type}"
            elif rsi_val >= 72.0:
                status_flag = f"🟠 YLIOSTETTU (RSI {round(rsi_val,1)})"
            elif abs(chg_1d) >= 5.0:
                vol_tag = f" RVOL:{rvol}x" if rvol >= 1.3 else ""
                status_flag = f"⚡ LIIKE {round(chg_1d,1)}%{vol_tag}"
            elif rs_1d >= 3.0 and chg_1d > 0:
                status_flag = f"💪 RS-LEAD (+{round(rs_1d,1)}%)"

            if earnings_soon:
                status_flag = f"⚠️ TULOS {next_q_str}" if status_flag == "OK" else f"{status_flag} ⚠️Q!"

            day_range_str = f"{round(day_low, 2)}–{round(day_high, 2)}"

            rows.append({
                "Ticker": sym if used_yf == sym or ".HE" in used_yf else f"{sym}({used_yf})",
                "Kori": cfg["bucket"],
                "Hinta": round(live_price, 2),
                "Sessio": market_session,
                "Muutos %": round(chg_1d, 2),
                "Day Low–High": day_range_str,
                "RVOL": f"{rvol}x",
                "52w %": round(dd_52w_pct, 1),
                "Arvostus (F/T/EV)": val_str,
                "Rev% / OpM% / FCF%": quality_str,
                "RSI(14)": round(rsi_val, 1),
                "SMA50%": round(dist_sma50, 1),
                "SMA200%": round(dist_sma200, 1),
                "ADR%": round(adr_pct, 1),
                "RS (1d/20d)": f"{rs_1d}%/{rs_20d}%",
                "Dyn Tuki": f"{dyn_support} ({support_type})",
                "Dyn Trim": dyn_trim,
                "Q-Tila": next_q_str,
                "Signaali": status_flag
            })

            try:
                raw_news = t.news
                if raw_news:
                    keywords = cfg.get("kw", [sym.lower()])
                    matched_title = None
                    for item in raw_news[:8]:
                        title = item.get("title") or item.get("content", {}).get("title", "")
                        if is_clean_headline(title) and title not in seen_titles:
                            t_low = title.lower()
                            if any(k in t_low for k in keywords):
                                matched_title = title
                                break
                    if matched_title:
                        seen_titles.add(matched_title)
                        company_news.append(f"- {sym}: {matched_title}")
            except Exception:
                pass

        except Exception:
            continue

    df = pd.DataFrame(rows)
    return now_str, macro_info, df, macro_news, sector_news, company_news

def format_md_table(sub_df):
    if sub_df.empty:
        return "Ei kohteita.\n\n"
    header = "| Ticker | Kori | Hinta | Ses | Muutos | Low–High | RVOL | 52w% | Arvostus | Rev/OpM/FCF | RSI | SMA50 | SMA200 | ADR | RS(1d/20d) | Dyn Tuki | Dyn Trim | Q-Tila | Signaali |\n"
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = ""
    for _, r in sub_df.iterrows():
        body += (
            f"| {r['Ticker']} | {r['Kori']} | {r['Hinta']} | {r['Sessio']} | {r['Muutos %']}% | {r['Day Low–High']} | {r['RVOL']} | "
            f"{r['52w %']}% | {r['Arvostus (F/T/EV)']} | {r['Rev% / OpM% / FCF%']} | {r['RSI(14)']} | {r['SMA50%']}% | "
            f"{r['SMA200%']}% | {r['ADR%']}% | {r['RS (1d/20d)']} | {r['Dyn Tuki']} | {r['Dyn Trim']} | {r['Q-Tila']} | {r['Signaali']} |\n"
        )
    return header + sep + body + "\n"

def build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news):
    vix = macro_info.get("VIX", {})
    us10y = macro_info.get("US10Y", {})
    qqq = macro_info.get("QQQ", {})
    smh = macro_info.get("SMH", {})
    spy = macro_info.get("SPY", {})
    fx = macro_info.get("EURUSD", {})

    active_df = df[df["Signaali"] != "OK"]
    inactive_df = df[df["Signaali"] == "OK"]

    md = f"# ST0_LIVE_MARKET_FEED — AI SCOUT REPORT (v2.9 MASTER)\n"
    md += f"AIKALEIMA: {now_str} (LIVE_USER_FEED: 0-3min)\n"
    md += (
        f"MAKRO & SEKTORIT: VIX: {vix.get('price')} ({vix.get('chg_pct')}%) | "
        f"US10Y: {us10y.get('price')}% ({us10y.get('chg_pct')}%) | "
        f"SMH: 1d {smh.get('chg_pct')}% / 20d {smh.get('chg_20d')}% | "
        f"QQQ: 1d {qqq.get('chg_pct')}% / 20d {qqq.get('chg_20d')}% | "
        f"SPY: 1d {spy.get('chg_pct')}% | EUR/USD: {fx.get('price')}\n\n"
    )

    if macro_news or sector_news:
        md += "## 1. MAKRO- & SEKTORITUTKA (TOP-DOWN)\n"
        for mn in macro_news:
            md += f"{mn}\n"
        for sn in sector_news:
            md += f"{sn}\n"
        md += "\n"

    md += f"## 2. KOKO SALKKU & SEURANTALISTA (21 KOHDETTA)\n"
    md += f"### 🚨 A. AKTIIVISET SIGNAALIT & POIKKEAMAT ({len(active_df)} kpl)\n"
    md += format_md_table(active_df)

    md += f"### 🟢 B. EI AKTIIVISIA SIGNAALEJA — NEUTRAALIT ({len(inactive_df)} kpl)\n"
    md += format_md_table(inactive_df)

    if company_news:
        md += "## 3. YHTIÖKOHTAISET UUTISET (24H)\n"
        md += "\n".join(company_news[:21]) + "\n"

    return md

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
            return True, "✅ Tiedot päivitetty automaattisesti Google Driveen (ST0_LIVE_MARKET_FEED)!"
        return False, f"Webhook vastasi koodilla {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, f"Yhteysvirhe: {str(e)}"

# ==========================================
# KÄYTTÖLIITTYMÄ (UI)
# ==========================================
st.title("📡 ST0 Market Scout v2.9 (Zero-Truncation Master PWA)")

if st.button("🔄 Päivitä Live-Kurssit & Lähetä Driveen", type="primary", use_container_width=True):
    st.cache_data.clear()

now_str, macro_info, df, macro_news, sector_news, company_news = fetch_all_market_data()
ai_report_md = build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news)

webhook_url = get_webhook_url()
ok, msg = push_to_google_drive_webhook(ai_report_md, webhook_url)

if ok:
    st.success(f"{msg} ({now_str}) — Koko: {len(ai_report_md)} merkkiä (~1650 merkin turvamarginaali Drive-rajaan!). Voit nyt avata Gemin ja sanoa: **'Tee tilannepäivitys ja toimintasuunnitelma'**!")
else:
    st.warning(f"🕒 Ladattu: {now_str} | {msg}")

with st.expander("📋 VARAVAIHTOEHTO: Kopioi raportti leikepöydälle (1 klikkaus oikeasta yläkulmasta)", expanded=not ok):
    st.code(ai_report_md, language="markdown")

active_df = df[df["Signaali"] != "OK"]
inactive_df = df[df["Signaali"] == "OK"]

st.header("📊 Koko Salkku & Seurantalista (21 kohdetta)")

st.subheader(f"🚨 1. Aktiiviset Signaalit ({len(active_df)} kpl)")
st.dataframe(active_df, use_container_width=True, hide_index=True)

st.subheader(f"🟢 2. Ei Aktiivisia Signaaleja ({len(inactive_df)} kpl)")
st.dataframe(inactive_df, use_container_width=True, hide_index=True)
