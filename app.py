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
    page_title="ST0 Market Scout v2.3",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# DYNAAMINEN KONFIGURAATIO & UUTISANKKURIT (04_TICKER_DNA)
# ==========================================
TICKERS = {
    # KORI 1: Core Compounders
    "GOOG":    {"yf": ["GOOG"],          "bucket": "KORI 1: Core",      "dna_ma": 200, "kw": ["alphabet", "google", "cloud", "waymo", "gemini", "tpu", "ai", "search", "doj"]},
    "TTWO":    {"yf": ["TTWO"],          "bucket": "KORI 1: Core",      "dna_ma": 200, "kw": ["take-two", "gta", "rockstar", "gaming", "ttwo", "game"]},
    "AAPL":    {"yf": ["AAPL"],          "bucket": "KORI 1: Core",      "dna_ma": 200, "kw": ["apple", "iphone", "ipad", "mac", "tim cook", "aapl", "china", "foxconn"]},
    "META":    {"yf": ["META"],          "bucket": "KORI 1: Core",      "dna_ma": 100, "kw": ["meta", "zuckerberg", "instagram", "whatsapp", "llama", "ai", "ad"]},
    # KORI 2: AI & Semi Stack
    "AVGO":    {"yf": ["AVGO"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 50,  "kw": ["broadcom", "avgo", "asic", "vmware", "hock tan", "chip", "ai"]},
    "NVDA":    {"yf": ["NVDA"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 50,  "kw": ["nvidia", "nvda", "blackwell", "rubin", "jensen", "gpu", "ai", "chip", "datacenter"]},
    "NBIS":    {"yf": ["NBIS"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 50,  "kw": ["nebius", "nbis", "gpu", "cloud", "ai", "data center", "datacenter"]},
    "MU":      {"yf": ["MU"],            "bucket": "KORI 2: AI/Semi",   "dna_ma": 100, "kw": ["micron", "hbm", "dram", "nand", "memory", "chip", "ai"]},
    "TSM":     {"yf": ["TSM"],           "bucket": "KORI 2: AI/Semi",   "dna_ma": 50,  "kw": ["tsmc", "taiwan semi", "foundry", "cowos", "wafer", "chip", "ai"]},
    "ASML":    {"yf": ["ASML"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 200, "kw": ["asml", "euv", "lithography", "chip", "semiconductor", "bookings"]},
    # KORI 3: High-Beta & Frontier
    "SPCX":    {"yf": ["SPCX", "DXYZ"],  "bucket": "KORI 3: High-Beta", "dna_ma": 50,  "kw": ["spacex", "starlink", "starship", "musk", "space", "rocket", "spcx"]},
    "MSTR":    {"yf": ["MSTR"],          "bucket": "KORI 3: High-Beta", "dna_ma": 50,  "kw": ["microstrategy", "strategy", "saylor", "bitcoin", "btc", "mstr"]},
    # KORI 4: Suomi / EUR
    "NOKIA":   {"yf": ["NOKIA.HE"],      "bucket": "KORI 4: Suomi",     "dna_ma": 200, "kw": ["nokia", "network", "5g", "optical", "telecom", "stock"]},
    "WRT1V":   {"yf": ["WRT1V.HE"],      "bucket": "KORI 4: Suomi",     "dna_ma": 100, "kw": ["wärtsilä", "wartsila", "marine", "energy", "engine", "power"]},
    "FRAMERY": {"yf": ["FRAMERY.HE"],    "bucket": "KORI 4: Suomi",     "dna_ma": 50,  "kw": ["framery", "pod", "office", "earnings", "q3", "q4"]},
    # SEURANTALISTA (Watchlist)
    "BTC-USD": {"yf": ["BTC-USD"],       "bucket": "WATCHLIST",         "dna_ma": 50,  "kw": ["bitcoin", "btc", "crypto", "etf", "halving", "fed"]},
    "AMZN":    {"yf": ["AMZN"],          "bucket": "WATCHLIST",         "dna_ma": 100, "kw": ["amazon", "aws", "amzn", "jassy", "cloud", "retail", "ai"]},
    "AMD":     {"yf": ["AMD"],           "bucket": "WATCHLIST",         "dna_ma": 200, "kw": ["amd", "advanced micro", "lisa su", "instinct", "epyc", "ryzen", "gpu", "ai"]},
    "ORCL":    {"yf": ["ORCL"],          "bucket": "WATCHLIST",         "dna_ma": 100, "kw": ["oracle", "orcl", "ellison", "oci", "cloud", "database", "ai"]},
    "TSLA":    {"yf": ["TSLA"],          "bucket": "WATCHLIST",         "dna_ma": 200, "kw": ["tesla", "tsla", "musk", "ev", "fsd", "robotaxi", "megapack", "cybercab"]},
    "NESTE":   {"yf": ["NESTE.HE"],      "bucket": "WATCHLIST",         "dna_ma": 200, "kw": ["neste", "renewable", "saf", "diesel", "refinery", "margin"]},
}

MACRO_TICKERS = {
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "QQQ": "QQQ",
    "SMH": "SMH",
    "SPY": "SPY",
    "EURUSD": "EURUSD=X"
}

# Klikkiotsikoiden suodatuslista (estää kohinan makro- ja sektoriuutisissa)
NOISE_PHRASES = [
    "stocks to buy", "stock to buy", "if you invested", "motley fool",
    "why this stock", "millionaire-maker", "retirees", "dividend stocks"
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
    now_str = datetime.now(tz_fi).strftime("%d.%m.%Y klo %H:%M:%S EET")

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

            # Poimitaan Makrouutiset (SPY / US10Y) ja Sektoriuutiset (SMH / QQQ)
            raw_m_news = t.news
            if raw_m_news:
                for item in raw_m_news[:5]:
                    title = item.get("title") or item.get("content", {}).get("title", "")
                    if is_clean_headline(title) and title not in seen_titles:
                        seen_titles.add(title)
                        if name in ["SPY", "US10Y", "VIX"] and len(macro_news) < 3:
                            macro_news.append(f"- **[MAKRO / {name}]:** {title}")
                        elif name in ["SMH", "QQQ"] and len(sector_news) < 3:
                            sector_news.append(f"- **[SEKTORI / {name}]:** {title}")
        except Exception:
            macro_info[name] = {"price": 0.0, "chg_pct": 0.0, "chg_20d": 0.0}

    # 2. YHTIÖKOHTAINEN DATA + UNIIKIT YHTIÖUUTISET
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
            low_60d = float(hist["Low"].tail(60).min())

            avg_vol_20 = float(vol_s.tail(21).iloc[:-1].mean()) if len(vol_s) >= 21 else float(vol_s.mean())
            last_vol = float(vol_s.iloc[-1])
            rvol = round(last_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0

            live_price = last_close
            market_session = "REG/CLOSE"
            val_str = "N/A"
            rev_gr_str = "N/A"
            try:
                fast = t.info
                pre_p = fast.get("preMarketPrice")
                post_p = fast.get("postMarketPrice")
                curr_p = fast.get("currentPrice") or fast.get("regularMarketPrice")
                reg_prev = fast.get("regularMarketPreviousClose") or prev_close

                if pre_p and pre_p > 0:
                    live_price = float(pre_p)
                    prev_close = float(last_close)
                    market_session = "PRE-MKT"
                elif post_p and post_p > 0 and abs(float(post_p) - last_close) / last_close > 0.0005:
                    live_price = float(post_p)
                    prev_close = float(reg_prev)
                    market_session = "AFTER-HRS"
                elif curr_p and curr_p > 0:
                    live_price = float(curr_p)
                    prev_close = float(reg_prev)

                # ARVOSTUSKERTOIMIEN SANITY CHECK (Estää rikkinäisen Fwd P/E -ansan)
                t_pe = fast.get("trailingPE")
                f_pe = fast.get("forwardPE")
                ev_ebitda = fast.get("enterpriseToEbitda")
                pb = fast.get("priceToBook")

                parts = []
                if f_pe and f_pe > 0:
                    if t_pe and t_pe > 0 and (f_pe < t_pe * 0.35 and f_pe < 15.0):
                        parts.append(f"PE:{round(float(t_pe),1)}x(T)")
                    else:
                        parts.append(f"Fwd:{round(float(f_pe),1)}x")
                elif t_pe and t_pe > 0:
                    parts.append(f"PE:{round(float(t_pe),1)}x(T)")

                if ev_ebitda and 0 < ev_ebitda < 150:
                    parts.append(f"EV/EB:{round(float(ev_ebitda),1)}x")
                elif pb and pb > 0 and not parts:
                    parts.append(f"PB:{round(float(pb),1)}x")

                if parts:
                    val_str = " | ".join(parts)

                rev_g = fast.get("revenueGrowth")
                if rev_g is not None:
                    rev_gr_str = f"{round(float(rev_g) * 100, 1)}%"
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

            candidates = [
                ("SMA50", sma50),
                ("SMA100", sma100),
                ("SMA200", sma200),
                ("BB-Low(2σ)", lower_bb),
                ("60d-Low", low_60d)
            ]
            below_supports = [(name, val) for name, val in candidates if val <= live_price * 1.015]
            if below_supports:
                support_type, dyn_support_raw = max(below_supports, key=lambda x: x[1])
                dyn_support = round(dyn_support_raw, 2)
            else:
                dyn_support = round(low_60d, 2)
                support_type = "60d-Low(Broken)"

            above_resistances = [val for _, val in [("SMA50", sma50), ("SMA200", sma200), ("BB-High", upper_bb), ("52w-High", high_52w)] if val >= live_price * 1.03]
            dyn_trim = round(min(above_resistances) if above_resistances else upper_bb, 2)

            dist_to_support_pct = ((live_price / dyn_support) - 1) * 100
            status_flag = "OK"

            if rsi_val <= 33.0:
                status_flag = f"🟢 RSI YLIMYYTY ({round(rsi_val,1)}) | Tuki: {dyn_support}"
            elif -1.5 <= dist_to_support_pct <= 2.5 and rsi_val <= 46.0:
                status_flag = f"🟢 TESTAA {support_type}-TUKEA ({dyn_support})"
            elif rsi_val >= 72.0:
                status_flag = f"🟠 RSI YLIOSTETTU ({round(rsi_val,1)}) | Trim: {dyn_trim}"
            elif abs(chg_1d) >= 5.0:
                vol_tag = f" [RVOL {rvol}x!]" if rvol >= 1.3 else ""
                status_flag = f"⚡ >5% LIIKE ({round(chg_1d,1)}%){vol_tag}"
            elif rs_1d >= 3.0 and chg_1d > 0:
                status_flag = f"💪 RS-JOHTAJA (1d: +{round(rs_1d,1)}% | 20d: {rs_20d}%)"

            rows.append({
                "Ticker": sym if used_yf == sym or ".HE" in used_yf else f"{sym} ({used_yf})",
                "Kori": cfg["bucket"],
                "Hinta": round(live_price, 2),
                "Sessio": market_session,
                "Muutos %": round(chg_1d, 2),
                "RVOL": f"{rvol}x",
                "52w Huipusta %": round(dd_52w_pct, 1),
                "Arvostus": val_str,
                "RevGr %": rev_gr_str,
                "RSI(14)": round(rsi_val, 1),
                "vs SMA50 %": round(dist_sma50, 1),
                "vs SMA200 %": round(dist_sma200, 1),
                "ADR %": round(adr_pct, 1),
                "RS (1d / 20d)": f"{rs_1d}% / {rs_20d}%",
                "Dyn Tuki": f"{dyn_support} ({support_type})",
                "Dyn Trim": dyn_trim,
                "Signaali": status_flag
            })

            # RELEVANSSISUODATETTU YHTIÖUUTISHAKU
            try:
                raw_news = t.news
                if raw_news:
                    keywords = cfg.get("kw", [sym.lower()])
                    matched_title = None
                    for item in raw_news[:6]:
                        title = item.get("title") or item.get("content", {}).get("title", "")
                        if is_clean_headline(title) and title not in seen_titles:
                            t_low = title.lower()
                            if any(k in t_low for k in keywords):
                                matched_title = title
                                break
                    if not matched_title:
                        for item in raw_news[:3]:
                            title = item.get("title") or item.get("content", {}).get("title", "")
                            if is_clean_headline(title) and title not in seen_titles:
                                matched_title = title
                                break
                    if matched_title:
                        seen_titles.add(matched_title)
                        company_news.append(f"- **{sym}:** {matched_title}")
            except Exception:
                pass

        except Exception:
            continue

    df = pd.DataFrame(rows)
    return now_str, macro_info, df, macro_news, sector_news, company_news

def build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news):
    vix = macro_info.get("VIX", {})
    us10y = macro_info.get("US10Y", {})
    qqq = macro_info.get("QQQ", {})
    smh = macro_info.get("SMH", {})
    spy = macro_info.get("SPY", {})
    fx = macro_info.get("EURUSD", {})

    md = f"# 📡 ST0_LIVE_MARKET_FEED — AI SCOUT REPORT (MACRO & ALPHA v2.3)\n"
    md += f"**AIKALEIMA:** `{now_str}` `[LIVE_USER_FEED: 0-3min]`\n"
    md += (
        f"**MAKRO & SEKTORIT:** `VIX: {vix.get('price')} ({vix.get('chg_pct')}%)` | "
        f"`US10Y Korko: {us10y.get('price')}% ({us10y.get('chg_pct')}%)` | "
        f"`SMH (Semi): 1d {smh.get('chg_pct')}% / 20d {smh.get('chg_20d')}%` | "
        f"`QQQ: 1d {qqq.get('chg_pct')}% / 20d {qqq.get('chg_20d')}%` | "
        f"`SPY: 1d {spy.get('chg_pct')}%` | `EUR/USD: {fx.get('price')}`\n\n"
    )

    if macro_news or sector_news:
        md += "## 🌍 MAKRO- & SEKTORITUTKA (TOP-DOWN CONTEXT)\n"
        for mn in macro_news:
            md += f"{mn}\n"
        for sn in sector_news:
            md += f"{sn}\n"
        md += "\n"

    alerts_df = df[df["Signaali"] != "OK"]
    if not alerts_df.empty:
        md += "## 🚨 AKTIIVISET SIGNAALIT & POIKKEAMAT\n"
        for _, r in alerts_df.iterrows():
            md += (
                f"- **{r['Ticker']} ({r['Hinta']} | {r['Muutos %']}% | RVOL: {r['RVOL']} | 52w: {r['52w Huipusta %']}% | {r['Arvostus']} | RevGr: {r['RevGr %']}):** "
                f"{r['Signaali']} | Wilder RSI: {r['RSI(14)']} | RS(1d/20d): {r['RS (1d / 20d)']} | Dyn Tuki: {r['Dyn Tuki']} | Dyn Trim: {r['Dyn Trim']}\n"
            )
        md += "\n"

    md += "## 📊 21 KOHTEEN FUNDAMENTTI-, VOLYYMI-, TEKNINEN & SUHTEELLINEN MATRIISI\n"
    md += "| Ticker | Kori | Hinta | Sessio | Muutos % | RVOL | 52w Huipusta | Arvostus | RevGr% | RSI(14) | vs SMA50% | vs SMA200% | ADR% | RS (1d / 20d) | Dyn Tuki | Dyn Trim | Signaali |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    for _, r in df.iterrows():
        md += (
            f"| **{r['Ticker']}** | {r['Kori']} | {r['Hinta']} | {r['Sessio']} | {r['Muutos %']}% | {r['RVOL']} | "
            f"{r['52w Huipusta %']}% | {r['Arvostus']} | {r['RevGr %']} | {r['RSI(14)']} | {r['vs SMA50 %']}% | "
            f"{r['vs SMA200 %']}% | {r['ADR %']}% | {r['RS (1d / 20d)']} | {r['Dyn Tuki']} | {r['Dyn Trim']} | {r['Signaali']} |\n"
        )

    if company_news:
        md += "\n## 📰 TUOREIMMAT YHTIÖKOHTAISET UUTISET (RELEVANSSISUODATETTU, 24H)\n"
        md += "\n".join(company_news[:18]) + "\n"

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
st.title("📡 ST0 Market Scout v2.3 (Macro, Sector & Alpha PWA)")

if st.button("🔄 Päivitä Live-Kurssit & Lähetä Driveen", type="primary", use_container_width=True):
    st.cache_data.clear()

now_str, macro_info, df, macro_news, sector_news, company_news = fetch_all_market_data()
ai_report_md = build_ai_markdown_report(now_str, macro_info, df, macro_news, sector_news, company_news)

webhook_url = get_webhook_url()
ok, msg = push_to_google_drive_webhook(ai_report_md, webhook_url)

if ok:
    st.success(f"{msg} ({now_str}) — Voit nyt avata Gemin ja sanoa: **'Tee tilannepäivitys ja toimintasuunnitelma'**!")
else:
    st.warning(f"🕒 Ladattu: {now_str} | {msg}")

with st.expander("📋 VARAVAIHTOEHTO: Kopioi raportti leikepöydälle (1 klikkaus oikeasta yläkulmasta)", expanded=not ok):
    st.code(ai_report_md, language="markdown")

st.subheader("🚨 Aktiiviset Signaalit")
st.dataframe(df[df["Signaali"] != "OK"], use_container_width=True, hide_index=True)

st.subheader("📊 Koko Salkku & Seurantalista (v2.3 Institutional Alpha Engine)")
st.dataframe(df, use_container_width=True, hide_index=True)
