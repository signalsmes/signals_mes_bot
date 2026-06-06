from indicators import calc_all, detect_sr_levels, detect_fvg
from config import *
from datetime import datetime

def get_signal_level(df):
    df = calc_all(df)
    levels = detect_sr_levels(df)
    fvg = detect_fvg(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last['close']
    rsi = last['rsi']
    macd = last['macd']
    macd_sig = last['macd_signal']
    ema200 = last['ema200']
    trend = last['trend']
    near_support = abs(price - levels['support']) / price < 0.003
    near_resistance = abs(price - levels['resistance']) / price < 0.003
    near_pdl = abs(price - levels['pdl']) / price < 0.004
    near_pdh = abs(price - levels['pdh']) / price < 0.004
    near_ema = abs(price - ema200) / price < 0.003
    level_long = near_support or near_pdl or near_ema
    level_short = near_resistance or near_pdh or near_ema
    macd_bull = last['macd_cross_up']
    macd_bear = last['macd_cross_down']
    result = {
        'level': 0, 'direction': None,
        'price': price, 'rsi': round(rsi, 1),
        'macd': round(macd, 2),
        'macd_signal': round(macd_sig, 2),
        'ema200': round(ema200, 2),
        'trend': trend, 'levels': levels,
        'fvg': fvg, 'lots': 0,
        'sl': 0, 'tp': 0, 'reason': []
    }
    if rsi < RSI_EXTREME_LONG and macd_bull and macd < -3 and level_long and trend == 'bull':
        result.update({'level': 3, 'direction': 'LONG', 'lots': SIGNAL_3_LOTS,
            'sl': round(price - SL_POINTS, 2), 'tp': round(price + TP_POINTS * 1.5, 2),
            'reason': [f'RSI={rsi:.1f} ЭКСТРЕМУМ', 'MACD разворот', 'Уровень + EMA200', 'ВСЕ УСЛОВИЯ!']})
    elif rsi < RSI_OVERSOLD and (macd_bull or macd < -2) and level_long:
        result.update({'level': 2, 'direction': 'LONG', 'lots': SIGNAL_2_LOTS,
            'sl': round(price - SL_POINTS, 2), 'tp': round(price + TP_POINTS, 2),
            'reason': [f'RSI={rsi:.1f} перепродан', 'MACD в минусе', 'Цена у уровня']})
    elif rsi < 38 and macd < 0 and (level_long or fvg) and trend == 'bull':
        result.update({'level': 1, 'direction': 'LONG', 'lots': SIGNAL_1_LOTS,
            'sl': round(price - SL_POINTS * 0.8, 2), 'tp': round(price + TP_POINTS * 0.8, 2),
            'reason': [f'RSI={rsi:.1f} снижается', 'Тренд бычий', 'Ждём подтверждения']})
    elif rsi > RSI_EXTREME_SHORT and macd_bear and macd > 3 and level_short and trend == 'bear':
        result.update({'level': 
