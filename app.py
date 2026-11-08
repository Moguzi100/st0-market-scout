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
    page_title="ST0 Market Scout v2.1",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# DYNAAMINEN KONFIGURAATIO (04_TICKER_DNA_PLAYBOOKS)
# dna_ma = Osakkeen luontainen primääri tukikeskiarvo
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
# WILDERIN VIRALLINEN RSI(14) (TradingView / Bloomberg Standard)
# ==========================================
def calc_wilder_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

@st.cache_data(ttl=120)
def fetch_all_market_data():
    tz_fi = pytz.timezone("Europe/Helsinki")
    now_str = datetime.now(tz_fi).strftime("%d.%m.%Y klo %H:%M:%S EET")

    macro_info = {}
    qqq_chg = 0.0
    spy_chg = 0.0
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
                elif name == "SPY":
                    spy_chg = chg
        except Exception:
            macro_info[name] = {"price": 0.0, "chg_pct": 0.0}

    rows = []
    news_items = []
    seen_titles = set()

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
            last_close = float(close_s.iloc[-1])
            prev_close = float(close_s.iloc[-2]) if len(close_s) >= 2 else last_close
            day_high = float(hist["High"].iloc[-1])
            day_low = float(hist["Low"].iloc[-1])
            high_52w = float(hist["High"].max())
            low_60d = float(hist["Low"].tail(60).min())

            # Haetaan live/pre/after-hours & fundamenttiarvostus (Fwd P/E)
            live_price = last_close
            market_session = "REG/CLOSE"
            fwd_pe_str = "N/A"
            try:
                fast = t.info
                pre_p = fast.get("preMarketPrice")
                post_p = fast.get("postMarketPrice")
                curr_p = fast.get("currentPrice") or fast.get("regularMarketPrice")
                reg_prev = fast.get("regularMarketPreviousClose") or prev_close

                if pre_p and pre_p > 0:
                    live_price = float(pre_p)
                    prev_close = float(last_close)  # Pre-market verrataan eilisen päätökseen
                    market_session = "PRE-MKT"
                elif post_p and post_p > 0 and abs(float(post_p) - last_close) / last_close > 0.0005:
                    live_price = float(post_p)
                    prev_close = float(reg_prev)
                    market_session = "AFTER-HRS"
                elif curr_p and curr_p > 0:
                    live_price = float(curr_p)
                    prev_close = float(reg_prev)

                f_pe = fast.get("forwardPE")
                t_pe = fast.get("trailingPE")
                pb = fast.get("priceToBook")
                if f_pe and f_pe > 0:
                    fwd_pe_str = f"{round(float(f_pe), 1)}x"
                elif t_pe and t_pe > 0:
                    fwd_pe_str = f"{round(float(t_pe), 1)}x(T)"
                elif pb and pb > 0:
                    fwd_pe_str = f"PB:{round(float(pb), 1)}x"
            except Exception:
                pass

            chg_pct = ((live_price / prev_close) - 1) * 100
            dd_52w_pct = ((live_price / high_52w) - 1) * 100
            rsi_val = float(calc_wilder_rsi(close_s).iloc[-1]) if len(close_s) >= 15 else 50.0

            # Liukuvat keskiarvot & Bollinger-kanavat (20pv ± 2σ)
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

            # Suhteellinen vahvuus (USA/Tech vs QQQ, Suomi/Teollisuus vs SPY)
            bench_chg = spy_chg if ".HE" in used_yf else qqq_chg
            rs_vs_bench = chg_pct - bench_chg

            # ==========================================
            # AITO RAKENTEELLINEN TUKITASOPORRAS (True Support Ladder)
            # Etsitään korkein aito tekninen tukitaso, joka on <= nykyhinta * 1.01
            # ==========================================
            candidates = [
                ("SMA50", sma50),
                ("SMA100", sma100),
                ("SMA200", sma200),
                ("BB-Low(2σ)", lower_bb),
                ("60d-Low", low_60d)
            ]
            below_supports = [(name, val) for name, val in candidates if val <= live_price * 1.015]
            if below_supports:
                # Valitaan lähin vahva tuki nykyhinnan alapuolelta
                support_type, dyn_support_raw = max(below_supports, key=lambda x: x[1])
                dyn_support = round(dyn_support_raw, 2)
            else:
                # Jos osake on kaikkien tukien ja 60pv pohjankin alla (äärimmäinen pudotus)
                dyn_support = round(low_60d, 2)
                support_type = "60d-Low(Broken)"

            # Rakenteellinen vastus / kevennystaso (Dyn Trim)
            above_resistances = [val for _, val in [("SMA50", sma50), ("SMA200", sma200), ("BB-High", upper_bb), ("52w-High", high_52w)] if val >= live_price * 1.03]
            dyn_trim = round(min(above_resistances) if above_resistances else upper_bb, 2)

            # ==========================================
            # TARKKA SIGNAALILOGIIKKA (v2.1)
            # ==========================================
            dist_to_support_pct = ((live_price / dyn_support) - 1) * 100
            status_flag = "OK"

            if rsi_val <= 33.0:
                status_flag = f"🟢 RSI YLIMYYTY ({round(rsi_val,1)}) | Tuki: {dyn_support}"
            elif -1.5 <= dist_to_support_pct <= 2.5 and rsi_val <= 46.0:
                status_flag = f"🟢 TESTAA {support_type}-TUKEA ({dyn_support})"
            elif rsi_val >= 72.0:
                status_flag = f"🟠 RSI YLIOSTETTU ({round(rsi_val,1)}) | Trim: {dyn_trim}"
            elif abs(chg_pct) >= 5.0:
                status_flag = f"⚡ >5% LIIKE ({round(chg_pct,1)}%)"
            elif rs_vs_bench >= 3.0 and chg_pct > 0:
                status_flag = f"💪 RS-JOHTAJA (+{round(rs_vs_bench,1)}% vs Idx)"

            rows.append({
                "Ticker": sym if used_yf == sym or ".HE" in used_yf else f"{sym} ({used_yf})",
                "Kori": cfg["bucket"],
                "Hinta": round(live_price, 2),
                "Sessio": market_session,
                "Muutos %": round(chg_pct, 2),
                "52w Huipusta %": round(dd_52w_pct, 1),
                "Fwd P/E": fwd_pe_str,
                "RSI(14)": round(rsi_val, 1),
                "vs SMA50 %": round(dist_sma50, 1),
                "vs SMA200 %": round(dist_sma200, 1),
                "ADR %": round(adr_pct, 1),
                "RS vs Idx": round(rs_vs_bench, 2),
                "Dyn Tuki": f"{dyn_support} ({support_type})",
                "Dyn Trim": dyn_trim,
                "Day Low/High": f"{round(day_low,2)}/{round(day_high,2)}",
                "Signaali": status_flag
            })

            # Poimitaan uniikit uutisotsikot (suodatetaan duplikaatit pois)
            try:
                raw_news = t.news
                if raw_news:
                    for item in raw_news[:3]:
                        title = item.get("title") or item.get("content", {}).get("title", "")
                        if title and title not in seen_titles:
                            seen_titles.add(title)
                            news_items.append(f"- **{sym}:** {title}")
                            break
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

    md = f"# 📡 ST0_LIVE_MARKET_FEED — AI SCOUT REPORT (PRECISION v2.1)\n"
    md += f"**AIKALEIMA:** `{now_str}` `[LIVE_USER_FEED: 0-3min]`\n"
    md += f"**MAKRO:** `VIX: {vix.get('price')} ({vix.get('chg_pct')}%)` | `QQQ: {qqq.get('chg_pct')}%` | `SPY: {spy.get('chg_pct')}%` | `EUR/USD: {fx.get('price')}`\n\n"

    alerts_df = df[df["Signaali"] != "OK"]
    if not alerts_df.empty:
        md += "## 🚨 AKTIIVISET SIGNAALIT & POIKKEAMAT\n"
        for _, r in alerts_df.iterrows():
            md += (
                f"- **{r['Ticker']} ({r['Hinta']} | {r['Muutos %']}% | 52w: {r['52w Huipusta %']}% | Fwd P/E: {r['Fwd P/E']}):** "
                f"{r['Signaali']} | Wilder RSI: {r['RSI(14)']} | Dyn Tuki: {r['Dyn Tuki']} | Dyn Trim: {r['Dyn Trim']}\n"
            )
        md += "\n"

    md += "## 📊 21 KOHTEEN FUNDAMENTTI-, TEKNINEN & SUHTEELLINEN MATRIISI\n"
    md += "| Ticker | Kori | Hinta | Sessio | Muutos % | 52w Huipusta | Fwd P/E | RSI(14) | vs SMA50% | vs SMA200% | ADR% | RS vs Idx | Dyn Tuki | Dyn Trim | Signaali |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    for _, r in df.iterrows():
        md += (
            f"| **{r['Ticker']}** | {r['Kori']} | {r['Hinta']} | {r['Sessio']} | {r['Muutos %']}% | "
            f"{r['52w Huipusta %']}% | {r['Fwd P/E']} | {r['RSI(14)']} | {r['vs SMA50 %']}% | "
            f"{r['vs SMA200 %']}% | {r['ADR %']}% | {r['RS vs Idx']}% | {r['Dyn Tuki']} | {r['Dyn Trim']} | {r['Signaali']} |\n"
        )

    if news_items:
        md += "\n## 📰 TUOREIMMAT YHTIÖKOHTAISET UUTISET (UNIIKIT, 24H)\n"
        md += "\n".join(news_items[:18]) + "\n"

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
st.title("📡 ST0 Market Scout v2.1 (Institutional Precision PWA)")

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

st.subheader("🚨 Aktiiviset Signaalit")
st.dataframe(df[df["Signaali"] != "OK"], use_container_width=True, hide_index=True)

st.subheader("📊 Koko Salkku & Seurantalista (v2.1 Precision Engine)")
st.dataframe(df, use_container_width=True, hide_index=True)
