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
    page_title="ST0 Market Scout v2.0",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# DYNAAMINEN KONFIGURAATIO (EI KOVAKOODATTUJA HINTOJA!)
# dna_ma = Osakkeen luontainen liukuva tukikeskiarvo (50, 100 tai 200 pv)
# ==========================================
TICKERS = {
    # KORI 1: Core Compounders
    "GOOG":    {"yf": ["GOOG"],          "bucket": "KORI 1: Core",      "dna_ma": 200},
    "TTWO":    {"yf": ["TTWO"],          "bucket": "KORI 1: Core",      "dna_ma": 200},
    "AAPL":    {"yf": ["AAPL"],          "bucket": "KORI 1: Core",      "dna_ma": 200},
    "META":    {"yf": ["META"],          "bucket": "KORI 1: Core",      "dna_ma": 100},
    # KORI 2: AI & Semi Stack
    "AVGO":    {"yf": ["AVGO"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 50},
    "NVDA":    {"yf": ["NVDA"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 50},
    "NBIS":    {"yf": ["NBIS"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 50},
    "MU":      {"yf": ["MU"],            "bucket": "KORI 2: AI/Semi",   "dna_ma": 100},
    "TSM":     {"yf": ["TSM"],           "bucket": "KORI 2: AI/Semi",   "dna_ma": 50},
    "ASML":    {"yf": ["ASML"],          "bucket": "KORI 2: AI/Semi",   "dna_ma": 200},
    # KORI 3: High-Beta & Frontier
    "SPCX":    {"yf": ["SPCX", "DXYZ"],  "bucket": "KORI 3: High-Beta", "dna_ma": 50},
    "MSTR":    {"yf": ["MSTR"],          "bucket": "KORI 3: High-Beta", "dna_ma": 50},
    # KORI 4: Suomi / EUR
    "NOKIA":   {"yf": ["NOKIA.HE"],      "bucket": "KORI 4: Suomi",     "dna_ma": 200},
    "WRT1V":   {"yf": ["WRT1V.HE"],      "bucket": "KORI 4: Suomi",     "dna_ma": 100},
    "FRAMERY": {"yf": ["FRAMERY.HE"],    "bucket": "KORI 4: Suomi",     "dna_ma": 50},
    # SEURANTALISTA (Watchlist)
    "BTC-USD": {"yf": ["BTC-USD"],       "bucket": "WATCHLIST",         "dna_ma": 50},
    "AMZN":    {"yf": ["AMZN"],          "bucket": "WATCHLIST",         "dna_ma": 100},
    "AMD":     {"yf": ["AMD"],           "bucket": "WATCHLIST",         "dna_ma": 200},
    "ORCL":    {"yf": ["ORCL"],          "bucket": "WATCHLIST",         "dna_ma": 100},
    "TSLA":    {"yf": ["TSLA"],          "bucket": "WATCHLIST",         "dna_ma": 200},
    "NESTE":   {"yf": ["NESTE.HE"],      "bucket": "WATCHLIST",         "dna_ma": 200},
}

MACRO_TICKERS = {"VIX": "^VIX", "QQQ": "QQQ", "SPY": "SPY", "EURUSD": "EURUSD=X"}

# ==========================================
# DYNAAMINEN TEKNINEN & TILASTOLLINEN MOOTTORI
# ==========================================
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=120)
def fetch_all_market_data():
    tz_fi = pytz.timezone("Europe/Helsinki")
    now_str = datetime.now(tz_fi).strftime("%d.%m.%Y klo %H:%M:%S EET")

    macro_info = {}
    qqq_chg = 0.0
    for name, yf_sym in MACRO_TICKERS.items():
        try:
            t = yf.Ticker(yf_sym)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                last_p = float(hist["Close"].iloc[-1])
                prev_p = float(hist["Close"].iloc[-2])
                chg = ((last_p / prev_p) - 1) * 100
                macro_info[name] = {"price": round(last_p, 2), "chg_pct": round(chg, 2)}
                if name == "QQQ":
                    qqq_chg = chg
        except Exception:
            macro_info[name] = {"price": 0.0, "chg_pct": 0.0}

    rows = []
    news_items = []

    for sym, cfg in TICKERS.items():
        try:
            # Automaattinen ticker-haku (kokeilee ensisijaista, sitten varatunnusta)
            t = None
            hist = pd.DataFrame()
            used_yf = cfg["yf"][0]
            for candidate in cfg["yf"]:
                temp_t = yf.Ticker(candidate)
                temp_h = temp_t.history(period="1y")
                if not temp_h.empty and len(temp_h) >= 5:
                    t = temp_t
                    hist = temp_h
                    used_yf = candidate
                    break
            if hist.empty:
                continue

            close_s = hist["Close"]
            last_close = float(close_s.iloc[-1])
            prev_close = float(close_s.iloc[-2]) if len(close_s) >= 2 else last_close
            day_high = float(hist["High"].iloc[-1])
            day_low = float(hist["Low"].iloc[-1])

            # Pre-Market / After-Hours / Live-hinta
            live_price = last_close
            market_session = "REG/CLOSE"
            try:
                fast = t.info
                pre_p = fast.get("preMarketPrice")
                post_p = fast.get("postMarketPrice")
                curr_p = fast.get("currentPrice") or fast.get("regularMarketPrice")
                if pre_p and pre_p > 0:
                    live_price = float(pre_p)
                    market_session = "PRE-MKT"
                elif post_p and post_p > 0:
                    live_price = float(post_p)
                    market_session = "AFTER-HRS"
                elif curr_p and curr_p > 0:
                    live_price = float(curr_p)
            except Exception:
                pass

            chg_pct = ((live_price / prev_close) - 1) * 100
            rsi_val = float(calc_rsi(close_s).iloc[-1]) if len(close_s) >= 15 else 50.0

            # Liukuvat keskiarvot & Bollinger-kanavat (20pv ± 2 keskihajontaa)
            sma20 = float(close_s.rolling(20).mean().iloc[-1]) if len(close_s) >= 20 else last_close
            std20 = float(close_s.rolling(20).std().iloc[-1]) if len(close_s) >= 20 else last_close * 0.05
            lower_bb = max(0.01, sma20 - 2.0 * std20)
            upper_bb = sma20 + 2.0 * std20

            sma50 = float(close_s.rolling(50).mean().iloc[-1]) if len(close_s) >= 50 else last_close
            sma100 = float(close_s.rolling(100).mean().iloc[-1]) if len(close_s) >= 100 else last_close
            sma200 = float(close_s.rolling(200).mean().iloc[-1]) if len(close_s) >= 200 else last_close

            dist_sma50 = ((live_price / sma50) - 1) * 100
            dist_sma200 = ((live_price / sma200) - 1) * 100
            adr_pct = float(((hist["High"] - hist["Low"]) / hist["Low"] * 100).tail(14).mean())
            rs_vs_qqq = chg_pct - qqq_chg

            # ==========================================
            # ITSEKALIBROITUVA DYNAAMINEN TUKI- JA KEVENNYSLASKENTA
            # ==========================================
            dna_ma_val = sma50 if cfg["dna_ma"] == 50 else (sma100 if cfg["dna_ma"] == 100 else sma200)

            # Jos kurssi on pääkeskiarvonsa yläpuolella, tuki on DNA-keskiarvo (tai SMA200);
            # jos kurssi on jo pudonnut keskiarvon alle, dynaaminen tuki on tilastollinen alakanava (Lower Bollinger 2σ)
            if live_price >= dna_ma_val:
                dyn_support = round(dna_ma_val, 2)
                support_type = f"SMA{cfg['dna_ma']}"
            elif live_price >= sma200:
                dyn_support = round(sma200, 2)
                support_type = "SMA200"
            else:
                dyn_support = round(min(lower_bb, live_price * (1 - adr_pct / 100.0)), 2)
                support_type = "BB-Low(2σ)"

            # Dynaaminen kevennystaso (Trim) = Tilastollinen yläkanava (Upper Bollinger 2σ) tai SMA50 vastus laskutrendissä
            dyn_trim = round(max(upper_bb, sma50 * 1.05), 2)

            # ==========================================
            # DYNAAMINEN SIGNAALILOGIIKKA (Ei vanhenevia rajoja)
            # ==========================================
            dist_to_support_pct = ((live_price / dyn_support) - 1) * 100
            status_flag = "OK"

            if rsi_val <= 33.0:
                status_flag = f"🟢 RSI YLIMYYTY ({round(rsi_val,1)}) + Tuki: {dyn_support}"
            elif 0 <= dist_to_support_pct <= 2.5 and rsi_val <= 45.0:
                status_flag = f"🟢 TESTAA {support_type}-TUKEA ({dyn_support})"
            elif rsi_val >= 73.0 or live_price >= dyn_trim:
                status_flag = f"🟠 DYN TRIM / YLIOSTETTU (Raja: {dyn_trim})"
            elif abs(chg_pct) >= 5.0:
                status_flag = f"⚡ >5% YLIREAKTIOLIIKE ({round(chg_pct,1)}%)"
            elif rs_vs_qqq >= 3.5 and chg_pct > 0:
                status_flag = f"💪 RS-JOHTAJA (+{round(rs_vs_qqq,1)}% vs QQQ)"

            rows.append({
                "Ticker": sym if used_yf == sym or ".HE" in used_yf else f"{sym} ({used_yf})",
                "Kori": cfg["bucket"],
                "Hinta": round(live_price, 2),
                "Tila": market_session,
                "Muutos %": round(chg_pct, 2),
                "Day Low": round(day_low, 2),
                "Day High": round(day_high, 2),
                "RSI(14)": round(rsi_val, 1),
                "vs SMA50 %": round(dist_sma50, 1),
                "vs SMA200 %": round(dist_sma200, 1),
                "ADR %": round(adr_pct, 1),
                "RS vs QQQ": round(rs_vs_qqq, 2),
                "Dyn Tuki": f"{dyn_support} ({support_type})",
                "Dyn Trim": dyn_trim,
                "Signaali": status_flag
            })

            try:
                raw_news = t.news
                if raw_news and len(raw_news) > 0:
                    top_n = raw_news[0]
                    title = top_n.get("title") or top_n.get("content", {}).get("title", "")
                    if title:
                        news_items.append(f"- **{sym}:** {title}")
            except Exception:
                pass

        except Exception:
            continue

    df = pd.DataFrame(rows)
    return now_str, macro_info, df, news_items

def build_ai_markdown_report(now_str, macro_info, df, news_items):
    vix = macro_info.get("VIX", {})
    qqq = macro_info.get("QQQ", {})
    spy = macro_info.get("SPY", {})
    fx = macro_info.get("EURUSD", {})

    md = f"# 📡 ST0_LIVE_MARKET_FEED — AI SCOUT REPORT (DYNAMIC v2.0)\n"
    md += f"**AIKALEIMA:** `{now_str}` `[LIVE_USER_FEED: 0-3min]`\n"
    md += f"**MAKRO:** `VIX: {vix.get('price')} ({vix.get('chg_pct')}%)` | `QQQ: {qqq.get('chg_pct')}%` | `SPY: {spy.get('chg_pct')}%` | `EUR/USD: {fx.get('price')}`\n\n"

    alerts_df = df[df["Signaali"] != "OK"]
    if not alerts_df.empty:
        md += "## 🚨 AKTIIVISET DYNAAMISET SIGNAALIT & POIKKEAMAT\n"
        for _, r in alerts_df.iterrows():
            md += f"- **{r['Ticker']} ({r['Hinta']} | {r['Muutos %']}%):** {r['Signaali']} | RSI: {r['RSI(14)']} | Low/High: {r['Day Low']}–{r['Day High']} | Dyn Tuki: {r['Dyn Tuki']} | Dyn Trim: {r['Dyn Trim']}\n"
        md += "\n"

    md += "## 📊 21 KOHTEEN DYNAAMINEN TEKNINEN & SUHTEELLINEN MATRIISI\n"
    md += "| Ticker | Kori | Hinta | Sessio | Muutos % | Day Low/High | RSI(14) | vs SMA50% | vs SMA200% | ADR% | RS vs QQQ | Dyn Tuki | Dyn Trim | Signaali |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    for _, r in df.iterrows():
        md += f"| **{r['Ticker']}** | {r['Kori']} | {r['Hinta']} | {r['Tila']} | {r['Muutos %']}% | {r['Day Low']}/{r['Day High']} | {r['RSI(14)']} | {r['vs SMA50 %']}% | {r['vs SMA200 %']}% | {r['ADR %']}% | {r['RS vs QQQ']}% | {r['Dyn Tuki']} | {r['Dyn Trim']} | {r['Signaali']} |\n"

    if news_items:
        md += "\n## 📰 TUOREIMMAT YHTIÖUUTISET (VIIMEISET 24H)\n"
        md += "\n".join(news_items[:15]) + "\n"

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
st.title("📡 ST0 Market Scout v2.0 (Dynamic Self-Calibrating PWA)")

if st.button("🔄 Päivitä Live-Kurssit & Lähetä Driveen", type="primary", use_container_width=True):
    st.cache_data.clear()

now_str, macro_info, df, news_items = fetch_all_market_data()
ai_report_md = build_ai_markdown_report(now_str, macro_info, df, news_items)

webhook_url = get_webhook_url()
ok, msg = push_to_google_drive_webhook(ai_report_md, webhook_url)

if ok:
    st.success(f"{msg} ({now_str}) — Voit nyt avata Gemin ja sanoa: **'Tee tilannepäivitys ja toimintasuunnitelma'**!")
else:
    st.warning(f"🕒 Ladattu: {now_str} | {msg}")

with st.expander("📋 VARAVAIHTOEHTO: Kopioi raportti leikepöydälle (1 klikkaus oikeasta yläkulmasta)", expanded=not ok):
    st.code(ai_report_md, language="markdown")

st.subheader("🚨 Aktiiviset Dynaaminen Signaalit")
st.dataframe(df[df["Signaali"] != "OK"], use_container_width=True, hide_index=True)

st.subheader("📊 Koko Salkku & Seurantalista (Itsekalibroituvat Tuki- & Trim-tasot)")
st.dataframe(df, use_container_width=True, hide_index=True)
