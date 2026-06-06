import requests
from datetime import datetime
from config import HIGH_IMPACT_NEWS, NEWS_PAUSE_MINUTES

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

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
                        'time': ev.get('time',''),
                        'forecast': ev.get('forecast','—'),
                        'previous': ev.get('previous','—'),
                    })
            return high_impact
    except Exception as e:
        print(f"Ошибка новостей: {e}")
        return []

def get_todays_news():
    all_news = get_news_calendar()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    return [n for n in all_news if today in n.get('date','')]

def format_news_for_briefing(news_list):
    if not news_list:
        return "📰 Важных новостей сегодня нет\n"
    text = "📰 НОВОСТИ СЕГОДНЯ:\n"
    for n in news_list:
        text += f"🔴 {n['time']} GMT · {n['title']}\n"
        text += f"   Прогноз: {n['forecast']} | Пред: {n['previous']}\n"
    return text

def analyze_news(news, direction):
    title = news.get('title','').upper()
    forecast = news.get('forecast','')
    previous = news.get('previous','')
    if 'FOMC' in title or 'NFP' in title or 'NON-FARM' in title:
        return {
            'verdict': 'WAIT',
            'label': '⏳ ЖДЁМ',
            'action': 'Закрываем за 30 мин. Входим после первых 15 мин.'
        }
    try:
        f = float(forecast.replace('%','').replace('K',''))
        p = float(previous.replace('%','').replace('K',''))
        if 'CPI' in title or 'PPI' in title:
            bull = f < p
        else:
            bull = f > p
        if bull and direction == 'LONG':
            return {'verdict':'HOLD','label':'✅ ДЕРЖИМ','action':'Прогноз бычий — держим лонг'}
        elif not bull and direction == 'SHORT':
            return {'verdict':'HOLD','label':'✅ ДЕРЖИМ','action':'Прогноз медвежий — держим шорт'}
        elif bull and direction == 'SHORT':
            return {'verdict':'CLOSE','label':'🔴 ЗАКРЫВАЕМ','action':'Прогноз бычий — закрываем шорт'}
        else:
            return {'verdict':'CLOSE','label':'🔴 ЗАКРЫВАЕМ','action':'Прогноз медвежий — закрываем лонг'}
    except:
        return {'verdict':'NEUTRAL','label':'⚪ НЕЙТРАЛЬНО','action':'Не влияет'}
