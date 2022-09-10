import requests

from bot.webapp.config import DefaultConfig


def history(last_days,last_records):
    req = requests.get('https://app.ayrshare.com/api/history',
                       params={'lastDays': last_days, 'lastRecords': last_records},
                       headers={'Authorization': f'Bearer {DefaultConfig.MAILTRAP_API_KEY}'})

    from pprint import pprint
    pprint(req.json())