import requests
from selenium import webdriver
from bs4 import BeautifulSoup
from multiprocessing import Pool
import re
import schedule, time
import sqlite3
import json
import os
import urllib.parse
from telegram import Bot
from make_db import get_user_list, insert_song, is_song, make_db

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
        kpop_chart_100.extend([[title.text, artist.text] for title, artist in zip(soup.select(title_sel), soup.select(artist_sel))])
    if os.path.exists(latest_path):
        with open(latest_path) as f:
            data = json.load(f)
        if 'kpop' in data.keys():
            before = data['kpop']
            if len(before) > 300:
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
            for chat_id in get_user_list(c, "kpop", ''): #TODO artist):
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
            if len(before) > 300:
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
            for chat_id in get_user_list(c, "pop", ""):
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

class SongDownloadLink():
    def __init__(self):
        self.processe_num = 4

    def start_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument("disable-gpu")
        return webdriver.Chrome('chromedriver', chrome_options=options)

    def crawl_kpop_song_list(self, page_num = 1):
        print("page num : ", page_num)
        url = "https://lover.ne.kr:124/bbs/zboard.php?category=1&id=sitelink1&page={}&page_num=24&sn=off&ss=on&sc=on" \
                  "&keyword=&select_arrange=headnum&desc=asc".format(page_num)
        type = 'kpop'
        driver = self.start_driver()
        driver.get(url)
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        song_info = []
        soup_songs = soup.select("td[align='left']")[5:]
        for i in soup_songs:
            info = i.text.split(' - ')
            artist = info[0].strip()
            song = info[1].strip()
            link = "https://lover.ne.kr:124/bbs/" + i.select('a')[0]['href']
            song_info.append((type,[song, artist, link]))
        driver.quit()
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        new_song_info = [song for song in song_info if not is_song(c, type, song[1])]
        c.close()
        conn.close()
        song_infos = [song_info[i:i + 5] for i in range(0, len(new_song_info), 5)]
        for song_info in song_infos:
            pool = Pool(processes=self.processe_num)
            pool.map(self.get_download_link, song_info)
            pool.close()
            pool.join()
        if new_song_info:
            self.crawl_kpop_song_list(page_num=page_num+1)

    def crawl_pop_song_list(self, page_num = 1):
        print("page num : ", page_num)
        url = "https://lover.ne.kr:124/bbs/zboard.php?category=4&id=sitelink1&page={}&page_num=24&sn=off&ss=on&sc=on&" \
              "keyword=&select_arrange=headnum&desc=asc".format(page_num)
        type = 'pop'
        driver = self.start_driver()
        driver.get(url)
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        song_info = []
        soup_songs = soup.select("td[align='left']")
        for i in soup_songs:
            info = i.text.split(' - ')
            artist = info[0].strip()
            song = info[1].strip()
            link = "https://lover.ne.kr:124/bbs/" + i.select('a')[0]['href']
            song_info.append((type, [song, artist, link]))
        driver.quit()
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        new_song_info = [song for song in song_info if not is_song(c, type, song[1])]
        c.close()
        conn.close()
        song_infos = [song_info[i:i + 5] for i in range(0, len(new_song_info), 5)]
        for song_info in song_infos:
            pool = Pool(processes=self.processe_num)
            pool.map(self.get_download_link, song_info)
            pool.close()
            pool.join()
        if new_song_info:
            self.crawl_pop_song_list(page_num=page_num+1)

    def get_download_link(self, song_info):
        type, song = song_info[0], song_info[1]
        link = song[2]
        driver = self.start_driver()
        driver.get(link)
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        url = ""
        for s in soup.select('iframe'):
            try:
                iframe_link = s['src']
                if iframe_link.startswith('..'):
                    url = "https://lover.ne.kr:124" + iframe_link[2:].replace('/link', '')
            except KeyError:
                continue
        driver.get(url)
        html_source = driver.page_source
        driver.quit()
        soup = BeautifulSoup(html_source, 'html.parser')
        download_soup = soup.select("script[type='text/javascript']")[-1]
        download_link = re.findall('https://.*"', str(download_soup))[0][:-1]
        song[2] = download_link
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        if not is_song(c, type, song):
            insert_song(c, type, song)
        conn.commit()
        c.close()
        conn.close()


def get_youtube_url(keyword):
    url = 'https://www.youtube.com/results?search_query='+ urllib.parse.quote_plus(keyword)
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    for link in soup.findAll('a', {'class': 'yt-uix-tile-link'}):
        return 'https://www.youtube.com' + link.get('href')

if __name__=='__main__':
    for i in range(1):
        print(i)
        make_db()
        Chrome = SongDownloadLink()
        Chrome.crawl_kpop_song_list()

        # get_kpop_100()
        # get_pop_200()


    # schedule.every(3).minutes.do(get_kpop_100)
    # schedule.every(3).minutes.do(get_pop_200)
    #
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)