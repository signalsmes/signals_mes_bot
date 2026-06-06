from indicators import calc_all, detect_sr_levels, detect_fvg
from config import *
from datetime import datetime

def get_signal_level(df):
    df = calc_all(df)
    levels = detect_sr_levels(df)
    fvg = detect_fvg(df)
    last = df.iloc[-1]
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
        'level': 0,
        'direction': None,
        'price': price,
        'rsi': round(rsi, 1),
        'macd': round(macd, 2),
        'macd_signal': round(macd_sig, 2),
        'ema200': round(ema200, 2),
        'trend': trend,
        'levels': levels,
        'fvg': fvg,
        'lots': 0,
        'sl': 0,
        'tp': 0,
        'reason': []
    }
    if rsi < RSI_EXTREME_LONG and macd_bull and macd < -3 and level_long and trend == 'bull':
        result['level'] = 3
        result['direction'] = 'LONG'
        result['lots'] = SIGNAL_3_LOTS
        result['sl'] = round(price - SL_POINTS, 2)
        result['tp'] = round(price + TP_POINTS * 1.5, 2)
        result['reason'] = ['RSI экстремум', 'MACD разворот', 'Уровень', 'ВСЕ УСЛОВИЯ!']
    elif rsi < RSI_OVERSOLD and level_long:
        result['level'] = 2
        result['direction'] = 'LONG'
        result['lots'] = SIGNAL_2_LOTS
        result['sl'] = round(price - SL_POINTS, 2)
        result['tp'] = round(price + TP_POINTS, 2)
        result['reason'] = ['RSI перепродан', 'Цена у уровня']
    elif rsi < 38 and macd < 0 and trend == 'bull':
        result['level'] = 1
        result['direction'] = 'LONG'
        result['lots'] = SIGNAL_1_LOTS
        result['sl'] = round(price - SL_POINTS * 0.8, 2)
        result['tp'] = round(price + TP_POINTS * 0.8, 2)
        result['reason'] = ['RSI снижается', 'Тренд бычий']
    elif rsi > RSI_EXTREME_SHORT and macd_bear and macd > 3 and level_short and trend == 'bear':
        result['level'] = 3
        result['direction'] = 'SHORT'
        result['lots'] = SIGNAL_3_LOTS
        result['sl'] = round(price + SL_POINTS, 2)
        result['tp'] = round(price - TP_POINTS * 1.5, 2)
        result['reason'] = ['RSI экстремум', 'MACD разворот', 'Сопротивление', 'ВСЕ УСЛОВИЯ!']
    elif rsi > RSI_OVERBOUGHT and level_short:
        result['level'] = 2
        result['direction'] = 'SHORT'
        result['lots'] = SIGNAL_2_LOTS
        result['sl'] = round(price + SL_POINTS, 2)
        result['tp'] = round(price - TP_POINTS, 2)
        result['reason'] = ['RSI перекуплен', 'Цена у уровня']
    elif rsi > 62 and macd > 0 and trend == 'bear':
        result['level'] = 1
        result['direction'] = 'SHORT'
        result['lots'] = SIGNAL_1_LOTS
        result['sl'] = round(price + SL_POINTS * 0.8, 2)
        result['tp'] = round(price - TP_POINTS * 0.8, 2)
        result['reason'] = ['RSI растёт', 'Тренд медвежий']
    return result

def get_session(hour_gmt):
    for name, hours in SESSIONS.items():
        if hours['start'] <= hour_gmt < hours['end']:
            return name
    return 'After Hours'

def is_trading_allowed(dt):
    if dt.weekday() >= 5:
        return False, "Выходной"
    if dt.hour >= STOP_TRADING_HOUR:
        return False, "После 20:00 GMT"
    return True, "OK"
