import json
import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import wget
import re


def upload_get_link(gauth, file_path):
    drive = GoogleDrive(gauth)
    folder_id = '1k2zDvpvahgfifOj9MMLPAytBZ9rzcTxK'
    upload_file = drive.CreateFile({"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
    upload_file.SetContentFile(file_path)
    upload_file.Upload()
    os.unlink(file_path)


def list_folder(drive, id):
    folder_list = drive.ListFile({
        'q': "'{}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'".format(
            id)}).GetList()
    return folder_list


if __name__ == "__main__":
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile(os.path.join("creds", "580916113" + "creds.txt"))

    urls = [
        "https://home.ebs.co.kr/docuprime/replay/2/list?c.page=1&searchKeywordValue=0&orderBy=NEW&searchConditionValue=0&courseId=BP0PAPB0000000005&vodSort=NEW&searchStartDtValue=0&brdcDsCdFilter=RUN&searchKeyword=&userId=&searchEndDt=&searchCondition=&searchEndDtValue=0&stepId=02BP0PAPB0000000005&searchStartDt=&",
        "https://home.ebs.co.kr/docuprime/replay/2/list?c.page=2&searchKeywordValue=0&orderBy=NEW&searchConditionValue=0&vodSort=NEW&courseId=BP0PAPB0000000005&searchStartDtValue=0&brdcDsCdFilter=RUN&userId=&searchKeyword=&searchCondition=&searchEndDt=&searchEndDtValue=0&stepId=02BP0PAPB0000000005&searchStartDt=&",
        "https://home.ebs.co.kr/docuprime/replay/2/list?c.page=3&searchKeywordValue=0&orderBy=NEW&searchConditionValue=0&courseId=BP0PAPB0000000005&vodSort=NEW&searchStartDtValue=0&brdcDsCdFilter=RUN&searchKeyword=&userId=&searchEndDt=&searchCondition=&searchEndDtValue=0&stepId=02BP0PAPB0000000005&searchStartDt=&",
        "https://home.ebs.co.kr/docuprime/replay/2/list?c.page=4&searchKeywordValue=0&orderBy=NEW&searchConditionValue=0&vodSort=NEW&courseId=BP0PAPB0000000005&searchStartDtValue=0&brdcDsCdFilter=RUN&userId=&searchKeyword=&searchCondition=&searchEndDt=&searchEndDtValue=0&stepId=02BP0PAPB0000000005&searchStartDt=&",
    ]

    for url in urls:
        res = requests.get(url)
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')

        posts = [i for i in soup.select("div > strong > a")]
        post_urls = []

        post_url_format = "https://www.ebs.co.kr/tv/show?prodId=7503&lectId={}"
        for post in posts:
            onclick = post['onclick']
            url_num = re.findall(r"\D(\d{8})\D", onclick)[0]
            post_urls.append([post.text, post_url_format.format(url_num)])

        for post_name, post_url in post_urls:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            options.add_argument('window-size=1920x1080')
            options.add_argument("disable-gpu")
            driver = webdriver.Chrome(options=options)
            driver.get(post_url)
            html = driver.page_source
            driver.quit()
            soup = BeautifulSoup(html, 'html.parser')
            video_url = soup.find("video").get("src")
            video_filename = post_name + ".mp4"
            wget.download(video_url, out=video_filename)
            upload_get_link(gauth, video_filename)

