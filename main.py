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
    format_morning_briefing, format_warning_20h
)
from config import CHECK_INTERVAL, SYMBOL

state = {
    'last_level': 0,
    'last_direction': None,
    'open_position': None,
    'last_briefing': None,
    'warned_20h': False
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
        news_list = get_todays_news()
        news_text = format_news_for_briefing(news_list)
        now = datetime.utcnow()
        session = get_session(now.hour)
        msg = format_morning_briefing(
            price=round(last['close'], 2),
            ema200=round(last['ema200'], 2),
            rsi=round(last['rsi'], 1),
            levels=levels,
            news_text=news_text,
            session=session
        )
        send_message(msg)
        state['last_briefing'] = today
        state['warned_20h'] = False
        print("✅ Брифинг отправлен")
    except Exception as e:
        print(f"❌ Ошибка брифинга: {e}")

def check_signals():
    now = datetime.utcnow()
    if now.hour == 19 and now.minute >= 30 and not state['warned_20h']:
        if state['open_position']:
            pos = state['open_position']
            price = get_current_price(SYMBOL)
            msg = format_warning_20h(price, pos['direction'], pos['lots'])
            send_message(msg)
            state['warned_20h'] = True
        return
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
        print(f"{now.strftime('%H:%M')} | {signal['price']} | RSI:{signal['rsi']} | Сигнал:{level} {direction or ''}")
        if level == 0:
            return
        if level == state['last_level'] and direction == state['last_direction']:
            return
        if level < state['last_level'] and direction == state['last_direction']:
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
        state['last_level'] = level
        state['last_direction'] = direction
        print(f"✅ Сигнал {level} {direction} отправлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def reset_daily():
    state['last_level'] = 0
    state['last_direction'] = None
    state['open_position'] = None
    state['warned_20h'] = False
    print("🔄 Сброс состояния")

def main():
    print("🚀 Запуск MES Trading Signal Bot...")
    if not test_connection():
        print("❌ Ошибка Telegram!")
        return
    print("✅ Telegram подключён")
    schedule.every().day.at("08:00").do(morning_briefing)
    schedule.every().day.at("21:00").do(reset_daily)
    now = datetime.utcnow()
    if 8 <= now.hour < 10:
        morning_briefing()
    print(f"⏱ Проверка каждые {CHECK_INTERVAL} сек...")
    while True:
        try:
            schedule.run_pending()
            check_signals()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\n⛔ Остановлен")
            send_message("⛔ Бот остановлен")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
