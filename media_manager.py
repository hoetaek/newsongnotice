from __future__ import unicode_literals
from pydrive.auth import GoogleAuth, AuthenticationError
from pydrive.drive import GoogleDrive
from pytube import YouTube
import urllib.parse, requests
from bs4 import BeautifulSoup
import time
import itunespy
import wget
from subprocess import call, run, PIPE
import os, re, json
from mutagen.id3 import ID3, USLT
import youtube_dl
from urllib.error import HTTPError


class DownloadYoutube:
    def __init__(self, link, artist='', song=''):
        self.link = link
        self.artist = artist
        self.song = song

    def start_download(self):
        if 'playlist' in self.link:
            return self.download_playlist()
        else:
            return self.download_video()

    def download_video(self):
        ydl_opts = {
            'quiet': True,
            'outtmpl': '%(title)s.%(ext)s',
            'writethumbnail': True,
            'format': 'mp4'
        }
        if self.artist and self.song:
            ydl_opts['outtmpl'] = f'{self.artist} - {self.song}.mp4'
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(self.link, download=True)
            filename = info_dict['title'] + '.mp4'
            thumbnail = filename[:filename.rfind('.')] + '.jpg'
        return filename, thumbnail

    def download_playlist(self):
        ydl_opts = {
            'quiet': True,
            'outtmpl': '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s',
            'format': 'mp4'
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(self.link, download=True)
            return info_dict['title']

    def get_song_link(self, artist, song, limit=1):
        url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote_plus(artist + ' - ' + song)
        response = requests.get(url)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        urls = list()
        i = 0
        for link in soup.findAll('a', {'class': 'yt-uix-tile-link'}):
            if link.get('href').startswith('/watch'):
                if limit == 1:
                    return 'https://www.youtube.com' + link.get('href')
                elif i < limit:
                    urls.append('https://www.youtube.com' + link.get('href'))
                else:
                    return urls
                i += 1
        return urls if urls else "no youtube link"


class VideoToMp3:
    def __init__(self, file_name, thumbnail):
        self.file_name = file_name
        self.thumbnail = thumbnail

    def convert_to_mp3(self):
        music_file_name = self.file_name[:-1] + '3'
        command = ['ffmpeg', '-i', self.file_name.encode('utf-8'), '-i', self.thumbnail.encode('utf-8'), '-acodec',
                   'libmp3lame', '-b:a', '192k', '-c:v', 'copy', '-map', '0:a:0', '-map', '1:v:0', music_file_name.encode('utf-8')]
        call(command, stdout=PIPE, stderr=PIPE)
        os.unlink(self.file_name)
        os.unlink(self.thumbnail)
        return music_file_name

    def convert_to_mp3_with_info(self, song, artist, track_data=''):
        cover = self.thumbnail
        if track_data:
            os.unlink(cover)
            title, cover, metadata, lyrics = track_data
            cover = wget.download(cover, out=artist + ' - ' + song + '.jpg')
            metadata_keys = list(metadata.keys())
            metadata = [
                '-metadata' if i % 2 == 0 else (
                            metadata_keys[i // 2] + '=' + str(metadata[metadata_keys[i // 2]])).encode('utf-8') for i in
                range(len(metadata) * 2)]
        else:
            print("no metadata")
            title = artist + ' - ' + song
            lyrics = ""
            metadata = []
        music = title.replace("/", "") + ".mp3"
        command = ['ffmpeg', '-i', self.file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec', 'libmp3lame',
                   '-b:a', '192k', '-c:v', 'copy',
                   '-map', '0:a:0', '-map', '1:v:0', music.encode('utf-8')]
        command[11:11] = metadata
        run(command, stdout=PIPE, stderr=PIPE)
        if lyrics:
            print("lyrics exists")
            audio = ID3(music)
            audio.add(USLT(text=lyrics))
            audio.save()

        os.unlink(self.file_name)
        os.unlink(cover)
        return os.path.basename(music)


class MusicData:
    def __init__(self, artist, song):
        self.term = f'{artist} - {song}'

    def get_track_data(self, index=0, search=False):
        try:
            tracks = itunespy.search_track(self.term)
        except LookupError:
            return None
        except ConnectionError:
            print("connection error")
            return self.get_track_data(index=index, search=search)
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
                    lyrics = self.get_lyrics(metadata['title'], metadata['artist'])
                if requests.get(cover).status_code != 200:
                    cover = cover.replace("500", "100")
                return [metadata['artist'] + ' - ' + metadata['title'], cover, metadata, lyrics]
        return track_data

    def get_lyrics(self, song, artist):
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

class Youtube_Util:
    def __init__(self, artist='', song='', link=''):
        self.artist = artist
        self.song = song
        self.link = link

    def download_youtube_video(self):
        video_file, thumbnail = DownloadYoutube(self.link).start_download()
        os.unlink(thumbnail)
        return video_file

    def download_youtube_music(self):
        video_file, thumbnail = DownloadYoutube(self.link).start_download()
        return VideoToMp3(video_file, thumbnail).convert_to_mp3()

    def download_youtube_music_with_info(self):
        pass

    def download_youtube_playlist(self):
        return DownloadYoutube(self.link).start_download()


    def download_youtube_link(song, artist, itunes = True):
        print(artist, song)
        print("downloading from youtube")
        link = get_youtube_url(artist + ' - ' + song)
        yt = YouTube(link)
        try:
            file_name = yt.streams.first().download()
            cover = wget.download(yt.thumbnail_url)
        except HTTPError:
            download_youtube_mp3(link, artist, song)
            cover = artist + ' - ' + song + '.jpg'
            file_name = artist + ' - ' + song + '.mp4'
        print("getting track data")
        pattern1 = r'\((.*?)\)'
        track_data = get_track_data(re.sub(pattern1, '', song) + ' ' + re.sub(pattern1, '', artist))
        if track_data:
            os.unlink(cover)
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


def download_mega_link(link):
    file_name = run(["megadl", "--print-names", "--no-progress", link.encode('utf-8')], stdout=PIPE, stderr=PIPE)
    output = file_name.stdout
    err = file_name.stderr
    return output.decode('utf-8').strip(), err.decode('utf-8').strip()

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


if __name__=='__main__':
    yt = Youtube_Util(link='https://www.youtube.com/playlist?list=PLjxrf2q8roU23XGwz3Km7sQZFTdB996iG')
    print(yt.download_youtube_playlist())
    # yt.download_youtube_music()
