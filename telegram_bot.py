import requests
from config import TELEGRAM_TOKEN, CHAT_ID, TICK_VALUE

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(text, parse_mode="HTML"):
    try:
        resp = requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def format_signal_1(signal, session):
    d = signal['direction']
    arrow = "LONG" if d == "LONG" else "SHORT"
    reasons = " | ".join(signal['reason'])
    return (
        f"<b>SIGNAL 1 - ATTENTION</b>\n"
        f"Direction: <b>{arrow}</b>\n"
        f"Price: {signal['price']}\n"
        f"Session: {session}\n"
        f"RSI: {signal['rsi']}\n"
        f"MACD: {signal['macd']}\n"
        f"EMA200: {signal['ema200']}\n"
        f"Trend: {signal['trend']}\n"
        f"Lots: <b>{signal['lots']}</b>\n"
        f"SL: {signal['sl']} | TP: {signal['tp']}\n"
        f"Reason: {reasons}\n"
        f"<i>Wait for confirmation!</i>"
    )

def format_signal_2(signal, session):
    d = signal['direction']
    reasons = " | ".join(signal['reason'])
    return (
        f"<b>SIGNAL 2 - AVERAGING</b>\n"
        f"Direction: <b>{d}</b>\n"
        f"Price: {signal['price']}\n"
        f"Session: {session}\n"
        f"RSI: {signal['rsi']}\n"
        f"MACD: {signal['macd']}\n"
        f"EMA200: {signal['ema200']}\n"
        f"Add: <b>+{signal['lots']} lot</b>\n"
        f"SL: {signal['sl']} | TP: {signal['tp']}\n"
        f"Reason: {reasons}\n"
        f"<i>Waiting for final signal</i>"
    )

def format_signal_3(signal, session):
    d = signal['direction']
    pts_risk = abs(signal['price'] - signal['sl'])
    pts_reward = abs(signal['tp'] - signal['price'])
    usd_risk = round(pts_risk * TICK_VALUE * signal['lots'], 0)
    usd_reward = round(pts_reward * TICK_VALUE * signal['lots'], 0)
    rr = round(pts_reward / pts_risk, 1) if pts_risk else 0
    reasons = " | ".join(signal['reason'])
    return (
        f"<b>STRONG SIGNAL - LEVEL 3 - ENTER NOW</b>\n"
        f"Direction: <b>{d}</b>\n"
        f"Price: {signal['price']}\n"
        f"Session: {session}\n"
        f"RSI: {signal['rsi']} OK\n"
        f"MACD: reversed OK\n"
        f"EMA200: {signal['ema200']} OK\n"
        f"Trend: {signal['trend']} OK\n"
        f"Add: <b>+{signal['lots']} lot</b>\n"
        f"SL: {signal['sl']} (-{pts_risk:.1f} pts / -${usd_risk})\n"
        f"TP: {signal['tp']} (+{pts_reward:.1f} pts / +${usd_reward})\n"
        f"RR: 1:{rr}\n"
        f"Reason: {reasons}\n"
        f"<b>THIS IS THE ENTRY POINT!</b>"
    )

def format_morning_briefing(price, ema200, rsi, levels, news_text, session):
    trend = "BULLISH" if price > ema200 else "BEARISH"
    return (
        f"<b>MORNING BRIEFING - MES/SPX500</b>\n"
        f"Price: {price}\n"
        f"EMA200: {ema200:.1f} - Trend: {trend}\n"
        f"RSI: {rsi:.1f}\n"
        f"Session: {session}\n\n"
        f"KEY LEVELS:\n"
        f"PDH: {levels['pdh']} - resistance\n"
        f"PDL: {levels['pdl']} - support\n"
        f"Resistance: {levels['resistance']}\n"
        f"Support: {levels['support']}\n\n"
        f"{news_text}\n"
        f"PLAN:\n"
        f"SHORT from {levels['pdh']} if RSI>72 + MACD down\n"
        f"LONG from {levels['pdl']} if RSI<28 + MACD up\n"
        f"Max: 3 contracts - Stop at 20:00 GMT"
    )

def format_warning_20h(price, direction, lots):
    return (
        f"<b>WARNING! 19:30 GMT</b>\n"
        f"Open position: <b>{direction} {lots} lots</b>\n"
        f"Price: <b>{price}</b>\n"
        f"<b>Close position before 20:00 GMT!</b>\n"
        f"Protection from broker stop-out."
    )

def test_connection():
    try:
        resp = requests.get(f"{BASE_URL}/getMe", timeout=10)
        if resp.status_code == 200:
            name = resp.json()['result']['first_name']
            send_message(
                f"<b>{name} is running!</b>\n"
                f"MES Trading Signals activated.\n"
                f"Добро пожаловать в MES SIGNALS!\n\n"
f"Бот анализирует рынок 24/5 и присылает\n"
f"сигналы для торговли фьючерсом MES\n"
f"на индексе S&P500.\n\n"
f"Каждое утро ты получаешь брифинг\n"
f"с ключевыми уровнями и новостями дня.\n\n"
f"Сигналы основаны на анализе:\n"
f"EMA200 · RSI · MACD · FVG\n"
f"Уровни сессий Asia · London · NY\n\n"
f"ВАЖНО:\n"
f"Количество контрактов и риски\n"
f"ты определяешь самостоятельно.\n"
f"Сигналы носят информационный характер.\n\n"
f"Удачи в торговле!"

            )
            return True
        return False
    except:
        return False
