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
    folder_id = '1iU1N2klX3-ksCjS-4nhKIC8EaZ4EwxtZ'
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
        "https://home.ebs.co.kr/knowledge_joy/replay/11/list?courseId=10204062&stepId=20005402",
    ]

    for url in urls:
        res = requests.get(url)
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')

        posts = [i for i in soup.select("div > strong > a")]
        post_urls = []

        post_url_format = "https://www.ebs.co.kr/tv/show?prodId=132491&lectId={}"
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

