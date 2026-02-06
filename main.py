import yfinance as yf
import requests
from datetime import datetime
import json
import time
import random
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from seleniumbase import SB

bot_token = "8169560167:AAEe0czlYttpySFVImxb4BNROZaEhdQA0Aw"
chat_id = "1022549373"


# ------------------- SAFE FLOAT (CRASH FIX ONLY) -------------------
def to_float(x, default=0.0):
    if isinstance(x, pd.Series):
        x = x.iloc[-1]
    if pd.isna(x):
        return default
    return float(x)


# ------------------- Utility -------------------
def compute_dynamic_weight(std, base_weight=1.0, scale=10):
    return round(base_weight * (1 + std / scale), 2)


def asym_scale(value, pos_scale=1.2, neg_scale=1.5):
    return pos_scale if value >= 0 else neg_scale


# ------------------- Data Fetching -------------------
def get_fii_net():
    api_url = "https://www.nseindia.com/api/fiidiiTradeReact"
    home_url = "https://www.nseindia.com/"

    try:
        with SB(uc=True, headless=True, locale="en") as sb:
            
            sb.open(home_url)
            sb.wait_for_ready_state_complete()
            time.sleep(3)

            response = sb.execute_script("""
                return fetch(arguments[0], {
                    method: 'GET',
                    credentials: 'include'
                }).then(r => r.text());
            """, api_url)

            data = json.loads(response)

            fii = next(
                (float(x["netValue"]) for x in data
                 if "FII" in x.get("category", "")),
                0.0
            )
            return fii

    except Exception as e:
        print(f"❌ SeleniumBase NSE fetch failed: {e}")
        return 0.0


def get_nifty():
    return yf.Ticker("^NSEI").info["regularMarketPrice"]


def get_vix():
    df = yf.download("^INDIAVIX", period="30d", interval="1d",
                     auto_adjust=False, progress=False)
    closes = df["Close"].dropna()

    vix_now = closes.iloc[-1]
    vix_std = closes.std()
    vix_mean = closes.mean()

    if isinstance(vix_std, pd.Series):
        vix_std = vix_std.iloc[0]
    if pd.isna(vix_std) or vix_std == 0:
        vix_std = 1.0

    return to_float(vix_now), to_float(vix_std, 1.0), to_float(vix_mean)


def get_crude():
    df = yf.download("CL=F", period="30d", interval="1d", progress=False)
    closes = df["Close"].dropna()

    crude_now = closes.iloc[-1]
    crude_std = closes.std()
    crude_mean = closes.mean()

    if isinstance(crude_std, pd.Series):
        crude_std = crude_std.iloc[0]
    if pd.isna(crude_std) or crude_std == 0:
        crude_std = 2.0

    return to_float(crude_now), to_float(crude_std, 2.0), to_float(crude_mean)


def get_usdinr():
    df = yf.download("USDINR=X", period="30d", interval="1d",
                     auto_adjust=False, progress=False)
    closes = df["Close"].dropna()

    usdinr_now = closes.iloc[-1]
    usdinr_std = closes.std()
    usdinr_mean = closes.mean()

    if isinstance(usdinr_std, pd.Series):
        usdinr_std = usdinr_std.iloc[0]
    if pd.isna(usdinr_std) or usdinr_std == 0:
        usdinr_std = 1.0

    return to_float(usdinr_now), to_float(usdinr_std, 1.0), to_float(usdinr_mean)


def get_dxy():
    df = yf.download("DX-Y.NYB", period="30d", interval="1d", progress=False)
    closes = df["Close"].dropna()

    dxy_now = closes.iloc[-1]
    dxy_std = closes.std()
    dxy_mean = closes.mean()

    if isinstance(dxy_std, pd.Series):
        dxy_std = dxy_std.iloc[0]
    if pd.isna(dxy_std) or dxy_std == 0:
        dxy_std = 1.0

    return to_float(dxy_now), to_float(dxy_std, 1.0), to_float(dxy_mean)


def get_us10y_yield():
    df = yf.download("^TNX", period="30d", interval="1d", progress=False)
    closes = df["Close"].dropna() / 10

    us10y_now = closes.iloc[-1]
    us10y_std = closes.std()
    us10y_mean = closes.mean()

    if isinstance(us10y_std, pd.Series):
        us10y_std = us10y_std.iloc[0]
    if pd.isna(us10y_std) or us10y_std == 0:
        us10y_std = 0.1

    return to_float(us10y_now), to_float(us10y_std, 0.1), to_float(us10y_mean)


def get_gold_silver_trend():
    gold = yf.download("GC=F", period="7d", interval="1d",
                       auto_adjust=True, progress=False)
    silver = yf.download("SI=F", period="7d", interval="1d",
                         auto_adjust=True, progress=False)

    gold_close = gold["Close"].dropna()
    silver_close = silver["Close"].dropna()

    gold_trend = (gold_close.pct_change().rolling(3).mean().iloc[-1] * 100
                  if len(gold_close) >= 4 else 0.0)
    silver_trend = (silver_close.pct_change().rolling(3).mean().iloc[-1] * 100
                    if len(silver_close) >= 4 else 0.0)

    return to_float(gold_trend), to_float(silver_trend)


def get_global_sentiment_score():
    indices = {
        "Nikkei": "^N225",
        "KOSPI": "^KS11",
        "Hang Seng": "^HSI",
        "ASX": "^AXJO"
    }

    total, count = 0, 0
    for ticker in indices.values():
        try:
            data = yf.download(ticker, period="2d", interval="1d", progress=False)
            if len(data) >= 2:
                prev = data["Close"].iloc[-2].item()
                curr = data["Close"].iloc[-1].item()
                total += ((curr - prev) / prev) * 100
                count += 1
        except:
            continue

    return round(total / count, 2) if count else 0.0


# ------------------- Nifty Helpers -------------------


def get_nifty_prev_change():
    data = yf.download("^NSEI", period="3d", interval="1d", auto_adjust=False)
    if len(data) >= 2:
        prev = data["Close"].iloc[-2].item()
        curr = data["Close"].iloc[-1].item()
        return ((curr - prev) / prev) * 100
    return 0.0


def get_nifty_trend():
    data = yf.download("^NSEI", period="5d", interval="1d", auto_adjust=False)
    if len(data) >= 3:
        closes = data["Close"].values[-3:]
        trend = [
            "up" if closes[i] > closes[i - 1] else "down" for i in range(1, 3)
        ]
        if trend == ["up", "up"]:
            return "up"
        elif trend == ["down", "down"]:
            return "down"
    return "sideways"


def get_nifty_avg():
    data = yf.download("^NSEI",
                       period="200d",
                       interval="1d",
                       auto_adjust=False)
    return data["Close"].mean().item() if not data.empty else 25000


# ------------------- Scoring & Advice -------------------


def get_final_advice(fii):
    # Fetch all required data
    nifty = get_nifty()
    nifty_trend = get_nifty_trend()
    nifty_avg = get_nifty_avg()
    nifty_change = get_nifty_prev_change()

    crude, crude_std, crude_baseline = get_crude()
    dxy, dxy_std, dxy_baseline = get_dxy()
    us10y, us10y_std, us10y_baseline = get_us10y_yield()
    vix, vix_std, vix_baseline = get_vix()
    usdinr, usdinr_std, usdinr_baseline = get_usdinr()

    gold_trend, silver_trend = get_gold_silver_trend()
    global_sentiment = get_global_sentiment_score()

    # Define adaptive weights
    weights = {
        "nifty": 1.0,
        "fii": 2.0,
        "vix": compute_dynamic_weight(vix_std, base_weight=1.5),
        "crude": compute_dynamic_weight(crude_std, base_weight=1.2),
        "usdinr": compute_dynamic_weight(usdinr_std, base_weight=1.2),
        "global": 1.2,
        "us10y": compute_dynamic_weight(us10y_std, base_weight=1.5),
        "dxy": compute_dynamic_weight(dxy_std, base_weight=1.5),
        "gold": 1.0,
        "silver": 1.0
    }

    # Compute individual component scores
    scores = pd.Series(dtype="float64")

    scores["nifty_change"] = weights["nifty"] * max(min(nifty_change / 2, 1),
                                                    -1)
    scores["fii_flow"] = weights["fii"] * max(min(fii / 2000, 1),
                                              -1) * asym_scale(fii)
    vix_baseline = 15
    scores["vix"] = -weights["vix"] * (
        (vix - vix_baseline) / vix_baseline) * asym_scale(vix - vix_baseline)
    scores["crude"] = -weights["crude"] * (
        (crude - crude_baseline) / crude_baseline) * asym_scale(crude -
                                                                crude_baseline)
    scores["usdinr"] = -weights["usdinr"] * (
        (usdinr - usdinr_baseline) /
        usdinr_baseline) * asym_scale(usdinr - usdinr_baseline)
    scores["global"] = -weights["global"] * max(min(global_sentiment / 3, 1),
                                               -1)
    scores["us10y"] = -weights["us10y"] * (
        (us10y - us10y_baseline) / us10y_baseline) * asym_scale(us10y -
                                                                us10y_baseline)
    scores["dxy"] = -weights["dxy"] * (
        (dxy - dxy_baseline) / dxy_baseline) * asym_scale(dxy - dxy_baseline)

    # Gold and Silver combined
    if gold_trend * silver_trend > 0:
        combined_trend = (gold_trend + silver_trend) / 2
        scores["gold_silver"] = combined_trend * weights["gold"] * 1.2
    else:
        scores["gold"] = gold_trend * weights["gold"]
        scores["silver"] = silver_trend * weights["silver"]

    # Nifty trend
    trend_score = {
        "up": 0.5,
        "sideways": 0.0,
        "down": -0.5
    }.get(nifty_trend, 0)
    scores["nifty_trend"] = trend_score * 0.8

    # Nifty vs avg
    scores["nifty_vs_avg"] = 0.3 if nifty > nifty_avg else -0.3

    # Total score
    final_score = scores.sum()

    # New: adaptive threshold from mean absolute score × factor + floor
    mean_abs = scores.abs().mean() or 0
    # std_threshold = max(mean_abs * 1.2, 1.5)
    std_threshold = scores.std() * 1.2 + scores.abs().mean() * 0.5

    # Final advice
    if final_score >= std_threshold:
        return (
            f"📊 Score: {final_score:.2f} ≥ Threshold: {std_threshold:.2f}\n"
            f"📈 Gold & silver prices may be high today.\n\n"
            f"🙅‍♂️ Avoid buying now.\n"
            f"💰 Consider booking profit if you're already holding."
        )
    elif final_score <= -std_threshold:
        return (
            f"📊 Score: {final_score:.2f} ≤ -Threshold: {std_threshold:.2f}\n"
            f"📉 Gold & silver prices may be lower today.\n\n"
            f"🛒 Good time to buy at lower levels.\n"
            f"✅ You may consider entering now."
        )
    else:
        return (
            f"📊 Score: {final_score:.2f} is within ±{std_threshold:.2f}\n"
            f"➖ No strong move expected today.\n\n"
            f"⏳ Better to wait and watch.\n"
            f"🤝 HOLD your position."
        )


# ------------------- Telegram -------------------


def send_telegram(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, data=data)
    if response.ok:
        msg_id = response.json()["result"]["message_id"]
        store_message_info(msg_id, int(time.time()))
        return msg_id
    return None


def store_message_info(msg_id, timestamp):
    try:
        with open("messages.json", "r") as f:
            msgs = json.load(f)
    except:
        msgs = []
    msgs.append({"id": msg_id, "time": timestamp})
    with open("messages.json", "w") as f:
        json.dump(msgs, f)


def delete_old_messages():
    try:
        with open("messages.json", "r") as f:
            msgs = json.load(f)
    except:
        msgs = []

    new_msgs = []
    now = int(time.time())
    url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"

    for msg in msgs:
        age = now - msg["time"]
        if 86400 <= age <= 172800:
            res = requests.post(url,
                                data={
                                    "chat_id": chat_id,
                                    "message_id": msg["id"]
                                })
            if not res.ok:
                new_msgs.append(msg)
        else:
            new_msgs.append(msg)

    with open("messages.json", "w") as f:
        json.dump(new_msgs, f)


# ------------------- Main -------------------


def run_daily_signal():
    delete_old_messages()

    fii = get_fii_net()
    nifty = get_nifty()
    vix, _, _ = get_vix()
    crude, _, _ = get_crude()
    usdinr, _, _ = get_usdinr()
    prev_change = get_nifty_prev_change()
    trend = get_nifty_trend()
    nifty_avg = get_nifty_avg()
    global_score = get_global_sentiment_score()
    dxy, _, _ = get_dxy()
    us10y, _, _ = get_us10y_yield()
    gold_trend, silver_trend = get_gold_silver_trend()

    sig = get_final_advice(fii)

    today = datetime.today()

    message = (
        f"📅 {today.strftime('%d %b %Y')} | 🪙 Gold & Silver FoF Advisor (India)\n\n"
        f"📈 Nifty50: {nifty:.2f}\n"
        f"📊 Nifty 1D Change: {prev_change:.2f}%\n"
        f"📉 Nifty Trend: {trend.title()}\n"
        f"📐 Nifty Average: {nifty_avg:.2f}\n"
        f"💰 FII Net Inflow: ₹{fii:.2f} Cr\n"
        f"🌪 India VIX: {vix:.2f}\n"
        f"🌍 Global Sentiment Score: {global_score:+.2f}\n"
        f"🛢 Crude Oil (WTI): ${crude:.2f}\n"
        f"💱 USD/INR: ₹{usdinr:.2f}\n"
        f"💵 Dollar Index (DXY): {dxy:.2f}\n"
        f"🇺🇸 US 10Y Yield: {us10y:.2f}%\n"
        f"🏅 Gold Futures: {gold_trend:+.2f}%\n"
        f"🥈 Silver Futures: {silver_trend:+.2f}%\n\n"
        f"{sig}"
    )

    print(message)
    send_telegram(message)


# def run_daily_signal():
if __name__ == "__main__":
    run_daily_signal()