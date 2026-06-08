import yfinance as yf
import pandas as pd
from datetime import datetime

SYMBOLS = ["MES=F", "ES=F", "^GSPC"]

def get_price_data(symbol="MES=F", period="5d", interval="3m"):
    for sym in [symbol] + [s for s in SYMBOLS if s != symbol]:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                continue
            df.columns = [c.lower() for c in df.columns]
            df = df[['open','high','low','close','volume']].dropna()
            if len(df) > 5:
                return df
        except Exception as e:
            print(f"Error {sym}: {e}")
            continue
    return pd.DataFrame()

def get_current_price(symbol="MES=F"):
    for sym in [symbol] + [s for s in SYMBOLS if s != symbol]:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period='1d', interval='1m')
            if not df.empty:
                return round(float(df['Close'].iloc[-1]), 2)
            price = ticker.fast_info.last_price
            if price and price > 0:
                return round(float(price), 2)
        except:
            continue
    return 0.0

def get_multi_timeframe(symbol="MES=F"):
    return {
        '1m':  get_price_data(symbol, period='1d',  interval='1m'),
        '3m':  get_price_data(symbol, period='2d',  interval='2m'),
        '5m':  get_price_data(symbol, period='3d',  interval='5m'),
        '15m': get_price_data(symbol, period='5d',  interval='15m'),
        '30m': get_price_data(symbol, period='10d', interval='30m'),
        '1h':  get_price_data(symbol, period='30d', interval='1h'),
    }

def is_market_open():
    now = datetime.utcnow()
    weekday = now.weekday()
    hour = now.hour
    if weekday == 5:
        return False
    if weekday == 6 and hour < 23:
        return False
    if weekday == 4 and hour >= 22:
        return False
    return True
