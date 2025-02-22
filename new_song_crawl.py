import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import schedule, time
import sqlite3
import json
import os
from telegram import Bot
from telegram.error import NetworkError
from make_db import get_user_list, insert_song, is_song
from music_file import download_mega_link, download_youtube_link, g_auth, upload_get_link, get_youtube_url
from new_data_manager import NewNotice

def get_pop_100():
    latest_path = os.path.join(BASE_DIR, 'latest.json')
    response = requests.get("https://www.billboard.com/charts/hot-100")
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    title_soup = soup.select("div > div.chart-list-item__title > span")
    artist_soup = soup.select("div > div.chart-list-item__artist")

    billboard200 = [title.text.strip() + " - " + artist.text.strip() for title, artist in zip(title_soup, artist_soup)]
    # billboard200.insert(0, soup.select('div.chart-number-one__title')[0].text.strip() + ' - ' + soup.select('div.chart-number-one__artist')[0].text.strip())
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
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        c.execute("SELECT user FROM users, charts, users_charts WHERE charts.id = users_charts.charts_id AND"
        " users.id = users_charts.user_id AND chart = '{}'".format("billboard"))
        user_list = [user[0] for user in c.fetchall()]
        for chat_id in user_list:
            for song in new_songs:
                song_name, artist = song.split(' - ')
                c.execute("SELECT link FROM pop_song WHERE song = ? COLLATE NOCASE AND artist = ? COLLATE NOCASE", (song_name, artist))
                link = c.fetchone()
                if link:
                    link = "다운로드 링크 : " + link[0] + '\n'
                else:
                    link = ""
                bot.sendMessage(chat_id= chat_id, #"580916113",
                                text= "빌보드 차트에 새로운 곡이 올라왔습니다\n" +
                                      song + '\n' +
                                      "유튜브 링크 : " + get_youtube_url(song) + '\n' +
                                      link +
                                      "\n알림을 그만 받고 싶다면 [/stop]을 터치해주세요.")

        c.close()
        conn.close()
        # for test
        # with open(latest_path, 'w') as f:
        #     data['kpop'] = []
        #     json.dump(data, f)
    else:
        with open(latest_path, 'w') as f:
            json.dump({'pop': []}, f)
        get_pop_100()
        return

class SongDownloadLink():
    def start_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument("disable-gpu")
        return webdriver.Chrome('chromedriver', chrome_options=options)

    def melon_chart(self):
        driver = self.start_driver()
        driver.get("https://www.melon.com/chart/index.htm")
        html = driver.page_source
        driver.quit()
        selectors = [['#lst50 > td:nth-child(6) > div > div > div.ellipsis.rank01 > span > a',
                      '#lst50 > td:nth-child(6) > div > div > div.ellipsis.rank02 > span'],
                     ['#lst100 > td:nth-child(6) > div > div > div.ellipsis.rank01 > span > a',
                      '#lst100 > td:nth-child(6) > div > div > div.ellipsis.rank02 > span']]
        kpop_chart_100 = []
        for title_sel, artist_sel in selectors:
            soup = BeautifulSoup(html, 'html.parser')
            kpop_chart_100.extend(
                [[title.text, artist.text] for title, artist in zip(soup.select(title_sel), soup.select(artist_sel))])
        melon_notice = NewNotice('songs.json')
        new_melon = melon_notice.compare_data("kpop", kpop_chart_100, limit=300)
        melon_notice.save_data("new_melon", new_melon)
        return kpop_chart_100

    def bill_chart(self):
        response = requests.get("https://www.billboard.com/charts/hot-100")
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        title_soup = soup.select("div > div.chart-list-item__title > span")
        artist_soup = soup.select("div > div.chart-list-item__artist")
        billboard200 = [title.text.strip() + " - " + artist.text.strip() for title, artist in
                        zip(title_soup, artist_soup)]
        bill_notice = NewNotice('songs.json')
        new_bill = bill_notice.compare_data("pop", billboard200, limit=300)
        bill_notice.save_data("new_bill", new_bill)
        return billboard200

    def crawl_kpop_song_list(self, current_page = 1, end_page = 25):
        print("kpop page num : ", current_page)
        url = "https://lover.ne.kr:124/bbs/zboard.php?id=sitelink7&page={}&select_arrange=headnum&desc=asc&category=1" \
              "&sn=off&ss=on&sc=on&keyword=&sn1=&divpage=1".format(current_page)
        song_type = 'kpop'
        driver = self.start_driver()
        driver.get(url)
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        song_info = []
        if current_page == 1:
            soup_songs = soup.select("td[align='left']")[4:]
        else:
            soup_songs = soup.select("td[align='left']")
        if not soup_songs:
            driver.quit()
            time.sleep(10600)
            self.crawl_kpop_song_list(current_page=current_page, end_page=end_page)
            return
        for i in soup_songs:
            info = i.text.split(' - ')
            artist = info[0].strip()
            song = info[1].strip()
            link = "https://lover.ne.kr:124/bbs/" + i.select('a')[0]['href'].rstrip()
            song_info.append((song_type,[song.replace("'", "''"), artist.replace("'", "''"), link]))
        driver.quit()
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        new_song_info = [song for song in song_info if not is_song(c, song_type, song[1])]
        c.close()
        conn.close()
        for i in new_song_info[:]:
            if self.get_download_link(i) == 'download limit':
                return "download limit"
        if new_song_info:# and current_page < end_page:
            try:
                self.crawl_kpop_song_list(current_page=current_page + 1)
            except NetworkError:
                print("network error, going to sleep for 300 sec")
                time.sleep(300)
                self.crawl_kpop_song_list(current_page=current_page + 1)

    def crawl_pop_song_list(self, current_page = 1, end_page = 25):
        print("pop page num : ", current_page)
        url = "https://lover.ne.kr:124/bbs/zboard.php?category=4&id=sitelink7&page={}&page_num=24&sn=off&ss=on&sc=on&" \
              "keyword=&select_arrange=headnum&desc=asc".format(current_page)
        song_type = 'pop'
        driver = self.start_driver()
        driver.get(url)
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        song_info = []
        soup_songs = soup.select("td[align='left']")
        if not soup_songs:
            driver.quit()
            time.sleep(10600)
            self.crawl_pop_song_list(current_page=current_page, end_page=end_page)
            return
        for i in soup_songs[1:]:
            info = i.text.split(' - ')
            artist = info[0].strip()
            song = info[1].strip()
            link = "https://lover.ne.kr:124/bbs/" + i.select('a')[0]['href'].rstrip()
            song_info.append((song_type, [song.replace("'", "''"), artist.replace("'", "''"), link]))
        driver.quit()
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        new_song_info = [song for song in song_info if not is_song(c, song_type, song[1])]
        c.close()
        conn.close()
        for i in new_song_info[:]:
            if self.get_download_link(i) == 'download limit':
                return "download limit"
        if new_song_info:# and current_page < end_page:
            try:
                self.crawl_pop_song_list(current_page=current_page + 1)
            except NetworkError:
                print("network error, going to sleep for 300 sec")
                time.sleep(300)
                self.crawl_pop_song_list(current_page=current_page + 1)

    def crawl_keyword_list(self, keyword, chat_id):
        url = "https://lover.ne.kr:124/bbs/zboard.php?category=1&id=sitelink1&page=1&page_num=24&sn=off&ss=on&sc=on&keyword=&select_arrange=headnum&desc=asc"
        driver = self.start_driver()
        driver.get(url)

        driver.find_element(By.XPATH, "//input[@type='text']").send_keys(keyword)
        driver.find_element(By.XPATH, "//input[@type='image']").click()
        driver.find_element(By.PARTIAL_LINK_TEXT, "무료노래다운사이트").click()
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        soup_songs = soup.select("td[align='left']")
        song_type = 'kpop'
        kpop_song_info = []
        for i in soup_songs:
            info = i.text.split(' - ')
            artist = info[0].strip()
            song = info[1].strip()
            if song.endswith('mp3'):
                song = song.replace('.mp3', '')
            link = "https://lover.ne.kr:124/bbs/" + i.select('a')[0]['href'].rstrip()
            kpop_song_info.append((song_type, [song.replace("'", "''"), artist.replace("'", "''"), link]))
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        kpop_new_song_info = [song for song in kpop_song_info if not is_song(c, song_type, song[1])]

        driver.find_element(By.PARTIAL_LINK_TEXT, "팝송다운사이트").click()
        song_type = 'pop'
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        soup_songs = soup.select("td[align='left']")
        pop_song_info = []
        for i in soup_songs:
            info = i.text.split(' - ')
            artist = info[0].strip()
            song = info[1].strip()
            link = "https://lover.ne.kr:124/bbs/" + i.select('a')[0]['href'].rstrip()
            pop_song_info.append(("pop", [song.replace("'", "''"), artist.replace("'", "''"), link]))
        pop_new_song_info = [song for song in pop_song_info if not is_song(c, song_type, song[1])]
        c.close()
        conn.close()
        new_song_info = kpop_new_song_info + pop_new_song_info
        driver.quit()
        if not new_song_info:
            bot.send_message(chat_id=chat_id, text="검색 결과가 존재하지 않습니다.")
        else:
            for i in new_song_info:
                result = self.get_download_link(i, search=True)
                if result:
                    bot.send_message(chat_id=chat_id, text=result)


    def get_download_link(self, song_info, search=False):
        song_type, song = song_info[0], song_info[1]
        song_name = song[0]
        song_artist = song[1]
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        song_exist = is_song(c, song_type, song_info[1])
        c.close()
        conn.close()
        if not song_exist:
            print(song[0], song[1])
            link = song[2]
            driver = self.start_driver()
            driver.get(link)

            html_source = driver.page_source
            soup = BeautifulSoup(html_source, 'html.parser')
            try:
                iframe_link = soup.select('iframe')[2]['src']
            except IndexError:
                print('db error')
                driver.quit()
                self.get_download_link(song_info, search=search)
                return
            except KeyError:
                try:
                    iframe_link = soup.select("[width='auto']")[0]['src']
                except IndexError:
                    iframe_link = soup.select("strong > a")[0]['href']
            if iframe_link.startswith('..'):
                iframe_link = iframe_link[2:].replace('/link', '').strip()
                while '/link' in iframe_link:
                    iframe_link = iframe_link.replace('/link', '')
                last_slash_dix = iframe_link.rfind('/')
                url = "https://lover.ne.kr:124" + iframe_link[:last_slash_dix+1] + 'a/e/' + iframe_link[last_slash_dix+1:]
                driver.get(url)
                html_source = driver.page_source
                soup = BeautifulSoup(html_source, 'html.parser')
                try:
                    download_soup = soup.select("script[language='javascript']")[0].text
                    download_link = ''.join([re.findall(r'".*"', i)[0].replace('"', '') for i in download_soup.splitlines()[1:4]])
                except IndexError:
                    url = "https://lover.ne.kr:124" + iframe_link[:last_slash_dix + 1] + 'a/b/' + iframe_link[
                                                                                                  last_slash_dix + 1:]
                    driver.get(url)
                    html_source = driver.page_source
                    soup = BeautifulSoup(html_source, 'html.parser')
                    try:
                        download_soup = soup.select("script[language='javascript']")[0].text
                        download_link = ''.join(
                            [re.findall(r'".*"', i)[0].replace('"', '') for i in download_soup.splitlines()[1:4]])
                    except IndexError:
                        url = "https://lover.ne.kr:124" + iframe_link[:last_slash_dix + 1] + 'a/z/' + iframe_link[
                                                                                                      last_slash_dix + 1:]
                        driver.get(url)
                        html_source = driver.page_source
                        soup = BeautifulSoup(html_source, 'html.parser')
                        download_soup = soup.select("script[language='javascript']")[0].text
                        download_link = ''.join(
                            [re.findall(r'".*"', i)[0].replace('"', '') for i in download_soup.splitlines()[1:4]])
                driver.quit()
                # try:
                #     download_link = re.findall('https://[^\"]*', str(download_soup))[0]
                # except IndexError:
                #     try:
                #         download_soup = soup.select("body > div > center:nth-child(13) > script:nth-child(2)")[0]
                #         download_link = re.findall('https://[^\"]*', str(download_soup))[0]
                #     except IndexError:
                #         download_link = soup.select("#sex > a")[0]['href']
                file, err = download_mega_link(download_link)
                if not file :
                    if err.endswith("Can't determine download url"):
                        pass
                    elif err.endswith("giving up"):
                        bot.sendMessage(chat_id="580916113",
                                        text="giving up, try again 300 sec later\n" + str(err))
                        time.sleep(200)
                        self.get_download_link(song_info, search=search)
                        return
                    elif err.endswith("returned 509"):
                        print("change the ip of the server and try again")
                        bot.sendMessage(chat_id="580916113",
                                        text="change the ip of the server and try again\n" + str(err))
                        self.get_download_link(song_info, search=search)
                        return
                    else:
                        bot.sendMessage(chat_id="580916113",
                                        text="unknow error program exit\n" + str(err))
                        raise SystemExit
                # Todo get rid of this
                # if song_type == 'kpop':
                #     file = song_artist + ' - ' + song_name + '.mp3'
            elif iframe_link.startswith("https://mega"):
                # driver.quit()
                file, err = download_mega_link(iframe_link)
                download_link = iframe_link
                if not file :
                    if err.endswith("Can't determine download url"):
                        pass
                    elif err.endswith("giving up"):
                        bot.sendMessage(chat_id="580916113",
                                        text="giving up, try again 300 sec later\n" + str(err))
                        time.sleep(200)
                        self.get_download_link(song_info, search=search)
                        return
                    elif err.endswith("returned 509"):
                        print("change the ip of the server and try again")
                        bot.sendMessage(chat_id="580916113",
                                        text="change the ip of the server and try again\n" + str(err))
                        self.get_download_link(song_info, search=search)
                        return
                    else:
                        bot.sendMessage(chat_id="580916113",
                                        text="unknow error program exit\n" + str(err))
                        raise SystemExit
                # if song_type == 'kpop': telegram.error.NetworkError
                #     file = song_artist + ' - ' + song_name + '.mp3'
            else:
                print("no mega file")
                driver.quit()
                if song_type == 'kpop':
                    file = download_youtube_link(song_name, song_artist, itunes=False)
                else:
                    file = download_youtube_link(song_name, song_artist)
                download_link = ""


            try:
                drive_auth = g_auth("my")
                song[2] = upload_get_link(drive_auth, file, "")
            except FileNotFoundError:
                song[2] = download_link

            conn = sqlite3.connect('user_info.db')
            c = conn.cursor()
            if search:
                insert_song(c, song_type, song)
                conn.commit()
                c.close()
                conn.close()
                return "곡: " + song_artist + " - " + song_name + \
                       '\n유튜브 링크 : ' + get_youtube_url(song_artist + " - " + song_name) + \
                       '\n다운로드 링크 : ' + song[2]
            insert_song(c, song_type, song)
            bot.sendMessage(chat_id="580916113",
                            text="곡: " + song_artist + " - " + song_name)
            for chat_id in get_user_list(c, song_type, song_artist):
                bot.sendMessage(chat_id= chat_id, #"580916113",
                                text= "곡: " + song_artist + " - " + song_name +
                                      '\n유튜브 링크 : ' + get_youtube_url(song_artist + " - " + song_name) +
                                      '\n다운로드 링크 : ' + song[2])

            conn.commit()
            c.close()
            conn.close()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
bot = Bot(token=token)



if __name__=='__main__':
    Chrome = SongDownloadLink()
    # Chrome.crawl_kpop_song_list()
    Chrome.crawl_pop_song_list()
    schedule.every(3).minutes.do(get_pop_100)
    schedule.every(30).minutes.do(Chrome.crawl_kpop_song_list)
    schedule.every(30).minutes.do(Chrome.crawl_pop_song_list)

    while True:
        schedule.run_pending()
        time.sleep(1)