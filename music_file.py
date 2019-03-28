from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pytube import YouTube
import urllib.parse, requests
from bs4 import BeautifulSoup
import itunespy
from musixmatch import Musixmatch
from selenium import webdriver
import wget
import subprocess
import os, re

def download_mega_link(link):
    file_name = os.popen('megadl --print-names --no-progress {}'.format(link)).read().replace('\n', '')
    return  file_name

def download_youtube_link(song, artist, itunes = True):
    link = get_youtube_url(artist + ' - ' + song)
    yt = YouTube(link)
    file_name = yt.streams.first().download()
    pattern1 = r'\((.*?)\)'
    track_data = get_track_data(re.sub(pattern1, '', song), re.sub(pattern1, '', artist))
    if track_data:
        title, cover, metadata = track_data
        metadata_keys = list(metadata.keys())
        metadata = ['-id3v2_version', '3'] + [
            '-metadata' if i % 2 == 0 else metadata_keys[i // 2] + '=' + str(metadata[metadata_keys[i // 2]]) for i in
            range(len(metadata) * 2)]
    else:
        title = artist + ' - ' + song
        cover = wget.download(yt.thumbnail_url)
        metadata = []
    if itunes == False:
        title = artist + ' - ' + song
    music = title + ".mp3"
    command = ['ffmpeg', '-i', file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec', 'libmp3lame', '-b:a', '256k', '-c:v', 'copy',
                     '-map', '0:a:0', '-map', '1:v:0', (music).encode('utf-8')]
    command[11:11] = metadata
    subprocess.call(command)#, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.unlink(file_name)
    os.unlink(cover)
    return os.path.basename(music)

def get_track_data(song, artist):
    try:
        track = itunespy.search_track(artist + ' ' + song)[0]
    except LookupError:
        return None
    metadata = {"title":track.track_name, "album":track.collection_name, "artist":track.artist_name, "genre":track.primary_genre_name,
                "TYER":track.release_date, "Track":track.track_number, "disc":track.disc_number}
    lyrics = get_lyrics(metadata['title'], metadata['artist'])
    if lyrics:
        metadata.update({'lyrics':lyrics})
    cover = track.artwork_url_100.replace('100', '500')
    file = wget.download(cover, out=artist + ' - ' + song + '.jpg')
    return metadata['artist'] + ' - ' + metadata['title'], file, metadata

def get_lyrics(song, artist):
    musixmatch = Musixmatch('1727b5ea994b4420ee5b6d27a0fd8bf5')
    try:
        lyrics_url = musixmatch.track_search(q_artist=artist, q_track=song, page_size=10, page=1, s_track_rating='desc')['message']['body']['track_list'][0]['track']['track_share_url']
    except IndexError:
        return None
    pattern = r'\?.*'
    lyrics_url = re.sub(pattern, '', lyrics_url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36', }
    response = requests.get(lyrics_url, headers=headers)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    lyrics = '\n'.join([s.text for s in soup.select("[class] span:nth-child(3) .mxm-lyrics__content")])
    return lyrics

def upload_get_link(file_path):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile("mycreds.txt")
    drive = GoogleDrive(gauth)
    upload_file = drive.CreateFile()
    upload_file.SetContentFile(file_path)
    upload_file.Upload()
    upload_file.InsertPermission({
                            'type': 'anyone',
                            'value': 'anyone',
                            'role': 'reader'})
    return upload_file['alternateLink']

def get_youtube_url(keyword):
    url = 'https://www.youtube.com/results?search_query='+ urllib.parse.quote_plus(keyword)
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    for link in soup.findAll('a', {'class': 'yt-uix-tile-link'}):
        if link.get('href').startswith('/watch'):
            return 'https://www.youtube.com' + link.get('href')
    return "no youtube link"

def start_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('headless')
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")
    return webdriver.Chrome('chromedriver', chrome_options=options)

if __name__=='__main__':
    # download_youtube_link("Always Remember Us This Way", "Lady GaGa")
    # download_youtube_link("그댈 마주하는건 힘들어", "버스커 버스커")
    # download_youtube_link("대박이다", "버스커 버스커")
    import sqlite3
    conn = sqlite3.connect("user_info.db")
    c = conn.cursor()
    c.execute("SELECT song, artist FROM kpop_song")
    song_infos = [i for i in c.fetchall()][228:235]
    for song_info in song_infos:
        song = song_info[0]
        artist = song_info[1]
        download_youtube_link(song, artist)

    c.close()
    conn.close()


