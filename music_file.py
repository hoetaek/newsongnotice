from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pytube import YouTube
import os


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

def download_mega_link(link):
    file_name = os.popen('megadl --print-names --no-progress {}'.format(link)).read().replace('\n', '')
    print(file_name)
    return  file_name

def download_youtube_link(link):
    # yt = YouTube(link)
    yt = YouTube("https://www.youtube.com/watch?v=YQHsXMglC9A")
    yt.streams.filter(only_audio=True).all().download('/audio')
# download_youtube_link("link")


def upload_get_link(file_path):
    drive = GoogleDrive(gauth)
    upload_file = drive.CreateFile()
    upload_file.SetContentFile(file_path)
    upload_file.Upload()
    upload_file.InsertPermission({
                            'type': 'anyone',
                            'value': 'anyone',
                            'role': 'reader'})
    return upload_file['alternateLink']