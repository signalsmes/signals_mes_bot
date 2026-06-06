import yfinance as yf
import pandas as pd

def get_price_data(symbol="ES=F", period="5d", interval="3m"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            ticker = yf.Ticker("^GSPC")
            df = ticker.history(period=period, interval=interval)
        df.columns = [c.lower() for c in df.columns]
        df = df[['open','high','low','close','volume']].dropna()
        return df
    except Exception as e:
        print(f"Ошибка данных: {e}")
        return pd.DataFrame()

def get_current_price(symbol="ES=F"):
    try:
        ticker = yf.Ticker(symbol)
        return float(ticker.fast_info.last_price)
    except:
        return 0.0

def get_multi_timeframe(symbol="ES=F"):
    return {
        '3m':  get_price_data(symbol, period='2d',  interval='2m'),
        '15m': get_price_data(symbol, period='5d',  interval='15m'),
        '1h':  get_price_data(symbol, period='30d', interval='1h'),
    }
