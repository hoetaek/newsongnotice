from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from subprocess import check_output
import subprocess
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
    file_name = check_output(['megadl', '--print-names', '--no-progress',
                              'https://mega.nz/#!CiY0jK7S!kWBHOp1GhRkb5L-rLCO5DHOb5MT8tmNji0pnxtQYKdY'.encode('utf-8')]).decode('utf-8')
    print(file_name)
    # file_name = subprocess.run(['megadl', '--print-names', '--no-progress', link.encode('utf-8')],
    #                            stdout=subprocess.PIPE, encoding='US-ASCII').stdout
    return file_name

out = os.popen('megadl https://mega.nz/#!CiY0jK7S!kWBHOp1GhRkb5L-rLCO5DHOb5MT8tmNji0pnxtQYKdY').read()
print(out)
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