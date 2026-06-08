import requests
from datetime import datetime, timezone, timedelta
from config import TELEGRAM_TOKEN, CHAT_ID, TICK_VALUE

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
DUBAI_TZ = timezone(timedelta(hours=4))

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
    else:
        return "🥉"

def get_level_name(signal):
    levels = signal.get('levels', {})
    price = signal['price']

    def near(a, b, pct=0.003):
        return abs(a - b) / b < pct if b else False

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
    for sl in levels.get('swing_lows', []):
        if near(price, sl):
            names.append('Swing Low')
            break
    for rn in levels.get('round_numbers', []):
        if near(price, rn, 0.002):
            names.append(f'Round {int(rn)}')
            break
    if signal.get('fvg'):
        names.append('FVG')
    return ' · '.join(names) if names else 'Уровень'

def format_signal(signal, session, avg=False):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_tp(signal['price'], signal['sl'], d)
    level_name = get_level_name(signal)
    avg_text = " +1" if avg else ""
    medal = get_medal(signal.get('level', 1))

    return (
        emoji + " " + d + avg_text + " · MESM26 (Micro E-mini S&P 500)\n"
        f"{medal}\n\n"
        f"Вход: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}\n\n"
        f"📐 {level_name}"
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
    trailing = "\n\nSL → безубыток" if tp_num == 1 and not last else ""
    return (
        f"✅ TP{tp_num} · MES · Micro E-mini\n\n"
        f"{emoji} {direction} · {action}\n"
        f"Цена: {price}"
        f"{trailing}"
    )

def format_sl_hit(price, direction):
    emoji = "🟢" if direction == "LONG" else "🔴"
    return (
        f"❌ SL · MES · Micro E-mini\n\n"
        f"{emoji} {direction} · позиция закрыта\n"
        f"Цена: {price}\n"
        f"Уровень SL достигнут"
    )

def format_level_alert(level_name, level_price, timeframe):
    return (
        f"📍 УРОВЕНЬ · MES · Micro E-mini\n\n"
        f"Цена у {level_name} · {timeframe}\n"
        f"Уровень: {level_price}"
    )

def format_ema_alert(ema_value, timeframe):
    return (
        f"📍 УРОВЕНЬ · MES · Micro E-mini\n\n"
        f"Цена касается EMA200 · {timeframe}\n"
        f"EMA200: {ema_value}"
    )

def format_weekly_stats(stats):
    if not stats:
        return "📊 Нет данных за неделю"
    pnl_sign = "+" if stats['pnl'] >= 0 else ""
    best_pnl = f"+${stats['best']['pnl']:.0f}" if stats.get('best') else "—"
    worst_pnl = f"-${abs(stats['worst']['pnl']):.0f}" if stats.get('worst') else "—"
    return (
        f"📊 СТАТИСТИКА НЕДЕЛИ · MES · Micro E-mini\n\n"
        f"Сделок:  {stats['total']}\n"
        f"Лонг:    {stats['longs']} · Шорт: {stats['shorts']}\n\n"
        f"Win Rate: {stats['wr']}%\n"
        f"Прибыльных: {stats['wins']}\n"
        f"Убыточных:  {stats['losses']}\n\n"
        f"P&L:     {pnl_sign}${stats['pnl']:.0f}\n"
        f"Лучшая:  {best_pnl}\n"
        f"Худшая:  {worst_pnl}\n\n"
        f"Profit Factor: {stats['pf']}"
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

    res_set = sorted(set(
        [levels['pdh']] +
        all_res[:3] +
        [r for r in rounds if r > price][:2]
    ), reverse=True)[:4]

    sup_set = sorted(set(
        [levels['pdl']] +
        all_sup[:3] +
        [r for r in rounds if r < price][:2]
    ), reverse=True)[:4]

    levels_text = "УРОВНИ:\n"
    for l in res_set:
        tag = "PDH" if l == levels['pdh'] else \
              "Weekly High" if l == levels.get('weekly_high') else \
              f"Round {int(l)}" if l in rounds else "Swing"
        levels_text += f"{l} ▪ {tag}\n"
    for l in sup_set:
        tag = "PDL" if l == levels['pdl'] else \
              "Weekly Low" if l == levels.get('weekly_low') else \
              f"Round {int(l)}" if l in rounds else "Swing"
        levels_text += f"{l} ▪ {tag}\n"
    levels_text += f"{round(ema200, 1)} ▪ EMA200\n"

    return (
        f"🌅 БРИФИНГ · MES · Micro E-mini\n"
        f"{date_str} · {time_str} Dubai\n\n"
        f"Цена: {price}\n\n"
        f"{levels_text}\n"
        f"{news_text}"
        f"{market_news}"
    )

def format_evening_summary(open_p, close_p, high_p, low_p,
                            signals_today, news_results, tomorrow_news):
    sig_text = ""
    for s in signals_today:
        emoji = "🟢" if s['type'] == 'LONG' else "🔴"
        medal = get_medal(s.get('level', 1))
        result = f"→ TP{s.get('tp_hit','')} ✅" if s.get('win') else "→ SL ❌"
        sig_text += f"{emoji} {medal} {s['type']} · {s['time']} · вход {s['entry']} {result}\n"
    if not sig_text:
        sig_text = "Сигналов не было\n"

    news_text = ""
    for n in news_results:
        news_text += f"{n['title']} · факт: {n['actual']} · прогноз: {n['forecast']}\n"
        news_text += f"  Реакция рынка: {n['reaction']}\n\n"
    if not news_text:
        news_text = "Новостей не было\n"

    return (
        f"🌙 ИТОГИ ДНЯ · MES · Micro E-mini\n\n"
        f"Открытие: {open_p} · Закрытие: {close_p}\n"
        f"Хай: {high_p} · Лой: {low_p}\n\n"
        f"НОВОСТИ:\n{news_text}"
        f"СИГНАЛЫ:\n{sig_text}\n"
        f"ЗАВТРА:\n"
        f"PDH: {high_p} · PDL: {low_p}\n"
        f"{tomorrow_news if tomorrow_news else 'Важных новостей нет'}"
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
                f"сигналы для торговли фьючерсом Micro-ES\n"
                f"на индексе S&P500.\n\n"
                f"Каждое утро ты получаешь брифинг\n"
                f"с ключевыми уровнями и новостями дня.\n\n"
                f"Сигналы основаны на авторской стратегии\n"
                f"мультитаймфреймного анализа.\n\n"
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
