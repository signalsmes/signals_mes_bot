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

    level_long = near_support or near_pdl or near_ema or fvg
    level_short = near_resistance or near_pdh or near_ema or fvg

    macd_bull = last['macd_cross_up']
    macd_bear = last['macd_cross_down']

    # SL дистанция
    sl_dist = price * 0.003

    result = {
        'level': 0,
        'direction': None,
        'price': round(price, 2),
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
        'reason': [],
        'averaging': False
    }

    # ── ЛОНГ ──────────────────────────────────────────────────────

    # Уровень 3 — все условия совпали
    if (rsi < RSI_EXTREME_LONG and
        macd_bull and macd < -3 and
        level_long and trend == 'bull'):
        result.update({
            'level': 3,
            'direction': 'LONG',
            'lots': SIGNAL_3_LOTS,
            'sl': round(price - sl_dist * 1.5, 2),
            'tp': round(price + sl_dist * 3, 2),
            'reason': ['RSI экстремум', 'MACD разворот', 'Уровень']
        })

    # Уровень 2
    elif (rsi < RSI_OVERSOLD and
          (macd_bull or macd < -2) and
          level_long):
        result.update({
            'level': 2,
            'direction': 'LONG',
            'lots': SIGNAL_2_LOTS,
            'sl': round(price - sl_dist, 2),
            'tp': round(price + sl_dist * 2, 2),
            'reason': ['RSI перепродан', 'Цена у уровня']
        })

    # Уровень 1
    elif (rsi < 38 and macd < 0 and
          (level_long or fvg) and
          trend == 'bull'):
        result.update({
            'level': 1,
            'direction': 'LONG',
            'lots': SIGNAL_1_LOTS,
            'sl': round(price - sl_dist * 0.8, 2),
            'tp': round(price + sl_dist * 1.5, 2),
            'reason': ['RSI снижается', 'Тренд бычий']
        })

    # ── ШОРТ ──────────────────────────────────────────────────────

    # Уровень 3
    elif (rsi > RSI_EXTREME_SHORT and
          macd_bear and macd > 3 and
          level_short and trend == 'bear'):
        result.update({
            'level': 3,
            'direction': 'SHORT',
            'lots': SIGNAL_3_LOTS,
            'sl': round(price + sl_dist * 1.5, 2),
            'tp': round(price - sl_dist * 3, 2),
            'reason': ['RSI экстремум', 'MACD разворот', 'Уровень']
        })

    # Уровень 2
    elif (rsi > RSI_OVERBOUGHT and
          (macd_bear or macd > 2) and
          level_short):
        result.update({
            'level': 2,
            'direction': 'SHORT',
            'lots': SIGNAL_2_LOTS,
            'sl': round(price + sl_dist, 2),
            'tp': round(price - sl_dist * 2, 2),
            'reason': ['RSI перекуплен', 'Цена у уровня']
        })

    # Уровень 1
    elif (rsi > 62 and macd > 0 and
          (level_short or fvg) and
          trend == 'bear'):
        result.update({
            'level': 1,
            'direction': 'SHORT',
            'lots': SIGNAL_1_LOTS,
            'sl': round(price + sl_dist * 0.8, 2),
            'tp': round(price - sl_dist * 1.5, 2),
            'reason': ['RSI растёт', 'Тренд медвежий']
        })

    # ── УСРЕДНЕНИЕ ────────────────────────────────────────────────
    # Сигнал усреднения когда RSI на экстремуме
    if result['level'] == 0:
        if rsi < 25 and level_long:
            result.update({
                'level': 2,
                'direction': 'LONG',
                'lots': 1,
                'sl': round(price - sl_dist, 2),
                'tp': round(price + sl_dist * 2, 2),
                'averaging': True,
                'reason': ['RSI экстремум', 'Усреднение']
            })
        elif rsi > 75 and level_short:
            result.update({
                'level': 2,
                'direction': 'SHORT',
                'lots': 1,
                'sl': round(price + sl_dist, 2),
                'tp': round(price - sl_dist * 2, 2),
                'averaging': True,
                'reason': ['RSI экстремум', 'Усреднение']
            })

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
        return False, f"После {STOP_TRADING_HOUR}:00 GMT"
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
            ('PDH', levels['pdh'],
             abs(price - levels['pdh']) / price < zone),
            ('PDL', levels['pdl'],
             abs(price - levels['pdl']) / price < zone),
            ('Сопротивление', levels['resistance'],
             abs(price - levels['resistance']) / price < zone),
            ('Поддержка', levels['support'],
             abs(price - levels['support']) / price < zone),
            ('EMA200', round(ema200, 2),
             abs(price - ema200) / price < zone),
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
    wr = len(wins) / len(trades_history) * 100 if trades_history else 0
    pf = gross_p / gross_l if gross_l > 0 else 0
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
        'longs': len([t for t in trades_history
                      if t.get('type') == 'LONG']),
        'shorts': len([t for t in trades_history
                       if t.get('type') == 'SHORT']),
    }
