from indicators import calc_all, detect_sr_levels, detect_fvg
from config import *
from datetime import datetime

def get_tf_data(df):
    if df is None or df.empty or len(df) < 30:
        return None
    df = calc_all(df)
    last = df.iloc[-1]
    return {
        'trend': last['trend'],
        'rsi': round(last['rsi'], 1),
        'macd': round(last['macd'], 2),
        'macd_hist': round(last['macd_hist'], 2),
        'ema200': round(last['ema200'], 2),
        'price': round(last['close'], 2),
        'cross_up': bool(last['macd_cross_up']),
        'cross_down': bool(last['macd_cross_down']),
    }

def calc_smart_sl(price, direction, levels):
    """SL за ближайшим уровнем/свингом + запас. Границы 12-25 пунктов."""
    buffer = 3
    min_sl = 12
    max_sl = 25

    if direction == "LONG":
        below = []
        for s in levels.get('swing_lows', []):
            if s < price:
                below.append(s)
        below.append(levels.get('support', 0))
        below.append(levels.get('pdl', 0))
        below = [b for b in below if b > 0 and b < price]
        if below:
            nearest = max(below)
            sl = nearest - buffer
            dist = price - sl
            if dist < min_sl:
                sl = price - min_sl
            elif dist > max_sl:
                sl = price - max_sl
            return round(sl, 2)
        return round(price - min_sl, 2)
    else:
        above = []
        for s in levels.get('swing_highs', []):
            if s > price:
                above.append(s)
        above.append(levels.get('resistance', 0))
        above.append(levels.get('pdh', 0))
        above = [a for a in above if a > price]
        if above:
            nearest = min(above)
            sl = nearest + buffer
            dist = sl - price
            if dist < min_sl:
                sl = price + min_sl
            elif dist > max_sl:
                sl = price + max_sl
            return round(sl, 2)
        return round(price + min_sl, 2)

def get_signal_level(dfs):
    tf1 = get_tf_data(dfs.get('1m'))
    tf3 = get_tf_data(dfs.get('3m'))
    tf5 = get_tf_data(dfs.get('5m'))
    tf15 = get_tf_data(dfs.get('15m'))
    tf30 = get_tf_data(dfs.get('30m'))

    if not tf3 or not tf15 or not tf5:
        return _no_signal()

    price = tf3['price']

    df15 = dfs.get('15m')
    if df15 is None or df15.empty:
        return _no_signal()
    df15c = calc_all(df15)
    levels = detect_sr_levels(df15c)
    fvg = False
    if dfs.get('3m') is not None:
        fvg = detect_fvg(dfs.get('3m'))

    # СТРОГАЯ согласованность: 30М + 15М + 5М все в одну сторону
    all_bull = (tf15['trend'] == 'bull' and tf5['trend'] == 'bull' and
                (tf30 is None or tf30['trend'] == 'bull'))
    all_bear = (tf15['trend'] == 'bear' and tf5['trend'] == 'bear' and
                (tf30 is None or tf30['trend'] == 'bear'))

    if not all_bull and not all_bear:
        return _no_signal()

    # MACD должен подтверждать на 5М И 3М
    macd_bull = tf5['macd'] > 0 and (tf3['macd'] > 0 or tf3['cross_up'])
    macd_bear = tf5['macd'] < 0 and (tf3['macd'] < 0 or tf3['cross_down'])

    if all_bull and not macd_bull:
        return _no_signal()
    if all_bear and not macd_bear:
        return _no_signal()

    # RSI средний по 3М и 1М
    rsi = tf3['rsi']
    if tf1:
        rsi = (tf3['rsi'] + tf1['rsi']) / 2

    near_pdl = abs(price - levels.get('pdl', 0)) / price < 0.004
    near_pdh = abs(price - levels.get('pdh', 0)) / price < 0.004
    near_sup = abs(price - levels.get('support', 0)) / price < 0.003
    near_res = abs(price - levels.get('resistance', 0)) / price < 0.003
    near_ema = abs(price - tf3['ema200']) / price < 0.003
    level_long = near_pdl or near_sup or near_ema or fvg
    level_short = near_pdh or near_res or near_ema or fvg

    result = _no_signal()
    result['price'] = price
    result['rsi'] = round(rsi, 1)
    result['macd'] = tf3['macd']
    result['macd_signal'] = tf3['macd']
    result['ema200'] = tf3['ema200']
    result['trend'] = tf3['trend']
    result['levels'] = levels
    result['fvg'] = fvg

    rsi_str = str(round(rsi, 1))

    # УРОВЕНЬ 3 — всё согласовано + RSI экстремум + уровень
    if all_bull and rsi < RSI_EXTREME_LONG and level_long:
        sl = calc_smart_sl(price, 'LONG', levels)
        result['level'] = 3
        result['direction'] = 'LONG'
        result['lots'] = SIGNAL_3_LOTS
        result['sl'] = sl
        result['reason'] = ['RSI=' + rsi_str, 'Все ТФ бычьи', 'Уровень']

    elif all_bear and rsi > RSI_EXTREME_SHORT and level_short:
        sl = calc_smart_sl(price, 'SHORT', levels)
        result['level'] = 3
        result['direction'] = 'SHORT'
        result['lots'] = SIGNAL_3_LOTS
        result['sl'] = sl
        result['reason'] = ['RSI=' + rsi_str, 'Все ТФ медвежьи', 'Уровень']

    # УРОВЕНЬ 2 — всё согласовано + RSI зона + уровень
    elif all_bull and rsi < RSI_OVERSOLD and level_long:
        sl = calc_smart_sl(price, 'LONG', levels)
        result['level'] = 2
        result['direction'] = 'LONG'
        result['lots'] = SIGNAL_2_LOTS
        result['sl'] = sl
        result['reason'] = ['RSI=' + rsi_str, '5М/15М/30М бычьи', 'Уровень']

    elif all_bear and rsi > RSI_OVERBOUGHT and level_short:
        sl = calc_smart_sl(price, 'SHORT', levels)
        result['level'] = 2
        result['direction'] = 'SHORT'
        result['lots'] = SIGNAL_2_LOTS
        result['sl'] = sl
        result['reason'] = ['RSI=' + rsi_str, '5М/15М/30М медвежьи', 'Уровень']

    return result

def _no_signal():
    return {
        'level': 0,
        'direction': None,
        'price': 0,
        'rsi': 50,
        'macd': 0,
        'macd_signal': 0,
        'ema200': 0,
        'trend': 'bull',
        'levels': {},
        'fvg': False,
        'lots': 0,
        'sl': 0,
        'tp': 0,
        'reason': [],
        'averaging': False,
    }

def get_session(hour_gmt):
    for name, hours in SESSIONS.items():
        if hours['start'] <= hour_gmt < hours['end']:
            return name
    return 'After Hours'

def is_trading_allowed(dt):
    if dt.weekday() >= 5:
        return False, "Выходной"
    if dt.hour >= STOP_TRADING_HOUR:
        return False, "После " + str(STOP_TRADING_HOUR) + ":00 GMT"
    return True, "OK"

def check_level_approach(df_1h, df_4h):
    alerts = []
    for tf_name, df in [('1H', df_1h), ('4H', df_4h)]:
        if df is None or df.empty:
            continue
        df_calc = calc_all(df)
        levels = detect_sr_levels(df_calc)
        last = df_calc.iloc[-1]
        price = last['close']
        ema200 = last['ema200']
        zone = 0.006
        checks = [
            ('PDH', levels['pdh'], abs(price - levels['pdh']) / price < zone),
            ('PDL', levels['pdl'], abs(price - levels['pdl']) / price < zone),
            ('Сопротивление', levels['resistance'], abs(price - levels['resistance']) / price < zone),
            ('Поддержка', levels['support'], abs(price - levels['support']) / price < zone),
            ('EMA200', round(ema200, 2), abs(price - ema200) / price < zone),
        ]
        for name, level_price, condition in checks:
            if condition:
                alerts.append({
                    'tf': tf_name,
                    'type': name,
                    'price': round(price, 2),
                    'level': level_price,
                })
    return alerts

def get_weekly_stats(trades_history):
    if not trades_history:
        return None
    wins = [t for t in trades_history if t.get('win')]
    losses = [t for t in trades_history if not t.get('win')]
    total_pnl = sum(t.get('pnl', 0) for t in trades_history)
    gross_p = sum(t.get('pnl', 0) for t in wins)
    gross_l = abs(sum(t.get('pnl', 0) for t in losses))
    wr = 0
    if trades_history:
        wr = len(wins) / len(trades_history) * 100
    pf = 0
    if gross_l > 0:
        pf = gross_p / gross_l
    best = max(trades_history, key=lambda t: t.get('pnl', 0), default=None)
    worst = min(trades_history, key=lambda t: t.get('pnl', 0), default=None)
    return {
        'total': len(trades_history),
        'wins': len(wins),
        'losses': len(losses),
        'wr': round(wr, 1),
        'pnl': round(total_pnl, 2),
        'pf': round(pf, 2),
        'best': best,
        'worst': worst,
        'longs': len([t for t in trades_history if t.get('type') == 'LONG']),
        'shorts': len([t for t in trades_history if t.get('type') == 'SHORT']),
    }
