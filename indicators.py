import pandas as pd
import numpy as np

def calc_ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(prices, fast)
    ema_slow = calc_ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_all(df, ema_period=200):
    df = df.copy()
    df['ema200'] = calc_ema(df['close'], ema_period)
    df['rsi'] = calc_rsi(df['close'])
    df['macd'], df['macd_signal'], df['macd_hist'] = calc_macd(df['close'])
    df['trend'] = np.where(df['close'] > df['ema200'], 'bull', 'bear')
    df['macd_cross_up'] = (
        (df['macd'] > df['macd_signal']) &
        (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    )
    df['macd_cross_down'] = (
        (df['macd'] < df['macd_signal']) &
        (df['macd'].shift(1) >= df['macd_signal'].shift(1))
    )
    return df

def detect_sr_levels(df, lookback=20):
    recent = df.tail(lookback)
    prev = df.tail(500)
    return {
        'resistance': round(recent['high'].max(), 2),
        'support': round(recent['low'].min(), 2),
        'pdh': round(prev['high'].iloc[:-lookback].max(), 2),
        'pdl': round(prev['low'].iloc[:-lookback].min(), 2),
    }

def detect_fvg(df):
    if len(df) < 3:
        return False
    gap = abs(df['close'].iloc[-1] - df['close'].iloc[-3])
    return gap > df['close'].iloc[-1] * 0.005
