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

def get_kpop_100():
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',}
    latest_path = os.path.join(BASE_DIR, 'latest.json')
    kpop_chart_100 = []
    selectors = [['#lst50 > td:nth-child(6) > div > div > div.ellipsis.rank01 > span > a', '#lst50 > td:nth-child(6) > div > div > div.ellipsis.rank02 > span'],
                 ['#lst100 > td:nth-child(6) > div > div > div.ellipsis.rank01 > span > a', '#lst100 > td:nth-child(6) > div > div > div.ellipsis.rank02 > span']]
    for title_sel, artist_sel in selectors:
        response = requests.get("https://www.melon.com/chart/index.htm", headers=headers)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        kpop_chart_100.extend([title.text + ' - ' + artist.text for title, artist in zip(soup.select(title_sel), soup.select(artist_sel))])
    if os.path.exists(latest_path):
        with open(latest_path) as f:
            data = json.load(f)
        if 'kpop' in data.keys():
            before = data['kpop']
            if len(before) > 130:
                before = before[90:]
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
                                text='\n'.join(['{}. {}'.format(i, song) for i, song in enumerate(new_songs, start=1)]))
            c.close()
            conn.close()
        # for test
        # with open(latest_path, 'w') as f:
        #     data['kpop'] = []
        #     json.dump(data, f)
    else:
        with open(latest_path, 'w') as f:
            json.dump({'kpop': []}, f)

def get_pop_200():
    latest_path = os.path.join(BASE_DIR, 'latest.json')
    response = requests.get("https://www.billboard.com/charts/hot-100")
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    title_soup = soup.select("div > div.chart-list-item__title > span")
    artist_soup = soup.select("div > div.chart-list-item__artist")

    billboard200 = [title.text.strip() + " - " + artist.text.strip() for title, artist in zip(title_soup, artist_soup)]
    billboard200.insert(0, soup.select('div.chart-number-one__title')[0].text.strip() + ' - ' + soup.select('div.chart-number-one__artist')[0].text.strip())
    if os.path.exists(latest_path):
        with open(latest_path) as f:
            data = json.load(f)
        if 'pop' in data.keys():
            before = data['pop']
            if len(before) > 130:
                before = before[90:]
        else:
            before = []

        new_songs = [i for i in billboard200 if i not in before]
        with open(latest_path, 'w') as f:
            before.extend(new_songs)
            data['pop'] = before
            json.dump(data, f)
        if new_songs:
            conn = sqlite3.connect('user_info.db')
            c = conn.cursor()
            for chat_id in user_list(c, "pop"):
                bot.sendMessage(chat_id=chat_id,  # 580916113
                                text='\n'.join(['{}. {}'.format(i, song) for i, song in enumerate(new_songs, start=1)]))
            c.close()
            conn.close()
        # for test
        # with open(latest_path, 'w') as f:
        #     data['kpop'] = []
        #     json.dump(data, f)
    else:
        with open(latest_path, 'w') as f:
            json.dump({'pop': []}, f)

if __name__=='__main__':
    for i in range(1):
        print(i)
        get_kpop_100()
        get_pop_200()


    schedule.every(3).minutes.do(get_kpop_100)
    schedule.every(3).minutes.do(get_pop_200)

    while True:
        schedule.run_pending()
        time.sleep(1)