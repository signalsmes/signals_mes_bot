import requests
from datetime import datetime, timezone, timedelta
from config import TELEGRAM_TOKEN, CHAT_ID, TICK_VALUE, CONTRACT_NAME

BASE_URL = "https://api.telegram.org/bot" + TELEGRAM_TOKEN
DUBAI_TZ = timezone(timedelta(hours=4))
NAME = CONTRACT_NAME + " (Micro E-mini S&P 500)"

def send_message(text, parse_mode="HTML"):
    try:
        resp = requests.post(
            BASE_URL + "/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print("Telegram error: " + str(e))
        return False

def calc_tp(price, sl, direction):
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

def get_medal(level):
    if level == 3:
        return "🥇"
    elif level == 2:
        return "🥈"
    return "🥉"

def get_level_name(signal):
    levels = signal.get('levels', {})
    price = signal['price']

    def near(a, b, pct=0.003):
        if not b:
            return False
        return abs(a - b) / b < pct

    names = []
    if near(price, levels.get('pdh', 0)):
        names.append('PDH')
    if near(price, levels.get('pdl', 0)):
        names.append('PDL')
    if near(price, signal.get('ema200', 0)):
        names.append('EMA200')
    if near(price, levels.get('resistance', 0)):
        names.append('Сопротивление')
    if near(price, levels.get('support', 0)):
        names.append('Поддержка')
    if near(price, levels.get('weekly_high', 0)):
        names.append('Weekly High')
    if near(price, levels.get('weekly_low', 0)):
        names.append('Weekly Low')
    for sh in levels.get('swing_highs', []):
        if near(price, sh):
            names.append('Swing High')
            break
    for slow in levels.get('swing_lows', []):
        if near(price, slow):
            names.append('Swing Low')
            break
    for rn in levels.get('round_numbers', []):
        if near(price, rn, 0.002):
            names.append('Round ' + str(int(rn)))
            break
    if signal.get('fvg'):
        names.append('FVG')
    if names:
        return ' · '.join(names)
    return 'Уровень'

def format_signal(signal, session, avg=False):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_tp(signal['price'], signal['sl'], d)
    level_name = get_level_name(signal)
    avg_text = " +1" if avg else ""
    medal = get_medal(signal.get('level', 1))

    return (
        emoji + " " + d + avg_text + " · " + NAME + "\n"
        + medal + "\n\n"
        + "Вход: " + str(signal['price']) + "\n"
        + "SL:     " + str(signal['sl']) + "\n\n"
        + "TP1:  " + str(tp['tp1']) + "\n"
        + "TP2:  " + str(tp['tp2']) + "\n"
        + "TP3:  " + str(tp['tp3']) + "\n"
        + "TP4:  " + str(tp['tp4']) + "\n\n"
        + "📐 " + level_name
    )

def format_signal_1(signal, session):
    return format_signal(signal, session)

def format_signal_2(signal, session):
    return format_signal(signal, session)

def format_signal_3(signal, session):
    return format_signal(signal, session)

def format_averaging(signal, session):
    return format_signal(signal, session, avg=True)

def format_tp_hit(tp_num, price, direction, last=False):
    emoji = "🟢" if direction == "LONG" else "🔴"
    action = "закрой всё" if last else "закрой часть позиции"
    trailing = ""
    if tp_num == 1 and not last:
        trailing = "\n\nSL → безубыток"
    return (
        "✅ TP" + str(tp_num) + " · " + NAME + "\n\n"
        + emoji + " " + direction + " · " + action + "\n"
        + "Цена: " + str(price)
        + trailing
    )

def format_sl_hit(price, direction):
    emoji = "🟢" if direction == "LONG" else "🔴"
    return (
        "❌ SL · " + NAME + "\n\n"
        + emoji + " " + direction + " · позиция закрыта\n"
        + "Цена: " + str(price) + "\n"
        + "Уровень SL достигнут"
    )

def format_level_alert(level_name, level_price, timeframe):
    return (
        "📍 УРОВЕНЬ · " + NAME + "\n\n"
        + "Цена у " + level_name + " · " + timeframe + "\n"
        + "Уровень: " + str(level_price)
    )

def format_ema_alert(ema_value, timeframe):
    return (
        "📍 УРОВЕНЬ · " + NAME + "\n\n"
        + "Цена касается EMA200 · " + timeframe + "\n"
        + "EMA200: " + str(ema_value)
    )

def format_weekly_stats(stats):
    if not stats:
        return "📊 Нет данных за неделю"
    pnl_sign = "+" if stats['pnl'] >= 0 else ""
    best_pnl = "—"
    worst_pnl = "—"
    if stats.get('best'):
        best_pnl = "+$" + str(round(stats['best']['pnl']))
    if stats.get('worst'):
        worst_pnl = "-$" + str(abs(round(stats['worst']['pnl'])))
    return (
        "📊 СТАТИСТИКА НЕДЕЛИ · " + NAME + "\n\n"
        + "Сделок:  " + str(stats['total']) + "\n"
        + "Лонг:    " + str(stats['longs']) + " · Шорт: " + str(stats['shorts']) + "\n\n"
        + "Win Rate: " + str(stats['wr']) + "%\n"
        + "Прибыльных: " + str(stats['wins']) + "\n"
        + "Убыточных:  " + str(stats['losses']) + "\n\n"
        + "P&L:     " + pnl_sign + "$" + str(round(stats['pnl'])) + "\n"
        + "Лучшая:  " + best_pnl + "\n"
        + "Худшая:  " + worst_pnl + "\n\n"
        + "Profit Factor: " + str(stats['pf'])
    )

def format_morning_briefing(price, ema200, rsi, levels, news_list, session):
    from news import format_market_news, format_news_forecast

    now_dubai = datetime.now(DUBAI_TZ)
    time_str = now_dubai.strftime('%H:%M')
    date_str = now_dubai.strftime('%d.%m.%Y')

    news_text = format_news_forecast(news_list)
    market_news = format_market_news()

    rounds = levels.get('round_numbers', [])
    all_res = levels.get('all_resistance', [])
    all_sup = levels.get('all_support', [])

    res_candidates = [levels['pdh']] + all_res[:3]
    for r in rounds:
        if r > price:
            res_candidates.append(r)
    res_set = sorted(set(res_candidates), reverse=True)[:4]

    sup_candidates = [levels['pdl']] + all_sup[:3]
    for r in rounds:
        if r < price:
            sup_candidates.append(r)
    sup_set = sorted(set(sup_candidates), reverse=True)[:4]

    levels_text = "УРОВНИ:\n"
    for l in res_set:
        if l == levels['pdh']:
            tag = "PDH"
        elif l == levels.get('weekly_high'):
            tag = "Weekly High"
        elif l in rounds:
            tag = "Round " + str(int(l))
        else:
            tag = "Swing"
        levels_text += str(l) + " ▪ " + tag + "\n"
    for l in sup_set:
        if l == levels['pdl']:
            tag = "PDL"
        elif l == levels.get('weekly_low'):
            tag = "Weekly Low"
        elif l in rounds:
            tag = "Round " + str(int(l))
        else:
            tag = "Swing"
        levels_text += str(l) + " ▪ " + tag + "\n"
    levels_text += str(round(ema200, 1)) + " ▪ EMA200\n"

    return (
        "🌅 БРИФИНГ · " + NAME + "\n"
        + date_str + " · " + time_str + " Dubai\n\n"
        + "Цена: " + str(price) + "\n\n"
        + levels_text + "\n"
        + news_text
        + market_news
    )

def format_evening_summary(open_p, close_p, high_p, low_p,
                            signals_today, news_results, tomorrow_news):
    sig_text = ""
    for s in signals_today:
        emoji = "🟢" if s['type'] == 'LONG' else "🔴"
        medal = get_medal(s.get('level', 1))
        if s.get('win'):
            result = "→ TP" + str(s.get('tp_hit', '')) + " ✅"
        else:
            result = "→ SL ❌"
        sig_text += emoji + " " + medal + " " + s['type'] + " · " + s['time'] + " · вход " + str(s['entry']) + " " + result + "\n"
    if not sig_text:
        sig_text = "Сигналов не было\n"

    return (
        "🌙 ИТОГИ ДНЯ · " + NAME + "\n\n"
        + "Открытие: " + str(open_p) + " · Закрытие: " + str(close_p) + "\n"
        + "Хай: " + str(high_p) + " · Лой: " + str(low_p) + "\n\n"
        + "СИГНАЛЫ:\n" + sig_text + "\n"
        + "ЗАВТРА:\n"
        + "PDH: " + str(high_p) + " · PDL: " + str(low_p) + "\n"
        + (tomorrow_news if tomorrow_news else "Важных новостей нет")
    )

def format_warning_20h(price, direction, lots):
    emoji = "🟢" if direction == "LONG" else "🔴"
    return (
        "⚠️ 19:30 GMT\n\n"
        + emoji + " " + direction + " · " + str(lots) + " лот · " + NAME + "\n"
        + "Цена: " + str(price) + "\n\n"
        + "Закрой позицию до 20:00 GMT"
    )

def test_connection():
    try:
        resp = requests.get(BASE_URL + "/getMe", timeout=10)
        return resp.status_code == 200
    except:
        return False
