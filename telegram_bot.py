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

def format_signal(signal, session):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_tp(signal['price'], signal['sl'], d)
    return (
        f"{emoji} {d} · MES · Micro E-mini\n\n"
        f"Вход: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}"
    )

def format_signal_1(signal, session):
    return format_signal(signal, session)

def format_signal_2(signal, session):
    return format_signal(signal, session)

def format_signal_3(signal, session):
    return format_signal(signal, session)

def format_averaging(signal, session):
    d = signal['direction']
    emoji = "🟢" if d == "LONG" else "🔴"
    tp = calc_tp(signal['price'], signal['sl'], d)
    return (
        f"{emoji} {d} +1 · MES · Micro E-mini\n\n"
        f"Цена: {signal['price']}\n"
        f"SL:     {signal['sl']}\n\n"
        f"TP1:  {tp['tp1']}\n"
        f"TP2:  {tp['tp2']}\n"
        f"TP3:  {tp['tp3']}\n"
        f"TP4:  {tp['tp4']}"
    )

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
        f"Цена: {price}"
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

def format_news_forecast(news_list):
    if not news_list:
        return "📰 Важных новостей нет\n"
    text = "📰 НОВОСТИ СЕГОДНЯ:\n"
    for n in news_list:
        text += f"🔴 {n['time']} GMT · {n['title']}\n"
        text += f"   Прогноз: {n['forecast']} | Пред: {n['previous']}\n"
        try:
            f = float(n['forecast'].replace('%','').replace('K',''))
            p = float(n['previous'].replace('%','').replace('K',''))
            title = n['title'].upper()
            if 'FOMC' in title or 'NFP' in title:
                text += f"   Ждём волатильности · закрываем позиции за 30 мин\n"
            elif 'CPI' in title or 'PPI' in title:
                if f < p:
                    text += f"   Прогноз ниже пред → ожидаем рост\n"
                else:
                    text += f"   Прогноз выше пред → ожидаем снижение\n"
            elif f > p:
                text += f"   Прогноз выше пред → ожидаем рост\n"
            else:
                text += f"   Прогноз ниже пред → ожидаем снижение\n"
        except:
            text += f"   Следим за реакцией рынка\n"
        text += "\n"
    return text

def format_morning_briefing(price, ema200, rsi, levels, news_list, session):
    news_text = format_news_forecast(news_list)
    return (
        f"🌅 БРИФИНГ · MES · Micro E-mini\n\n"
        f"📍 Цена: {price}\n\n"
        f"УРОВНИ ДНЯ:\n"
        f"PDH: {levels['pdh']}\n"
        f"PDL: {levels['pdl']}\n"
        f"Asia High:    {levels.get('asiaH', '—')}\n"
        f"Asia Low:     {levels.get('asiaL', '—')}\n"
        f"London High:  {levels.get('lonH', '—')}\n"
        f"London Low:   {levels.get('lonL', '—')}\n\n"
        f"{news_text}"
        f"🎯 ПЛАН:\n"
        f"Лонг от PDL {levels['pdl']} · Шорт от PDH {levels['pdh']}"
    )

def format_evening_summary(open_p, close_p, high_p, low_p,
                            signals_today, news_results, tomorrow_news):
    sig_text = ""
    for s in signals_today:
        emoji = "🟢" if s['type'] == 'LONG' else "🔴"
        result = f"→ TP{s.get('tp_hit','')} ✅" if s.get('win') else "→ SL ❌"
        sig_text += f"{emoji} {s['type']} · {s['time']} · вход {s['entry']} {result}\n"
    if not sig_text:
        sig_text = "Сигналов не было\n"

    news_text = ""
    for n in news_results:
        news_text += f"🔴 {n['title']} · факт: {n['actual']} · прогноз: {n['forecast']}\n"
        news_text += f"   Реакция рынка: {n['reaction']}\n\n"
    if not news_text:
        news_text = "Новостей не было\n"

    return (
        f"🌙 ИТОГИ ДНЯ · MES · Micro E-mini\n\n"
        f"📊 Движение дня:\n"
        f"Открытие: {open_p} · Закрытие: {close_p}\n"
        f"Хай: {high_p} · Лой: {low_p}\n\n"
        f"📰 НОВОСТИ:\n"
        f"{news_text}"
        f"📈 СИГНАЛЫ СЕГОДНЯ:\n"
        f"{sig_text}\n"
        f"💡 ЗАВТРА:\n"
        f"PDH сегодня: {high_p}\n"
        f"PDL сегодня: {low_p}\n"
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
