import yfinance as yf
import pandas as pd
from datetime import datetime

SYMBOLS = ["MES=F", "ES=F", "^GSPC"]

def get_price_data(symbol="MES=F", period="1mo", interval="5m"):
    """Получает данные с fallback на альтернативные тикеры"""
    for sym in [symbol] + [s for s in SYMBOLS if s != symbol]:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period=period, interval=interval)
            if df is None or df.empty:
                continue
            df.columns = [c.lower() for c in df.columns]
            if 'open' not in df.columns or 'close' not in df.columns:
                continue
            df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
            if len(df) > 5:
                return df
        except Exception as e:
            continue
    return pd.DataFrame()

def get_current_price(symbol="MES=F"):
    """Получает текущую цену с fallback"""
    for sym in [symbol] + [s for s in SYMBOLS if s != symbol]:
        try:
            ticker = yf.Ticker(sym)
            # Пробуем 1-минутные данные (ближайшие данные)
            try:
                df = ticker.history(period='1d', interval='1m')
                if df is not None and not df.empty:
                    price = float(df['Close'].iloc[-1])
                    if price > 0:
                        return round(price, 2)
            except:
                pass
            # Fallback на fast_info
            try:
                price = ticker.fast_info.last_price
                if price and price > 0:
                    return round(float(price), 2)
            except:
                pass
        except Exception as e:
            continue
    return 0.0

def get_multi_timeframe(symbol="MES=F"):
    """
    Получает данные по всем таймфреймам.
    Периоды увеличены для точной EMA200.
    """
    result = {}
    try:
        result['1m'] = get_price_data(symbol, period='5d', interval='1m')
        result['3m'] = get_price_data(symbol, period='10d', interval='2m')
        result['5m'] = get_price_data(symbol, period='1mo', interval='5m')
        result['15m'] = get_price_data(symbol, period='2mo', interval='15m')
        result['30m'] = get_price_data(symbol, period='3mo', interval='30m')
        result['1h'] = get_price_data(symbol, period='6mo', interval='1h')
    except Exception as e:
        print("Error in get_multi_timeframe: " + str(e))
    
    # Проверяем что хотя бы базовые ТФ есть
    if result['3m'].empty or result['15m'].empty:
        print("Critical: no data for 3m or 15m")
        return result
    
    return result

def is_market_open():
    """Проверяет открыт ли рынок (выходной день, время торговли)"""
    try:
        now = datetime.utcnow()
        weekday = now.weekday()
        hour = now.hour
        
        # Суббота и воскресенье
        if weekday == 5:
            return False
        if weekday == 6 and hour < 23:
            return False
        
        # Пятница после 22:00 UTC
        if weekday == 4 and hour >= 22:
            return False
        
        return True
    except Exception as e:
        print("Error in is_market_open: " + str(e))
        return True
