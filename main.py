import time
import schedule
from datetime import datetime
from data_feed import get_multi_timeframe, get_current_price
from strategy import (
    get_signal_level, get_session, is_trading_allowed,
    check_level_approach, get_weekly_stats
)
from indicators import calc_all, detect_sr_levels
from news import get_todays_news
from telegram_bot import (
    send_message, test_connection,
    format_signal_1, format_signal_2, format_signal_3,
    format_averaging, format_tp_hit, format_sl_hit,
    format_level_alert, format_ema_alert,
    format_weekly_stats, format_morning_briefing,
    format_evening_summary, format_warning_20h, calc_tp
)
from config import CHECK_INTERVAL, SYMBOL

state = {
    'last_level': 0,
    'last_direction': None,
    'open_position': None,
    'last_briefing': None,
    'warned_20h': False,
    'signals_today': [],
    'week_trades': [],
    'day_open': None,
    'day_high': None,
    'day_low': None,
    'last_level_alert': {},
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

        state['last_briefing'] = today
        state['warned_20h'] = False
        state['signals_today'] = []
        state['day_open'] = price
        state['day_high'] = price
        state['day_low'] = price
        state['last_level'] = 0
        state['last_direction'] = None
        state['last_level_alert'] = {}
        print("Briefing sent")

    except Exception as e:
        print(f"Briefing error: {e}")

def evening_summary():
    try:
        dfs = get_multi_timeframe(SYMBOL)
        df = dfs.get('15m')
        close_price = get_current_price(SYMBOL)

        if df is not None and not df.empty:
            close_price = round(df['close'].iloc[-1], 2)
            open_price = state['day_open'] or round(df['open'].iloc[0], 2)
            high_price = state['day_high'] or round(df['high'].max(), 2)
            low_price = state['day_low'] or round(df['low'].min(), 2)
        else:
            open_price = state['day_open'] or close_price
            high_price = state['day_high'] or close_price
            low_price = state['day_low'] or close_price

        tomorrow_news = get_todays_news()
        tomorrow_text = ""
        if tomorrow_news:
            tomorrow_text = "Завтра: " + ", ".join(
                [n['title'] for n in tomorrow_news[:2]]
            )

        msg = format_evening_summary(
            open_p=open_price,
            close_p=close_price,
            high_p=high_price,
            low_p=low_price,
            signals_today=state['signals_today'],
            news_results=[],
            tomorrow_news=tomorrow_text
        )
        send_message(msg)
        print("Evening summary sent")
    except Exception as e:
        print(f"Evening summary error: {e}")

def weekly_stats():
    try:
        stats = get_weekly_stats(state['week_trades'])
        msg = format_weekly_stats(stats)
        send_message(msg)
        state['week_trades'] = []
        print("Weekly stats sent")
    except Exception as e:
        print(f"Weekly stats error: {e}")

def check_level_alerts():
    try:
        dfs = get_multi_timeframe(SYMBOL)
        df_1h = dfs.get('1h')

        import yfinance as yf
        ticker = yf.Ticker(SYMBOL)
        df_4h_raw = ticker.history(period='30d', interval='4h')
        df_4h = None
        if not df_4h_raw.empty:
            df_4h_raw.columns = [c.lower() for c in df_4h_raw.columns]
            df_4h = df_4h_raw[['open','high','low','close','volume']].dropna()

        alerts = check_level_approach(df_1h, df_4h)
        now = datetime.utcnow()

        for alert in alerts:
            key = f"{alert['type']}_{alert['tf']}"
            last_alert_time = state['last_level_alert'].get(key)

            if last_alert_time:
                hours_passed = (now - last_alert_time).seconds / 3600
                if hours_passed < 4:
                    continue

            if alert['type'] == 'EMA200':
                msg = format_ema_alert(
                    ema_value=alert['level'],
                    timeframe=alert['tf']
                )
            else:
                msg = format_level_alert(
                    level_name=alert['type'],
                    level_price=alert['level'],
                    timeframe=alert['tf']
                )

            send_message(msg)
            state['last_level_alert'][key] = now
            print(f"Level alert: {alert['type']} {alert['tf']}")
            time.sleep(2)

    except Exception as e:
        print(f"Level alert error: {e}")

def check_tp_sl():
    if not state['open_position']:
        return
    try:
        dfs = get_multi_timeframe(SYMBOL)
        df = dfs.get('3m')
        if df is None or df.empty:
            return
        price = round(df['close'].iloc[-1], 2)

        pos = state['open_position']
        direction = pos['direction']
        tp_levels = pos['tp_levels']
        sl = pos['sl']
        tp_hit = pos.get('tp_hit', 0)

        if state['day_high'] and price > state['day_high']:
            state['day_high'] = price
        if state['day_low'] and price < state['day_low']:
            state['day_low'] = price

        sl_hit = (direction == 'LONG' and price <= sl) or \
                 (direction == 'SHORT' and price >= sl)

        if sl_hit:
            send_message(format_sl_hit(price, direction))
            for s in state['signals_today']:
                if s.get('active'):
                    s['win'] = False
                    s['active'] = False
                    state['week_trades'].append({
                        **s, 'pnl': -abs(pos['entry'] - sl) * 5
                    })
            state['open_position'] = None
            state['last_level'] = 0
            state['last_direction'] = None
            return

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

                if i == 1:
                    state['open_position']['sl'] = pos['entry']
                    print(f"Trailing stop: breakeven {pos['entry']}")

                if is_last:
                    for s in state['signals_today']:
                        if s.get('active'):
                            s['win'] = True
                            s['tp_hit'] = i
                            s['active'] = False
                            pnl = abs(tp_price - pos['entry']) * pos['lots'] * 5
                            state['week_trades'].append({**s, 'pnl': pnl})
                    state['open_position'] = None
                    state['last_level'] = 0
                    state['last_direction'] = None
                break

    except Exception as e:
        print(f"TP/SL error: {e}")

def check_signals():
    now = datetime.utcnow()

    if now.hour == 19 and now.minute >= 30 and not state['warned_20h']:
        if state['open_position']:
            pos = state['open_position']
            dfs = get_multi_timeframe(SYMBOL)
            df = dfs.get('3m')
            price = round(df['close'].iloc[-1], 2) if df is not None and not df.empty else 0
            send_message(format_warning_20h(price, pos['direction'], pos['lots']))
            state['warned_20h'] = True
        return

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

        print(f"{now.strftime('%H:%M')} | "
              f"{signal['price']} | "
              f"RSI:{signal['rsi']} | "
              f"{level} {direction or ''}")

        if level == 0:
            return

        if (state['open_position'] and
                direction == state['open_position']['direction'] and
                signal.get('averaging')):
            pos = state['open_position']
            if signal['rsi'] < 25 or signal['rsi'] > 75:
                send_message(format_averaging(signal, session))
                pos['lots'] += 1
                return

        if (level == state['last_level'] and
                direction == state['last_direction']):
            return
        if (level < state['last_level'] and
                direction == state['last_direction']):
            return

        if level == 1:
            msg = format_signal_1(signal, session)
        elif level == 2:
            msg = format_signal_2(signal, session)
        elif level == 3:
            msg = format_signal_3(signal, session)
        else:
            return

        send_message(msg)

        tp_levels = calc_tp(signal['price'], signal['sl'], direction)
        state['open_position'] = {
            'direction': direction,
            'entry': signal['price'],
            'sl': signal['sl'],
            'tp_levels': tp_levels,
            'lots': signal['lots'],
            'tp_hit': 0
        }

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
        print(f"Signal: {level} {direction}")

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
    schedule.every().friday.at("20:30").do(weekly_stats)
    schedule.every().hour.do(check_level_alerts)

    now = datetime.utcnow()
    if 8 <= now.hour < 10:
        morning_briefing()

    print(f"Checking every {CHECK_INTERVAL} sec...")

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

if __name__ == "__main__":
    main()
