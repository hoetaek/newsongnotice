import requests
from bs4 import BeautifulSoup
import schedule, time
import sqlite3
import json
import os
from telegram import Bot
from make_db import user_list

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
bot = Bot(token=token)

def get_kpop():
    cookies = {
        'SCOUTER': 'x3mttqnd87j5f9',
        'PCID': '15519307755048607540802',
        'PC_PCID': '15519307755048607540802',
        'POC': 'MP10',
    }

    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Save-Data': 'on',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.melon.com/index.htm',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'If-None-Match': '"0:b578"',
    }

    response = requests.get('https://www.melon.com/chart/index.htm', headers=headers, cookies=cookies)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    kpop_chart_100 = [td.text for td in soup.select('#lst50 > td:nth-child(6) > div > div > div.ellipsis.rank01 > span > a')]

    latest_path = os.path.join(BASE_DIR, 'latest.json')
    if os.path.exists(latest_path):
        with open(latest_path) as f:
            data = json.load(f)
        if 'kpop' in data.keys():
            before = data['kpop']
            if len(before) > 20:
                before = before[7:]
        else:
            before = []

        new_songs = [i for i in kpop_chart_100 if i not in before]
        with open(latest_path, 'w') as f:
            before.extend(new_songs)
            data['kpop'] = before
            json.dump(data, f)
        if new_songs:
            conn = sqlite3.connect('user_info.db')
            c = conn.cursor()
            for chat_id in user_list(c, "kpop"):
                bot.sendMessage(chat_id=chat_id,  # 580916113
                                text='\n'.join(['{}. {}'.format(i, song) for i, song in enumerate(new_songs)]))
            c.close()
            conn.close()
        # for test
        # with open(latest_path, 'w') as f:
        #     data['kpop'] = []
        #     json.dump(data, f)


    else:
        with open(latest_path, 'w') as f:
            json.dump({'kpop': []}, f)

if __name__=='__main__':
    for i in range(2):
        print(i)
        get_kpop()


    schedule.every(3).minutes.do(get_kpop)

    while True:
        schedule.run_pending()
        time.sleep(1)