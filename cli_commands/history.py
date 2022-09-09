import requests

from vidbot import api_key


def history(last_days,last_records):
    req = requests.get('https://app.ayrshare.com/api/history',
                       params={'lastDays': last_days, 'lastRecords': last_records},
                       headers={'Authorization': f'Bearer {api_key}'})

    from pprint import pprint
    pprint(req.json())