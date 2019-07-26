from __future__ import unicode_literals
from pydrive.auth import GoogleAuth, AuthenticationError
from pydrive.drive import GoogleDrive
from pytube import YouTube
import urllib.parse, requests
from bs4 import BeautifulSoup
import time
import itunespy
import wget
from subprocess import run, PIPE
import os, re, json
from mutagen.id3 import ID3, USLT
import youtube_dl
from urllib.error import HTTPError

def download_mega_link(link):
    file_name = run(["megadl", "--print-names", "--no-progress", link.encode('utf-8')], stdout=PIPE, stderr=PIPE)
    output = file_name.stdout
    err = file_name.stderr
    return  output.decode('utf-8').strip(), err.decode('utf-8').strip()

def download_youtube_link(song, artist, itunes = True):
    print(artist, song)
    print("downloading from youtube")
    link = get_youtube_url(artist + ' - ' + song)
    yt = YouTube(link)
    try:
        file_name = yt.streams.first().download()
    except HTTPError:
        download_youtube_mp3(link, artist, song)
        file_name = artist + ' - ' + song + '.mp3'
    print("getting track data")
    pattern1 = r'\((.*?)\)'
    track_data = get_track_data(re.sub(pattern1, '', song) + ' ' + re.sub(pattern1, '', artist))
    if track_data:
        title, cover, metadata, lyrics = track_data
        cover = wget.download(cover, out=artist + ' - ' + song + '.jpg')
        metadata_keys = list(metadata.keys())
        metadata = [
            '-metadata' if i % 2 == 0 else (metadata_keys[i // 2] + '=' + str(metadata[metadata_keys[i // 2]])).encode('utf-8') for i in
            range(len(metadata) * 2)]
    else:
        print("no metadata")
        title = artist + ' - ' + song
        lyrics = ""
        cover = wget.download(yt.thumbnail_url)
        metadata = []
    if itunes == False:
        title = artist + ' - ' + song
    print('converting mp4 to mp3')
    music = title.replace("/", "") + ".mp3"
    command = ['ffmpeg', '-i', file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec', 'libmp3lame', '-b:a', '192k', '-c:v', 'copy',
                     '-map', '0:a:0', '-map', '1:v:0', music.encode('utf-8')]
    command[11:11] = metadata
    run(command, stdout=PIPE, stderr=PIPE)
    if lyrics:
        print("lyrics exists")
        audio = ID3(music)
        audio.add(USLT(text=lyrics))
        audio.save()

    os.unlink(file_name)
    os.unlink(cover)
    return os.path.basename(music)

def get_track_data(term, index=0, search=False):
    print(term)
    try:
        tracks = itunespy.search_track(term)
    except LookupError:
        return None
    except ConnectionError:
        print("connection error")
        return get_track_data(term, index=index, search=search)
    track_data = []
    for i, track in enumerate(tracks):
        metadata = {"title":track.track_name, "album":track.collection_name, "artist":track.artist_name, "genre":track.primary_genre_name,
                    "TYER":track.release_date, "Track":track.track_number, "disc":track.disc_number}
        lyrics = ""
        cover = track.artwork_url_100.replace("100", "500")

        if index == 'all':
            track_data.append([metadata['artist'] + ' - ' + metadata['title'], cover, metadata, lyrics])
        elif index == i:
            if search == False:
                lyrics = get_lyrics(metadata['title'], metadata['artist'])
            if requests.get(cover).status_code != 200:
                cover = cover.replace("500", "100")
            return [metadata['artist'] + ' - ' + metadata['title'], cover, metadata, lyrics]
    return track_data

def get_lyrics(song, artist):
    pattern = r'\(feat(.*?)\)'
    song = re.sub(pattern, '', song).strip()
    url = "http://api.musixmatch.com/ws/1.1/track.search?format=json&q_artist={}&q_track={}&page_size=3&page=1&s_track_rating=desc" \
          "&apikey=1727b5ea994b4420ee5b6d27a0fd8bf5".format(urllib.parse.quote_plus(artist), urllib.parse.quote_plus(song))
    response = requests.get(url).json()
    try:
        lyrics_url = response['message']['body']['track_list'][0]['track']['track_share_url']
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

def g_auth(chat_id):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile(os.path.join("creds", chat_id + "creds.txt"))
    if gauth.credentials is None:
        gauth.CommandLineAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile(os.path.join("creds", chat_id + "creds.txt"))
    return gauth

def g_auth_bot(update, chat_id):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile(os.path.join("creds", chat_id + "creds.txt"))
    try:
        if gauth.credentials is None:
            update.message.reply_text("구글 드라이브 접근 권한이 필요합니다.")
            update.message.reply_text("3분 안에 다음 링크에서 로그인하여 코드를 보내주세요.\n" + gauth.GetAuthUrl())
            code = ""
            times = 0
            time.sleep(20)
            while len(code) != 57 and times < 30:
                file_name = 'gauth_code.json'
                if os.path.exists(file_name):
                    with open(file_name, 'r') as f:
                        data = json.load(f)
                        if chat_id in data.keys():
                            code = data[chat_id]
                    os.unlink(file_name)
                times = times + 1
                time.sleep(5)
            try:
                gauth.Auth(code)
                update.message.reply_text("인증되었습니다.")
            except AuthenticationError:
                return

        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
        else:
            # Initialize the saved creds
            gauth.Authorize()
    except:
        if gauth.credentials is None:
            update.callback_query.message.reply_text("구글 드라이브 접근 권한이 필요합니다.")
            update.callback_query.message.reply_text("3분 안에 다음 링크에서 로그인하여 코드를 보내주세요.\n" + gauth.GetAuthUrl())
            code = ""
            times = 0
            time.sleep(20)
            while len(code) != 57 and times < 30:
                file_name = 'gauth_code.json'
                if os.path.exists(file_name):
                    with open(file_name, 'r') as f:
                        data = json.load(f)
                        if chat_id in data.keys():
                            code = data[chat_id]
                    os.unlink(file_name)
                times = times + 1
                time.sleep(5)
            try:
                gauth.Auth(code)
                update.callback_query.message.reply_text("인증되었습니다.")
            except AuthenticationError:
                return

        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
        else:
            # Initialize the saved creds
            gauth.Authorize()

    # Save the current credentials to a file
    gauth.SaveCredentialsFile(os.path.join("creds", chat_id + "creds.txt"))
    return gauth

def upload_get_link(gauth, file_path, chat_id, permission=True, playlist=""):
    drive = GoogleDrive(gauth)
    folder_id = ''
    with open('creds/folder_id.json', 'r') as f:
        data = json.load(f)
        if chat_id in data.keys():
            folder_id = data[chat_id]
    if folder_id:
        if playlist:
            folders = list_folder(drive, folder_id)
            playlist_folder_id = [folder['id'] for folder in folders if folder['title']==playlist]
            if not playlist_folder_id:
                folder = drive.CreateFile({'title': playlist, "parents":  [{"id": folder_id}],
                                           "mimeType": "application/vnd.google-apps.folder"})
                folder.Upload()
                folder_id = folder['id']
            else:
                folder_id = playlist_folder_id[0]
            upload_file = drive.CreateFile({"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
        else:
            upload_file = drive.CreateFile({"parents": [{"kind": "drive#fileLink","id": folder_id}]})
    else:
        upload_file = drive.CreateFile()
    upload_file.SetContentFile(file_path)
    upload_file.Upload()
    os.unlink(file_path)
    if permission:
        upload_file.InsertPermission({
                                'type': 'anyone',
                                'value': 'anyone',
                                'role': 'reader'})
        return upload_file['alternateLink']
    else:
        return

def list_folder(drive, id):
    folder_list = drive.ListFile({'q': "'{}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'".format(id)}).GetList()
    return folder_list

def get_youtube_url(keyword, limit=1):
    url = 'https://www.youtube.com/results?search_query='+ urllib.parse.quote_plus(keyword)
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    urls = list()
    i = 0
    for link in soup.findAll('a', {'class': 'yt-uix-tile-link'}):
        if link.get('href').startswith('/watch'):
            if limit==1:
                return 'https://www.youtube.com' + link.get('href')
            elif i < limit:
                urls.append('https://www.youtube.com' + link.get('href'))
            else:
                return urls
            i += 1
    return urls if urls else "no youtube link"


class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')

def download_youtube_mp3(link, artist, song):
    ydl_opts = {
        'writethumbnail': True,
        'outtmpl': f'{artist} - {song}.mp4',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])

if __name__=='__main__':
    # download_youtube_link("Always Remember Us This Way", "Lady GaGa")
    # download_youtube_link("꽃 길", "BIGBANG(빅뱅)", itunes=False)
    # get_track_data('장범준')
    # import sqlite3
    # mega_output = download_mega_link("https://mega.nz/#!3iZCxKIS!8LhjRrLOPBcJT892x3sS8UNBZ2JTYPI1fPtD-Lss7p0")
    # if mega_output[1].endswith("Can't determine download url"):
    #     print("True")
    download_youtube_link('뭐해(what are you up to)', '강다니엘')
    # download_youtube_mp3("https://www.youtube.com/watch?v=_-QY40Reub8", '뭐해(what are you up to)', '강다니엘')
    # [print(m) for m in mega_output]
    # conn = sqlite3.connect("user_info.db")
    # c = conn.cursor()
    # c.execute("SELECT song, artist FROM kpop_song")
    # song_infos = [i for i in c.fetchall()][10:20]
    # for song_info in song_infos:
    #     song = song_info[0]
    #     artist = song_info[1]
    #     print(get_track_data(song, artist))
    #
    # c.close()
    # conn.close()
    #


