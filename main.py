import time
import schedule
from datetime import datetime
from data_feed import get_multi_timeframe, get_current_price
from strategy import get_signal_level, get_session, is_trading_allowed
from indicators import calc_all, detect_sr_levels
from news import get_todays_news, format_news_for_briefing
from telegram_bot import (
    send_message, test_connection,
    format_signal_1, format_signal_2, format_signal_3,
    format_averaging, format_tp_hit, format_sl_hit,
    format_morning_briefing, format_evening_summary,
    format_warning_20h, calc_tp
)
from config import CHECK_INTERVAL, SYMBOL

state = {
    'last_level': 0,
    'last_direction': None,
    'open_position': None,
    'last_briefing': None,
    'warned_20h': False,
    'signals_today': [],
    'day_open': None,
    'day_high': None,
    'day_low': None,
}

def morning_briefing():
    today = datetime.utcnow().date()
    if state['last_briefing'] == today:
        return
    try:
        dfs = get_multi_timeframe(SYMBOL)
        df = dfs.get('15m')
        if df is None or df.empty:
            return
        df_calc = calc_all(df)
        levels = detect_sr_levels(df)
        last = df_calc.iloc[-1]
        price = round(last['close'], 2)
        news_list = get_todays_news()

        # Session levels
        levels['asiaH'] = round(last['high'] * 1.003, 2)
        levels['asiaL'] = round(last['low'] * 0.997, 2)
        levels['lonH'] = round(last['high'] * 1.005, 2)
        levels['lonL'] = round(last['low'] * 0.995, 2)

        now = datetime.utcnow()
        session = get_session(now.hour)

        msg = format_morning_briefing(
            price=price,
            ema200=round(last['ema200'], 2),
            rsi=round(last['rsi'], 1),
            levels=levels,
            news_list=news_list,
            session=session
        )
        send_message(msg)

        # Reset daily state
        state['last_briefing'] = today
        state['warned_20h'] = False
        state['signals_today'] = []
        state['day_open'] = price
        state['day_high'] = price
        state['day_low'] = price
        state['last_level'] = 0
        state['last_direction'] = None
        print("Briefing sent")

    except Exception as e:
        print(f"Briefing error: {e}")

def evening_summary():
    try:
        price = get_current_price(SYMBOL)
        tomorrow_news = get_todays_news()
        tomorrow_text = ""
        if tomorrow_news:
            tomorrow_text = "Завтра: " + ", ".join([n['title'] for n in tomorrow_news[:2]])

        msg = format_evening_summary(
            open_p=state['day_open'] or price,
            close_p=price,
            high_p=state['day_high'] or price,
            low_p=state['day_low'] or price,
            signals_today=state['signals_today'],
            news_results=[],
            tomorrow_news=tomorrow_text
        )
        send_message(msg)
        print("Evening summary sent")
    except Exception as e:
        print(f"Evening summary error: {e}")

def check_tp_sl():
    """Проверяем достижение TP/SL для открытой позиции"""
    if not state['open_position']:
        return

    try:
        price = get_current_price(SYMBOL)
        pos = state['open_position']
        direction = pos['direction']
        tp_levels = pos['tp_levels']
        sl = pos['sl']
        tp_hit = pos.get('tp_hit', 0)

        # Обновляем дневной хай/лой
        if state['day_high'] and price > state['day_high']:
            state['day_high'] = price
        if state['day_low'] and price < state['day_low']:
            state['day_low'] = price

        # Проверяем SL
        if direction == 'LONG' and price <= sl:
            send_message(format_sl_hit(price, direction))
            # Обновляем журнал
            for s in state['signals_today']:
                if s.get('active'):
                    s['win'] = False
                    s['active'] = False
            state['open_position'] = None
            state['last_level'] = 0
            state['last_direction'] = None
            return

        if direction == 'SHORT' and price >= sl:
            send_message(format_sl_hit(price, direction))
            for s in state['signals_today']:
                if s.get('active'):
                    s['win'] = False
                    s['active'] = False
            state['open_position'] = None
            state['last_level'] = 0
            state['last_direction'] = None
            return

        # Проверяем TP уровни
        for i in range(tp_hit + 1, 5):
            tp_key = f'tp{i}'
            if tp_key not in tp_levels:
                continue
            tp_price = tp_levels[tp_key]
            hit = (direction == 'LONG' and price >= tp_price) or \
                  (direction == 'SHORT' and price <= tp_price)

            if hit:
                is_last = i == 4
                send_message(format_tp_hit(i, price, direction, last=is_last))
                state['open_position']['tp_hit'] = i

                if is_last:
                    for s in state['signals_today']:
                        if s.get('active'):
                            s['win'] = True
                            s['tp_hit'] = i
                            s['active'] = False
                    state['open_position'] = None
                    state['last_level'] = 0
                    state['last_direction'] = None
                break

    except Exception as e:
        print(f"TP/SL check error: {e}")

def check_signals():
    now = datetime.utcnow()

    # Предупреждение 19:30 GMT
    if now.hour == 19 and now.minute >= 30 and not state['warned_20h']:
        if state['open_position']:
            pos = state['open_position']
            price = get_current_price(SYMBOL)
            send_message(format_warning_20h(price, pos['direction'], pos['lots']))
            state['warned_20h'] = True
        return

    # Проверяем TP/SL
    check_tp_sl()

    allowed, reason = is_trading_allowed(now)
    if not allowed:
        return

    try:
        dfs = get_multi_timeframe(SYMBOL)
        df = dfs.get('3m')
        if df is None or df.empty or len(df) < 50:
            return

        signal = get_signal_level(df)
        session = get_session(now.hour)
        level = signal['level']
        direction = signal['direction']

        print(f"{now.strftime('%H:%M')} | {signal['price']} | RSI:{signal['rsi']} | {level} {direction or ''}")

        if level == 0:
            return

        # Не повторяем сигнал
        if level == state['last_level'] and direction == state['last_direction']:
            return
        if level < state['last_level'] and direction == state['last_direction']:
            return

        # Усреднение если уже в позиции
        if state['open_position'] and direction == state['open_position']['direction']:
            pos = state['open_position']
            if signal['rsi'] < 25 or signal['rsi'] > 75:
                send_message(format_averaging(signal, session))
                pos['lots'] += 1
                return

        # Новый сигнал
        if level == 1:
            msg = format_signal_1(signal, session)
        elif level == 2:
            msg = format_signal_2(signal, session)
        elif level == 3:
            msg = format_signal_3(signal, session)
        else:
            return

        send_message(msg)

        # Сохраняем позицию
        tp_levels = calc_tp(signal['price'], signal['sl'], direction)
        state['open_position'] = {
            'direction': direction,
            'entry': signal['price'],
            'sl': signal['sl'],
            'tp_levels': tp_levels,
            'lots': signal['lots'],
            'tp_hit': 0
        }

        # Журнал дня
        state['signals_today'].append({
            'type': direction,
            'time': now.strftime('%H:%M'),
            'entry': signal['price'],
            'win': None,
            'tp_hit': None,
            'active': True
        })

        state['last_level'] = level
        state['last_direction'] = direction
        print(f"Signal sent: {level} {direction}")

    except Exception as e:
        print(f"Signal error: {e}")

def main():
    print("Starting MES Trading Signal Bot...")
    if not test_connection():
        print("Telegram connection failed!")
        return
    print("Telegram connected")

    schedule.every().day.at("08:00").do(morning_briefing)
    schedule.every().day.at("21:00").do(evening_summary)

    now = datetime.utcnow()
    if 8 <= now.hour < 10:
        morning_briefing()

    print(f"Checking signals every {CHECK_INTERVAL} seconds...")

    while True:
        try:
            schedule.run_pending()
            check_signals()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("Stopped")
            send_message("Бот остановлен")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ ==
