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

def calc_levels(price, sl, direction):
    dist = abs(price - sl)
    if direction == "LONG":
        return {
            "tp1": round(price + dist * 1.0, 2),
            "tp2": round(price + dist * 1.8, 2),
            "tp3": round(price + dist * 2.8, 2),
            "tp4": round(price + dist * 4.0, 2),
        }
    else:
        return {
            "tp1": round(price - dist * 1.0, 2),
            "tp2": round(price - dist * 1.8, 2),
            "tp3": round(price - dist * 2.8, 2),
            "tp4": round(price - dist * 4.0, 2),
        }

def format_signal_1(signal, session):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_levels(signal['price'], signal['sl'], d)
    return (
        f"{emoji} {d} · MES · Micro E-mini\n\n"
        f"Вход: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}"
    )

def format_signal_2(signal, session):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_levels(signal['price'], signal['sl'], d)
    return (
        f"{emoji} {d} · MES · Micro E-mini\n\n"
        f"Вход: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}"
    )

def format_signal_3(signal, session):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_levels(signal['price'], signal['sl'], d)
    return (
        f"{emoji} {d} · MES · Micro E-mini\n\n"
        f"Вход: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}"
    )

def format_averaging(signal, session):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_levels(signal['price'], signal['sl'], d)
    return (
        f"{emoji} {d} +1 · MES · Micro E-mini\n\n"
        f"Цена: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}"
    )

def format_morning_briefing(price, ema200, rsi, levels, news_text, session):
    trend = "выше EMA" if price > ema200 else "ниже EMA"
    return (
        f"🌅 БРИФИНГ · MES · Micro E-mini\n\n"
        f"Цена:   {price}\n"
        f"EMA200: {ema200:.1f} · {trend}\n"
        f"RSI:    {rsi:.1f}\n\n"
        f"УРОВНИ:\n"
        f"PDH: {levels['pdh']}\n"
        f"PDL: {levels['pdl']}\n"
        f"Сопр: {levels['resistance']}\n"
        f"Подд: {levels['support']}\n\n"
        f"{news_text}"
    )

def format_warning_20h(price, direction, lots):
    emoji = "🟢" if direction == "LONG" else "🔴"
    return (
        f"⚠️ 19:30 GMT\n\n"
        f"{emoji} {direction} · {lots} лот · MES\n"
        f"Цена: {price}\n\n"
        f"Закрой позицию до 20:00 GMT"
    )

def test_connection():
    try:
        resp = requests.get(f"{BASE_URL}/getMe", timeout=10)
        if resp.status_code == 200:
            name = resp.json()['result']['first_name']
            send_message(
                f"<b>{name}</b>\n\n"
                f"Добро пожаловать в MES SIGNALS!\n\n"
                f"Бот анализирует рынок 24/5 и присылает\n"
                f"сигналы для торговли фьючерсом MES\n"
                f"на индексе S&P500.\n\n"
                f"Каждое утро ты получаешь брифинг\n"
                f"с ключевыми уровнями и новостями дня.\n\n"
                f"Сигналы основаны на анализе:\n"
                f"EMA200 · RSI · MACD · FVG\n"
                f"Уровни поддержки и сопротивления\n"
                f"Максимумы/минимумы предыдущего дня\n"
                f"Уровни сессий Азии · Лондона · NY\n\n"
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
