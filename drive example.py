from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


def get_credential(chat_id):
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile(chat_id + "creds.txt")
    if gauth.credentials is None:
        # Authenticate if they're not there
        print(gauth.GetAuthUrl())

        code = input("write the code here")
        gauth.Auth(code)
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile(chat_id + "creds.txt")
    drive = GoogleDrive(gauth)
#
# import telegram   #텔레그램 모듈을 가져옵니다.
#
# my_token = '790146878:AAFKnWCnBV9WMSMYPnfcRXukmftgDyV_BlY'   #토큰을 변수에 저장합니다.
#
# bot = telegram.Bot(token = my_token)   #bot을 선언합니다.
#
# updates = bot.getUpdates()  #업데이트 내역을 받아옵니다.
#
# for u in updates[-3:]:   # 내역중 메세지를 출력합니다.
#     print(u.message.text)
#     chat_id = u.message.chat.id
#     print(chat_id)

get_credential('111')
