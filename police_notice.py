import requests
from bs4 import BeautifulSoup
from new_data_manager import NewNotice
from telegram import Bot
import schedule, time
import re

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
    notice_title = [a.text for a in soup.select("td.tl > a")]
    links = ["https://ap.police.go.kr" + a['href'] for a in soup.select("td.tl > a")]
    notices = [[i, j] for i, j in zip(notice_title, links)]
    police_notice = NewNotice('others.json')
    new_notice = police_notice.compare_data("police_notice", notices)
    police_notice.save_data()
    if new_notice:
        chat_ids = [580916113, 659233833]
        for chat_id in chat_ids:
            token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
            bot = Bot(token=token)
            messages = []
            for message, link in new_notice:
                messages.append("<a href=\"{}\">{}</a>".format(link, message.replace("<", "").replace(">", "")))
            bot.send_message(chat_id=chat_id,
                             parse_mode="HTML",
                             text ="의경 관련 새로운 공지가 있습니다.\n\n" +
                                   "\n".join(messages))

def check_snue_update():
    response = requests.post("http://portal.snue.ac.kr/enview/board/list.brd?boardId=graduate_notice")
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    notice_title = [i.text.strip() for i in soup.select("td.td2")]
    url = "http://portal.snue.ac.kr/enview/board/read.brd?boardId=graduate_notice&bltnNo={}&cmpBrdId=graduate_notice&cmd=READ"
    links = [url.format(re.search('\d+', i['onclick']).group()) for i in soup.select("tr.board-item")]
    notices = [[i, j] for i, j in zip(notice_title, links)]

    snue_notice = NewNotice('others.json')
    new_notice = snue_notice.compare_data("snue_notice", notices)
    snue_notice.save_data()
    if new_notice:
        chat_ids = [580916113, 659233833]
        for chat_id in chat_ids:
            token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
            bot = Bot(token=token)
            messages = []
            for message, link in new_notice:
                messages.append("<a href=\"{}\"> {} </a>".format(link, message.replace("<", "").replace(">", "")))
            bot.send_message(chat_id=chat_id,
                             parse_mode="HTML",
                             text="서울교대 새로운 학사공지가 있습니다.\n\n" +
                                  "\n".join(messages))

def check_lost_found():
    res = requests.get("http://115.84.165.106/admin/find_list.jsp")
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    notice = [i for i in soup.select("td > span > a")][2:]
    notice_title = [i.text.strip() for i in notice]
    url = "http://115.84.165.106/admin/find_view_0.jsp?curPage=1&targetCode=&searchKey=&sort_1=&code1=&code2=&code3=&code4=&code5=&code6=&cate1=&cate2=&cate3=&cate4=&cate5=&cate6=&cate7=&cate8=&cate9=&cate10=&cate11=&date_start=&date_end=&yy=&mm=&id="
    notice_link = [url + re.search('\d+', i['onclick']).group() for i in notice]
    notice = [[i, j] for i, j in zip(notice_title, notice_link)]
    landf_notice = NewNotice('others.json')
    new_notice = landf_notice.compare_data("landf_notice", notice)
    landf_notice.save_data()
    if new_notice:
        token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
        bot = Bot(token=token)
        messages = []
        for message, link in new_notice:
            messages.append("<a href=\"{}\"> {} </a>".format(link, message.replace("<", "").replace(">", "")))
        bot.send_message(chat_id=580916113,
                         parse_mode="HTML",
                         text="분실물이 새로 등록되었습니다.\n\n" +
                              "\n".join(messages))


if __name__=='__main__':
    check_police_update()
    check_snue_update()
    # check_lost_found()

    schedule.every(3).hours.do(check_police_update)
    schedule.every(3).hours.do(check_snue_update)
    # schedule.every(30).minutes.do(check_lost_found)

    while True:
        schedule.run_pending()
        time.sleep(1)
