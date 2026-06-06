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
        print(f"Ошибка Telegram: {e}")
        return False

def format_signal_1(signal, session):
    d = signal['direction']
    return f"""
⚠️ <b>СИГНАЛ 1 · ВНИМАНИЕ</b>
━━━━━━━━━━━━━━━━━━━━━━━━
{'📈' if d=='LONG' else '📉'} <b>{d}</b> · {signal['price']}
📊 Сессия: {session}
· RSI: {signal['rsi']}
· MACD: {signal['macd']}
· EMA200: {signal['ema200']}
· Тренд: {'⬆️ БЫЧИЙ' if signal['trend']=='bull' else '⬇️ МЕДВЕЖИЙ'}
⚙️ Открываем <b>{signal['lots']} лот</b>
🛡 SL: {signal['sl']} · 🎯 TP: {signal['tp']}
💡 {' | '.join(signal['reason'])}
⚠️ <i>Ждём подтверждения!</i>
""".strip()

def format_signal_2(signal, session):
    d = signal['direction']
    return f"""
🔵 <b>СИГНАЛ 2 · УСРЕДНЕНИЕ</b>
━━━━━━━━━━━━━━━━━━━━━━━━
{'📈' if d=='LONG' else '📉'} <b>{d}</b> · {signal['price']}
📊 Сессия: {session}
· RSI: {signal['rsi']} {'🔴 перепродан' if signal['rsi']<30 else '🔴 перекуплен'}
· MACD: {signal['macd']}
· EMA200: {signal['ema200']}
⚙️ Добавляем <b>+{signal['lots']} лот</b>
🛡 SL: {signal['sl']} · 🎯 TP: {signal['tp']}
💡 {' | '.join(signal['reason'])}
🔄 <i>Ждём финального сигнала</i>
""".strip()

def format_signal_3(signal, session):
    d = signal['direction']
    pts_risk = abs(signal['price'] - signal['sl'])
    pts_reward = abs(signal['tp'] - signal['price'])
    usd_risk = round(pts_risk * TICK_VALUE * signal['lots'], 0)
    usd_reward = round(pts_reward * TICK_VALUE * signal['lots'], 0)
    rr = round(pts_reward / pts_risk, 1) if pts_risk else 0
    return f"""
🟢 <b>СИЛЬНЫЙ СИГНАЛ · УРОВЕНЬ 3</b>
━━━━━━━━━━━━━━━━━━━━━━━━
{'🚀' if d=='LONG' else '💥'} <b>ВХОДИМ: {d}</b>
💰 Цена: {signal['price']}
📊 Сессия: {session}
· RSI: {signal['rsi']} ✅
· MACD: развернулся ✅
· EMA200: {signal['ema200']} ✅
· Тренд: {'⬆️ БЫЧИЙ' if signal['trend']=='bull' else '⬇️ МЕДВЕЖИЙ'} ✅
⚙️ Добавляем <b>+{signal['lots']} лот</b>
🛡 SL: {signal['sl']} (-{pts_risk:.1f} pts · -${usd_risk})
🎯 TP: {signal['tp']} (+{pts_reward:.1f} pts · +${usd_reward})
⚖️ R:R = 1:{rr}
💡 {' | '.join(signal['reason'])}
✅ <b>ЭТО ТОЧКА ВХОДА!</b>
""".strip()

def format_morning_briefing(price, ema200, rsi, levels, news_text, session):
    trend = '⬆️ БЫЧИЙ' if price > ema
