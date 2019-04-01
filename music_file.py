from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pytube import YouTube
import urllib.parse, requests
from bs4 import BeautifulSoup
import itunespy
import wget
from subprocess import Popen, PIPE
import os, re
from mutagen.id3 import ID3, USLT

def download_mega_link(link):
    file_name = Popen(["megadl", "--print-names", " --no-progress", link], stdout=PIPE, stderr=PIPE)
    output, err = file_name.communicate()
    return  output.decode('utf-8').strip(), err.decode('utf-8').strip()

def download_youtube_link(song, artist, itunes = True):
    print(artist, song)
    print("downloading from youtube")
    link = get_youtube_url(artist + ' - ' + song)
    yt = YouTube(link)
    file_name = yt.streams.first().download()
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
    music = title + ".mp3"
    command = ['ffmpeg', '-i', file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec', 'libmp3lame', '-b:a', '256k', '-c:v', 'copy',
                     '-map', '0:a:0', '-map', '1:v:0', music.encode('utf-8')]
    command[11:11] = metadata
    Popen(command, stdout=PIPE, stderr=PIPE)
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
        return get_track_data(term)
    track_data = []
    for track in tracks:
        metadata = {"title":track.track_name, "album":track.collection_name, "artist":track.artist_name, "genre":track.primary_genre_name,
                    "TYER":track.release_date, "Track":track.track_number, "disc":track.disc_number}
        if search == False:
            lyrics = get_lyrics(metadata['title'], metadata['artist'])
        else:
            lyrics = ""
        cover = track.artwork_url_100.replace('100', '500')
        track_data.append([metadata['artist'] + ' - ' + metadata['title'], cover, metadata, lyrics])
    if index == 'all':
        return track_data
    return track_data[index]

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

def upload_get_link(file_path):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.CommandLineAuth()
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
    os.unlink(file_path)
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

if __name__=='__main__':
    # download_youtube_link("Always Remember Us This Way", "Lady GaGa")
    # download_youtube_link("꽃 길", "BIGBANG(빅뱅)", itunes=False)
    # get_track_data('장범준')
    # import sqlite3
    mega_output = download_mega_link("https://mega.nz/#!L7pDjYKS!bHnuF-f1Q4B8Vf4yo9QcBuPYEtR2tNI228CjPvXzgVE")
    if mega_output[1].endswith("Can't determine download url"):
        print("True")
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


