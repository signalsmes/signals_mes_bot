import requests
from datetime import datetime, timezone, timedelta
from config import HIGH_IMPACT_NEWS, NEWS_PAUSE_MINUTES

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
DUBAI_TZ = timezone(timedelta(hours=4))

def get_dubai_time():
    return datetime.now(DUBAI_TZ)

def gmt_to_dubai(time_str):
    try:
        parts = time_str.split(':')
        h = int(parts[0]) + 4
        m = parts[1] if len(parts) > 1 else '00'
        if h >= 24:
            h -= 24
        return f"{h:02d}:{m}"
    except:
        return time_str

def get_news_calendar():
    try:
        resp = requests.get(CALENDAR_URL, timeout=10)
        if resp.status_code == 200:
            events = resp.json()
            high_impact = []
            for ev in events:
                if ev.get('impact') == 'High' and 'USD' in ev.get('country',''):
                    high_impact.append({
                        'title': ev.get('title',''),
                        'date': ev.get('date',''),
                        'time': gmt_to_dubai(ev.get('time','')),
                        'forecast': ev.get('forecast','—'),
                        'previous': ev.get('previous','—'),
                    })
            return high_impact
    except Exception as e:
        print(f"Calendar error: {e}")
        return []

def translate_impact(title):
    title_lower = title.lower()
    bullish_words = [
        'rate cut', 'stimulus', 'deal', 'agreement', 'growth',
        'beat', 'strong', 'rally', 'positive', 'recovery',
        'trade deal', 'ceasefire', 'peace', 'surge', 'rises',
        'record', 'jobs', 'employment', 'hiring'
    ]
    bearish_words = [
        'rate hike', 'inflation', 'recession', 'war', 'tariff',
        'selloff', 'weak', 'miss', 'negative', 'crisis',
        'default', 'sanction', 'conflict', 'falls', 'drops',
        'fears', 'concern', 'risk', 'tension'
    ]
    for word in bullish_words:
        if word in title_lower:
            return '📈 позитив для рынка'
    for word in bearish_words:
        if word in title_lower:
            return '📉 давление на рынок'
    return '⚪ следим за реакцией'

def translate_title(title):
    translations = {
        'federal reserve': 'ФРС',
        'fed ': 'ФРС ',
        'rate': 'ставка',
        'inflation': 'инфляция',
        'gdp': 'ВВП',
        'recession': 'рецессия',
        'trade': 'торговля',
        'tariff': 'тарифы',
        'president': 'президент',
        'deal': 'сделка',
        'agreement': 'соглашение',
        'china': 'Китай',
        'economy': 'экономика',
        'market': 'рынок',
        'stocks': 'акции',
        'rally': 'рост рынка',
        'selloff': 'распродажа',
        'trump': 'Трамп',
        'powell': 'Пауэлл',
        'jobs': 'рынок труда',
        'employment': 'занятость',
        'oil': 'нефть',
        'gold': 'золото',
        'dollar': 'доллар',
        'opec': 'ОПЕК',
        'europe': 'Европа',
        'russia': 'Россия',
        'ukraine': 'Украина',
        'war': 'война',
        'peace': 'мир',
        'ceasefire': 'перемирие',
        'sanctions': 'санкции',
        'interest rates': 'процентные ставки',
        'consumer price': 'потребительские цены',
        'record high': 'исторический максимум',
        'record low': 'исторический минимум',
        'beats expectations': 'превысил прогноз',
        'misses expectations': 'ниже прогноза',
        'holds steady': 'без изменений',
        'cuts rates': 'снижает ставку',
        'raises rates': 'повышает ставку',
        's&p 500': 'S&P 500',
        'wall street': 'Уолл-стрит',
        'nasdaq': 'Nasdaq',
    }
    result = title
    for eng, rus in translations.items():
        result = result.lower().replace(eng.lower(), rus)
    return result[0].upper() + result[1:] if result else title

def get_market_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://query1.finance.yahoo.com/v1/finance/search?q=S%26P500+market+economy&newsCount=15&lang=en-US"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            news_items = data.get('news', [])
            keywords = [
                'fed', 'federal reserve', 'rate', 'inflation', 'gdp',
                'recession', 'trade', 'tariff', 'president', 'deal',
                'agreement', 'war', 'china', 'economy', 'market',
                's&p', 'futures', 'stocks', 'rally', 'selloff',
                'trump', 'powell', 'jobs', 'employment', 'oil',
                'opec', 'russia', 'ukraine', 'ceasefire', 'peace',
                'sanctions', 'record', 'crisis', 'debt', 'budget'
            ]
            important = []
            seen = set()
            for item in news_items:
                title = item.get('title', '')
                if title in seen:
                    continue
                title_lower = title.lower()
                for kw in keywords:
                    if kw in title_lower:
                        important.append({
                            'title': title,
                            'title_ru': translate_title(title),
                            'impact': translate_impact(title),
                        })
                        seen.add(title)
                        break
            return important[:5]
    except Exception as e:
        print(f"News error: {e}")
        return []

def get_todays_news():
    all_news = get_news_calendar()
    today = datetime.now(DUBAI_TZ).strftime('%Y-%m-%d')
    return [n for n in all_news if today in n.get('date', '')]

def format_news_forecast(news_list):
    if not news_list:
        return ""
    text = "НОВОСТИ:\n"
    for n in news_list:
        text += f"{n['time']} · {n['title']}\n"
        try:
            f = float(n['forecast'].replace('%','').replace('K',''))
            p = float(n['previous'].replace('%','').replace('K',''))
            title = n['title'].upper()
            if 'FOMC' in title or 'NFP' in title:
                text += f"→ ждём волатильности · закрываем позиции за 30 мин\n"
            elif 'CPI' in title or 'PPI' in title:
                if f < p:
                    text += f"→ прогноз ниже пред · ожидаем рост\n"
                else:
                    text += f"→ прогноз выше пред · ожидаем снижение\n"
            elif f > p:
                text += f"→ прогноз выше пред · ожидаем рост\n"
            else:
                text += f"→ прогноз ниже пред · ожидаем снижение\n"
        except:
            text += f"→ следим за реакцией\n"
    return text + "\n"

def format_market_news():
    news = get_market_news()
    if not news:
        return ""
    text = "РЫНОК:\n"
    for n in news:
        text += f"· {n['title_ru']}\n"
        text += f"  {n['impact']}\n\n"
    return text
