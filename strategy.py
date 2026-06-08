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

def get_signal_level(dfs):
    tf1  = get_tf_data(dfs.get('1m'))
    tf3  = get_tf_data(dfs.get('3m'))
    tf5  = get_tf_data(dfs.get('5m'))
    tf15 = get_tf_data(dfs.get('15m'))
    tf30 = get_tf_data(dfs.get('30m'))

    if not tf3 or not tf15:
        return _no_signal()

    price = tf3['price']

    df15 = dfs.get('15m')
    if df15 is None or df15.empty:
        return _no_signal()
    df15c = calc_all(df15)
    levels = detect_sr_levels(df15c)
    fvg = detect_fvg(dfs.get('3m')) if dfs.get('3m') is not None else False

    # Старшие ТФ определяют направление
    senior_bull = tf15['trend'] == 'bull' and (tf30 is None or tf30['trend'] == 'bull')
    senior_bear = tf15['trend'] == 'bear' and (tf30 is None or tf30['trend'] == 'bear')

    if not senior_bull and not senior_bear:
        return _no_signal()

    # Младшие ТФ подтверждают
    junior_bull = tf3['macd'] > 0 or tf3['cross_up']
    junior_bear = tf3['macd'] < 0 or tf3['cross_down']
    if tf1:
        junior_bull = junior_bull and tf1['macd'] > 0
        junior_bear = junior_bear and tf1['macd'] < 0

    # RSI средний
    rsi = tf3['rsi']
    if tf1:
        rsi = (tf3['rsi'] + tf1['rsi']) / 2

    # Уровни
    near_pdl = abs(price - levels.get('pdl', 0)) / price < 0.004
    near_pdh = abs(price - levels.get('pdh', 0)) / price < 0.004
    near_sup = abs(price - levels.get('support', 0)) / price < 0.003
    near_res = abs(price - levels.get('resistance', 0)) / price < 0.003
    near_ema = abs(price - tf3['ema200']) / price < 0.003
    level_long  = near_pdl or near_sup or near_ema or fvg
    level_short = near_pdh or near_res or near_ema or fvg

    # SL жёсткий максимум 15 пунктов
    sl_pts = 15

    result = _no_signal()
    result['price'] = price
    result['rsi'] = round(rsi, 1)
    result['macd'] = tf3['macd']
    result['macd_signal'] = tf3['macd']
    result['ema200'] = tf3['ema200']
    result['trend'] = tf3['trend']
    result['levels'] = levels
    result['fvg'] = fvg

    # Уровень 3
    if senior_bull and junior_bull and rsi < RSI_EXTREME_LONG and level_long:
        result.update({'level':3,'direction':'LONG','lots':SIGNAL_3_LOTS,
            'sl':round(price-sl_pts,2),'tp':round(price+sl_pts*2,2),
            'reason':[f'RSI={rsi:.1f}','Все ТФ бычьи','Уровень']})
    elif senior_bear and junior_bear and rsi > RSI_EXTREME_SHORT and level_short:
        result.update({'level':3,'direction':'SHORT','lots':SIGNAL_3_LOTS,
            'sl':round(price+sl_pts,2),'tp':round(price-sl_pts*2,2),
            'reason':[f'RSI={rsi:.1f}','Все ТФ медвежьи','Уровень']})

    # Уровень 2
    elif senior_bull and rsi < RSI_OVERSOLD and level_long:
        result.update({'level':2,'direction':'LONG','lots':SIGNAL_2_LOTS,
            'sl':round(price-sl_pts,2),'tp':round(price+sl_pts*2,2),
            'reason':[f'RSI={rsi:.1f}','15М бычий','Уровень']})
    elif senior_bear and rsi > RSI_OVERBOUGHT and level_short:
        result.update({'level':2,'direction':'SHORT','lots':SIGNAL_2_LOTS,
            'sl':round(price+sl_pts,2),'tp':round(price-sl_pts*2,2),
            'reason':[f'RSI={rsi:.1f}','15М медвежий','Уровень']})

    # Уровень 1
    elif senior_bull and tf3['rsi'] < 38 and tf3['macd'] < 0 and (level_long or fvg):
        result.update({'level':1,'direction':'LONG','lots':SIGNAL_1_LOTS,
            'sl':round(price-sl_pts,2),'tp':round(price+sl_pts*1.5,2),
            'reason':[f'RSI={tf3["rsi"]}','15М бычий','Ждём']})
    elif senior_bear and tf3['rsi'] > 62 and tf3['macd'] > 0 and (level_short or fvg):
        result.update({'level':1,'direction':'SHORT','lots':SIGNAL_1_LOTS,
            'sl':round(price+sl_pts,2),'tp':round(price-sl_pts*1.5,2),
            'reason':[f'RSI={tf3["rsi"]}','15М медвежий','Ждём']})

    # Усреднение
    if result['level'] == 0:
        if rsi < 25 and senior_bull and level_long:
            result.update({'level':2,'direction':'LONG','lots':1,
                'sl':round(price-sl_pts,2),'tp':round(price+sl_pts*2,2),
                'averaging':True,'reason':[f'RSI={rsi:.1f}','Усреднение']})
        elif rsi > 75 and senior_bear and level_short:
            result.update({'level':2,'direction':'SHORT','lots':1,
                'sl':round(price+sl_pts,2),'tp':round(price-sl_pts*2,2),
                'averaging':True,'reason':[f'RSI={rsi:.1f}','Усреднение']})

    return result

def _no_signal():
    return {'level':0,'direction':None,'price':0,'rsi':50,'macd':0,
        'macd_signal':0,'ema200':0,'trend':'bull','levels':{},'fvg':False,
        'lots':0,'sl':0,'tp':0,'reason':[],'averaging':False}

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
            ('PDH', levels['pdh'], abs(price-levels['pdh'])/price < zone),
            ('PDL', levels['pdl'], abs(price-levels['pdl'])/price < zone),
            ('Сопротивление', levels['resistance'], abs(price-levels['resistance'])/price < zone),
            ('Поддержка', levels['support'], abs(price-levels['support'])/price < zone),
            ('EMA200', round(ema200,2), abs(price-ema200)/price < zone),
        ]
        for name, level_price, condition in checks:
            if condition:
                alerts.append({'tf':tf_name,'type':name,'price':round(price,2),'level':level_price})
    return alerts

def get_weekly_stats(trades_history):
    if not trades_history:
        return None
    wins = [t for t in trades_history if t.get('win')]
    losses = [t for t in trades_history if not t.get('win')]
    total_pnl = sum(t.get('pnl',0) for t in trades_history)
    gross_p = sum(t.get('pnl',0) for t in wins)
    gross_l = abs(sum(t.get('pnl',0) for t in losses))
    wr = len(wins)/len(trades_history)*100 if trades_history else 0
    pf = gross_p/gross_l if gross_l > 0 else 0
    best = max(trades_history, key=lambda t: t.get('pnl',0), default=None)
    worst = min(trades_history, key=lambda t: t.get('pnl',0), default=None)
    return {'total':len(trades_history),'wins':len(wins),'losses':len(losses),
        'wr':round(wr,1),'pnl':round(total_pnl,2),'pf':round(pf,2),
        'best':best,'worst':worst,
        'longs':len([t for t in trades_history if t.get('type')=='LONG']),
        'shorts':len([t for t in trades_history if t.get('type')=='SHORT'])}
