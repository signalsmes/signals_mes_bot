def check_level_alerts():
    try:
        dfs = get_multi_timeframe(SYMBOL)
        df_1h = dfs.get('1h')

        import yfinance as yf
        ticker = yf.Ticker(SYMBOL)
        df_4h_raw = ticker.history(period='30d', interval='4h')
        df_4h = None
        if not df_4h_raw.empty:
            df_4h_raw.columns = [c.lower() for c in df_4h_raw.columns]
            df_4h = df_4h_raw[['open','high','low','close','volume']].dropna()

        alerts = check_level_approach(df_1h, df_4h)
        now = datetime.utcnow()

        for alert in alerts:
            key = f"{alert['type']}_{alert['tf']}"
            last_alert_time = state['last_level_alert'].get(key)

            # Не отправляем если уже отправляли
            # менее 4 часов назад
            if last_alert_time:
                hours_passed = (now - last_alert_time).seconds / 3600
                if hours_passed < 4:
                    continue

            if alert['type'] == 'EMA200':
                msg = format_ema_alert(
                    ema_value=alert['level'],
                    timeframe=alert['tf']
                )
            else:
                msg = format_level_alert(
                    level_name=alert['type'],
                    level_price=alert['level'],
                    timeframe=alert['tf']
                )

            send_message(msg)
            state['last_level_alert'][key] = now
            print(f"Level alert sent: {alert['type']} {alert['tf']}")
            time.sleep(2)

    except Exception as e:
        print(f"Level alert error: {e}")
