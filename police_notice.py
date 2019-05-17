import requests
from bs4 import BeautifulSoup
from new_data_manager import NewNotice
from telegram import Bot
import schedule, time

cookies = {
    'WMONID': 'z0ZIgcdEDfv',
    'JSESSIONID': 'baamHl11puguMfk6howNw',
}

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
    'Origin': 'https://ap.police.go.kr',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Referer': 'https://ap.police.go.kr/ap/bbs/list.do?bbsId=B0000006&menuNo=200031',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,zh;q=0.6',
}

params = (
    ('menuNo', '200031'),
    ('bbsId', 'B0000006'),
)

data = {
  'ntcrNm': '\uC11C\uC6B8\uC9C0\uBC29\uACBD\uCC30\uCCAD',
  'searchCnd': '1',
  'searchWrd': '',
  'x': '15',
  'y': '12'
}

def check_police_update():
    response = requests.post('https://ap.police.go.kr/ap/bbs/list.do', headers=headers, params=params, cookies=cookies, data=data)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    notices = [a.text for a in soup.select("td.tl > a")]
    police_notice = NewNotice('others.json')
    new_notice = police_notice.compare_data("police_notice", notices)
    police_notice.save_data()
    if new_notice:
        chat_ids = [580916113, 659233833]
        for chat_id in chat_ids:
            token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
            bot = Bot(token=token)
            bot.send_message(chat_id=chat_id,
                             text ="의경 관련 새로운 공지가 있습니다.\n\n{}".format('\n'.join(new_notice)))


if __name__=='__main__':
    check_police_update()
    schedule.every(3).hours.do(check_police_update)

    while True:
        schedule.run_pending()
        time.sleep(1)

