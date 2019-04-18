from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, MessageHandler, CommandHandler, CallbackQueryHandler, Filters
from tempfile import NamedTemporaryFile
from pydrive.drive import GoogleDrive
import sqlite3, json
from make_db import insert_user, is_user, insert_song, get_song_list, get_artist_list
from new_song_crawl import SongDownloadLink, get_youtube_url
from music_file import g_auth, upload_get_link, download_youtube_link, get_track_data
from telegram.ext.dispatcher import run_async
from pytube import YouTube
import os, re, difflib, subprocess, wget

@run_async
def get_message(bot, update):
    chat_id = str(update.message['chat']['id'])
    text = update.message.text
    conn = sqlite3.connect("user_info.db")
    c = conn.cursor()
    if len(text) == 57:
        file_name = 'gauth_code.json'
        with open(file_name, 'w') as f:
            json.dump({chat_id:text}, f)

    if text.startswith("검색"):
        keyword = text[2:].strip()
        if keyword:
            update.message.reply_text(keyword + "을(를) 검색 중입니다.")
            chrome = SongDownloadLink()
            chrome.crawl_keyword_list(keyword, chat_id)
            update.message.reply_text("다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

    elif text.startswith("유튜브"):
        keyword = text[3:].strip().split(' ')
        song_type = keyword[0]
        if song_type == 'pop' or song_type == 'kpop':
            try:
                song, artist = ' '.join(keyword[1:]).split('/')
            except IndexError:
                update.message.reply_text("가수/노래 형식으로 입력해주세요.")
                return
            update.message.reply_text(artist + ' ' + song + "을(를) 유튜브에서 다운 받는 중입니다.\n곡이 데이터베이스에 저장됩니다.")
            file = download_youtube_link(song, artist)
            drive_auth = g_auth(bot, update, "my")
            update.message.reply_text(artist + ' ' + song + "을(를) 드라이브에 업로드 중입니다.")
            link = upload_get_link(drive_auth, file, chat_id)
            insert_song(c, song_type, [song, artist, link])
            bot.sendMessage(chat_id=chat_id,
                            text="곡 : " + artist + ' - ' + song + \
                                 '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                                 '\n다운로드 링크 : ' + link + "\n\n")
            update.message.reply_text("다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

        elif '/' in ' '.join(keyword):
            song, artist = ' '.join(keyword).split('/')
            update.message.reply_text(artist + ' ' + song + "을(를) 유튜브에서 다운 받는 중입니다.\n곡이 데이터베이스에 저장되지 않습니다.")
            file = download_youtube_link(song, artist)
            drive_auth = g_auth(bot, update, chat_id)
            update.message.reply_text(artist + ' ' + song + "을(를) 드라이브에 업로드 중입니다.")
            link = upload_get_link(drive_auth, file, chat_id)
            bot.sendMessage(chat_id=chat_id,
                            text="곡 : " + artist + ' - ' + song + \
                                 '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                                 '\n다운로드 링크 : ' + link + "\n\n")
            update.message.reply_text("다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

        elif song_type == '음원':
            keyword = ' '.join(keyword[1:])
            update.message.reply_text("{}을(를) 유튜브에서 검색중입니다.".format(keyword))
            if keyword.startswith('http'):
                link = keyword
            else:
                link = get_youtube_url(keyword)
            yt = YouTube(link)
            title = yt.title
            update.message.reply_text("{}을(를) 유튜브에서 다운 받는 중입니다.".format(title))
            video_file_name = yt.streams.first().download()
            video_file_name = os.path.basename(video_file_name)

            drive_auth = g_auth(bot, update, chat_id)
            if drive_auth:
                update.message.reply_text("{}을(를) 음원으로 변환 중입니다.".format(title))
                if video_file_name.endswith('mp4'):
                    music_file_name = video_file_name[:-1] + '3'
                    cover = wget.download(yt.thumbnail_url)
                    command = ['ffmpeg', '-i', video_file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec',
                               'libmp3lame',
                               '-b:a', '192k', '-c:v', 'copy', '-map', '0:a:0', '-map', '1:v:0',
                               music_file_name.encode('utf-8')]
                    subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    os.unlink(video_file_name)
                    update.message.reply_text("{}을(를) 업로드 중입니다.".format(title))
                    upload_get_link(drive_auth, music_file_name, chat_id, permission=False)
                    os.unlink(cover)
                    update.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                              "구글 드라이브에서 확인해주세요.".format(title))
                else:
                    os.unlink(video_file_name)
                    update.message.reply_text("{} 음원 변환에 실패했습니다.\n".format(title))
            else:
                drive_auth = g_auth(bot, update, 'my')
                update.message.reply_text("인증에 실패하셨습니다.")
                if video_file_name.endswith('mp4'):
                    music_file_name = video_file_name[:-1] + '3'
                    cover = wget.download(yt.thumbnail_url)
                    command = ['ffmpeg', '-i', video_file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec',
                               'libmp3lame',
                               '-b:a', '192k', '-c:v', 'copy', '-map', '0:a:0', '-map', '1:v:0',
                               music_file_name.encode('utf-8')]
                    subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    update.message.reply_text("{}을(를) 업로드 중입니다.".format(title))
                    music_drive_link = upload_get_link(drive_auth, music_file_name, chat_id)
                    os.unlink(cover)
                    os.unlink(video_file_name)
                    update.message.reply_text("{}을(를) 유튜브에서 다운 받았습니다.\n"
                                              "음원 링크 : {}".format(title, music_drive_link))
                else:
                    os.unlink(video_file_name)
                    update.message.reply_text("{} 음원 변환에 실패했습니다.\n".format(title))

        else:
            keyword = ' '.join(keyword)
            update.message.reply_text("{}을(를) 유튜브에서 검색중입니다.".format(keyword))
            if keyword.startswith('http'):
                link = keyword
            else:
                link = get_youtube_url(keyword)
            yt = YouTube(link)
            title = yt.title
            update.message.reply_text("{}을(를) 유튜브에서 다운 받는 중입니다.".format(title))
            video_file_name = yt.streams.first().download()
            video_file_name = os.path.basename(video_file_name)
            drive_auth = g_auth(bot, update, chat_id)
            if drive_auth:
                update.message.reply_text("{}을(를) 드라이브에 업로드 중입니다.".format(title))
                upload_get_link(drive_auth, video_file_name, chat_id, permission=False)
                update.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                          "구글 드라이브에서 확인해주세요.".format(title))
            else:
                drive_auth = g_auth(bot, update, 'my')
                update.message.reply_text("인증에 실패하셨습니다.")
                update.message.reply_text("{}을(를) 드라이브에 업로드 중입니다.".format(title))
                video_drive_link = upload_get_link(drive_auth, video_file_name, chat_id)
                update.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                          "동영상 링크 : {}".format(title, video_drive_link))

    elif text.startswith("http"):
        link = text
        show_list = [InlineKeyboardButton("동영상", callback_data="url, 동영상, " + link), InlineKeyboardButton("음원",
                                            callback_data="url, 음원, " + link)]
        menu = build_menu(show_list, 2)
        show_markup = InlineKeyboardMarkup(menu)
        bot.sendMessage(text="동영상 또는 음원을 골라주세요.",
                        chat_id=chat_id,
                        reply_markup=show_markup)

    elif text.startswith("아이튠즈"):
        keyword = text[4:].strip()
        track_data = get_track_data(keyword, index='all', search=True)
        if track_data:
            titles = [i[0] for i in get_track_data(keyword, index='all', search=True)]
            update.message.reply_text('\n'.join(titles) + "와 같은 노래들이 있습니다.")
        else:
            update.message.reply_text("검색 결과가 존재하지 않습니다.ㅠㅠㅠ\n"
                                      "다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

    elif text.startswith("가수"):
        keyword = text[2:].strip()
        if keyword:
            update.message.reply_text(keyword + " 가수를 검색 중입니다.")
            songs = []
            for song_type in ['kpop', 'pop']:
                c.execute("SELECT artist FROM {}_artist".format(song_type))
                songs.extend(sorted([artist[0] for artist in c.fetchall()]))
            songs = [artist for artist in songs if show_dif(artist.lower(), keyword.lower()) < 0.1 or (len(keyword.lower()) > 1 and keyword.lower() in artist.lower())]
            for artist in songs:
                for song_type in ['kpop', 'pop']:
                    song_infos = get_song_list(c, song_type, artist)
                    if len(song_infos) > 1:
                        show_list = [InlineKeyboardButton(song_info[2] + ' - ' + song_info[1],
                                                          callback_data="send, " + song_type + ", " + str(song_info[0]))
                                     for song_info in song_infos] \
                                    + [InlineKeyboardButton('get all',
                                                            callback_data="send, " + song_type + ", " + "get all, " + str(
                                                                song_infos[0][0]))]
                        menu = build_menu(show_list, 1)
                        show_markup = InlineKeyboardMarkup(menu)
                        bot.sendMessage(text="{}이(가) 선택되었습니다.".format(artist),
                                              chat_id=chat_id,
                                              reply_markup=show_markup)
                    elif len(song_infos) == 1:
                        song_info = song_infos[0]
                        song = song_info[1]
                        artist = song_info[2]
                        link = song_info[3]
                        bot.sendMessage(text="{}이(가) 선택되었습니다.".format(artist + ' - ' + song),
                                              chat_id=chat_id)
                        bot.sendMessage(chat_id=chat_id,
                                        text="곡 : " + artist + ' - ' + song + \
                                             '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                                             '\n다운로드 링크 : ' + link + "\n\n")
            bot.sendMessage(chat_id=chat_id,
                            text="다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

    elif text.startswith("노래"):
        keyword = text[2:].strip()
        if keyword:
            update.message.reply_text(keyword + " 노래를 검색 중입니다.")
            songs = []
            for song_type in ['kpop', 'pop']:
                c.execute("SELECT song, artist, link FROM {}_song".format(song_type))
                songs.extend(sorted([song for song in c.fetchall()], key=lambda element:element[0]))
            song_infos = [song for song in songs if show_dif(song[0].lower(), keyword.lower()) < 0.12 or (
                        len(keyword.lower()) > 1 and keyword.lower() in song[0].lower())]
            for song_info in song_infos:
                song = song_info[0]
                artist = song_info[1]
                link = song_info[2]
                bot.sendMessage(text="{}이(가) 선택되었습니다.".format(artist + ' - ' + song),
                                chat_id=chat_id)
                bot.sendMessage(chat_id=chat_id,
                                text="곡 : " + artist + ' - ' + song + \
                                     '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                                     '\n다운로드 링크 : ' + link + "\n\n")
            update.message.reply_text("다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

    conn.commit()
    c.close()
    conn.close()

def show_dif(a, b):
    result = difflib.ndiff(a, b)
    result = ''.join(result)
    return (result.count('+') + result.count('-')) / (len(result)+1)

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

def start(bot, update):
    update.message.reply_text(
        '안녕하세요.\n'
        '새로운 노래 알림봇을 추가해주셔서 감사합니다.\n'
        '새로운 곡 다운로드 링크 알림을 받고 싶으시면 [/new_download]를 터치해주세요\n'
        '신청하신 서비스를 확인하고 싶으시면 [/check_service]를 터치해주세요\n'
        '노래를 찾고 싶으시면 [/search]를 터치해주세요\n'
        '텍스트로 검색하는 방법을 알고 싶으시면 [/command]를 터치해주세요.\n'
        '드라이브 업로드 폴더를 설정하고 싶으시면 [/drive]를 터치해주세요.\n'
        '도움이 필요하시면 [/help]를 터치해주세요.')

def stop(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()

    user_id = is_user(c, chat_id)
    if not user_id:
        c.execute("INSERT INTO users VALUES(NULL, '{}')".format(chat_id))
        user_id = c.lastrowid
    c.execute("DELETE FROM users_charts WHERE user_id = {}".format(user_id))
    c.execute("DELETE FROM users_kpop_artist WHERE user_id = {}".format(user_id))
    c.execute("DELETE FROM users_pop_artist WHERE user_id = {}".format(user_id))
    conn.commit()
    c.close()
    conn.close()
    update.message.reply_text(
        '이용해주셔서 감사합니다.\n'
        '이제부터 새로운 노래 알림을 보내지 않습니다.\n')

def help(bot, update):
    update.message.reply_text(
        '차트에 새로 올라오는 노래 알림을 받고 싶다면 [/chart]를 터치해주세요.\n'
        '새로운 곡 다운로드 링크 알림을 받고 싶으시면 [/new_download]를 터치해주세요\n'
        '노래를 찾고 싶으시면 [/search]를 터치해주세요.\n'
        '신청하신 서비를 확인하고 싶으시면 [/check_service]를 터치해주세요\n'
        '텍스트로 검색하는 방법을 알고 싶으시면 [/command]를 터치해주세요.\n\n'
        '신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.')

def check_service(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_id = is_user(c, chat_id)
    if not user_id:
        c.execute("INSERT INTO users VALUES(NULL, '{}')".format(chat_id))
        user_id = c.lastrowid
    c.execute("SELECT charts_id FROM users_charts WHERE user_id = {}".format(user_id))
    service_chart = []
    for i in c.fetchall():
        chart_id = i[0]
        c.execute("SELECT chart FROM charts WHERE id = {}".format(chart_id))
        service_chart.append(c.fetchone()[0])
    if service_chart:
        chart_text = '신청하신 차트는 ' + ', '.join(service_chart) + "입니다." + '\n'
    else:
        chart_text = "신청하신 차트가 없습니다.\n"

    kpop_artist = get_artist_list(c, 'kpop', chat_id)
    pop_artist = get_artist_list(c, 'pop', chat_id)
    c.close()
    conn.close()
    artist_text = ""
    if kpop_artist:
        artist_text = "kpop : \n{} 아티스트를 선택했습니다.\n".format(', '.join(kpop_artist))
    if pop_artist:
        artist_text = artist_text + "pop : \n{} 아티스트를 선택했습니다.\n".format(', '.join(pop_artist))
    if not kpop_artist and not pop_artist:
        artist_text = "선택하신 아티스트가 없습니다.\n"

    update.message.reply_text(
        chart_text +
        artist_text
    )
    update.message.reply_text(
        "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요."
    )

def download_url(bot, update):
    print('download from url')
    data = update.callback_query.data.split(', ')
    down_type = data[1]
    link = data[2]
    print(down_type)
    print(link)
    chat_id = str(update.callback_query.message.chat_id)
    print(chat_id)
    yt = YouTube(link)
    print(yt)
    title = yt.title
    update.message.reply_text("{}을(를) 유튜브에서 다운 받는 중입니다.".format(title))
    video_file_name = yt.streams.first().download()
    video_file_name = os.path.basename(video_file_name)

    if down_type=='동영상':
        print('start downl')
        drive_auth = g_auth(bot, update, chat_id)
        if drive_auth:
            update.message.reply_text("{}을(를) 드라이브에 업로드 중입니다.".format(title))
            upload_get_link(drive_auth, video_file_name, chat_id, permission=False)
            update.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                      "구글 드라이브에서 확인해주세요.".format(title))
        else:
            drive_auth = g_auth(bot, update, 'my')
            update.message.reply_text("인증에 실패하셨습니다.")
            update.message.reply_text("{}을(를) 드라이브에 업로드 중입니다.".format(title))
            video_drive_link = upload_get_link(drive_auth, video_file_name, chat_id)
            update.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                      "동영상 링크 : {}".format(title, video_drive_link))
    else:
        drive_auth = g_auth(bot, update, chat_id)
        if drive_auth:
            update.message.reply_text("{}을(를) 음원으로 변환 중입니다.".format(title))
            if video_file_name.endswith('mp4'):
                music_file_name = video_file_name[:-1] + '3'
                cover = wget.download(yt.thumbnail_url)
                command = ['ffmpeg', '-i', video_file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec',
                           'libmp3lame',
                           '-b:a', '192k', '-c:v', 'copy', '-map', '0:a:0', '-map', '1:v:0',
                           music_file_name.encode('utf-8')]
                subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                os.unlink(video_file_name)
                update.message.reply_text("{}을(를) 업로드 중입니다.".format(title))
                upload_get_link(drive_auth, music_file_name, chat_id, permission=False)
                os.unlink(cover)
                update.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                          "구글 드라이브에서 확인해주세요.".format(title))
            else:
                os.unlink(video_file_name)
                update.message.reply_text("{} 음원 변환에 실패했습니다.\n".format(title))
        else:
            drive_auth = g_auth(bot, update, 'my')
            update.message.reply_text("인증에 실패하셨습니다.")
            if video_file_name.endswith('mp4'):
                music_file_name = video_file_name[:-1] + '3'
                cover = wget.download(yt.thumbnail_url)
                command = ['ffmpeg', '-i', video_file_name.encode('utf-8'), '-i', cover.encode('utf-8'), '-acodec',
                           'libmp3lame',
                           '-b:a', '192k', '-c:v', 'copy', '-map', '0:a:0', '-map', '1:v:0',
                           music_file_name.encode('utf-8')]
                subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                update.message.reply_text("{}을(를) 업로드 중입니다.".format(title))
                music_drive_link = upload_get_link(drive_auth, music_file_name, chat_id)
                os.unlink(cover)
                os.unlink(video_file_name)
                update.message.reply_text("{}을(를) 유튜브에서 다운 받았습니다.\n"
                                          "음원 링크 : {}".format(title, music_drive_link))
            else:
                os.unlink(video_file_name)
                update.message.reply_text("{} 음원 변환에 실패했습니다.\n".format(title))


@run_async
def drive(bot, update):
    chat_id = str(update.message['chat']['id'])
    gauth = g_auth(bot, update, chat_id)
    drive = GoogleDrive(gauth)
    folder_list = list_folder(drive, 'root')
    children = list()
    for folder in folder_list:
        data = {'title': folder['title'],
                'id': folder['id']}
        children.append(data)
    with open('drive_folder.json', 'w') as f:
        json.dump({'title':'root', 'id':None, 'children':children}, f)
    titles_show_list = [InlineKeyboardButton(child['title'], callback_data="drive, " + str(i)) for i, child in enumerate(children)]
    menu = build_menu(titles_show_list, 3)
    titles_show_markup = InlineKeyboardMarkup(menu)
    update.message.reply_text("어느 폴더에 업로드할 지 선택해주세요.\n", reply_markup=titles_show_markup)

@run_async
def drive_callback(bot, update):
    data = update.callback_query.data.split(', ')
    folder_idx = int(data[1])
    chat_id = str(update.callback_query.message.chat_id)
    gauth = g_auth(bot, update, chat_id)
    drive = GoogleDrive(gauth)
    with open('drive_folder.json', 'r') as f:
        data = json.load(f)
        folder = data['children'][folder_idx]
        folder_title = folder['title']
        folder_id = folder['id']
    folder_list = list_folder(drive, folder_id)
    children = list()
    for folder in folder_list:
        data = {'title': folder['title'],
                           'id': folder['id']}
        children.append(data)
    if children:
        with open('drive_folder.json', 'w') as f:
            json.dump({'title':folder_title, 'id':folder_id, 'children':children}, f)
        titles_show_list = [InlineKeyboardButton(child['title'], callback_data="drive, " + str(i)) for i, child in
                            enumerate(children)] + [InlineKeyboardButton('선택', callback_data='drsel')]
        menu = build_menu(titles_show_list, 3)
        titles_show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}가 선택되었습니다.".format(folder_title),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=titles_show_markup)
    else:
        os.unlink('drive_folder.json')
        with open('creds/folder_id.json', 'w') as f:
            json.dump({chat_id:folder_id}, f)
        bot.edit_message_text(text="{}가 선택되었습니다.".format(folder_title),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)

def drive_selected(bot, update):
    chat_id = str(update.callback_query.message.chat_id)
    with open('drive_folder.json', 'r') as f:
        data = json.load(f)
        folder_title = data['title']
        folder_id = data['id']
    os.unlink('drive_folder.json')
    with open('creds/folder_id.json', 'w') as f:
        json.dump({chat_id: folder_id}, f)
    bot.edit_message_text(text="{}가 선택되었습니다.".format(folder_title),
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)

def list_folder(drive, id):
    folder_list = drive.ListFile({'q': "'{}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'".format(id)}).GetList()
    return folder_list

def command(bot, update):
    update.message.reply_text(
        '노래 검색은 크게 4가지 방법이 있습니다.(데이터베이스 검색, 웹사이트 검색, 유튜브 다운로드, 아이튠즈 음악 정보 검색)\n\n'
        '1. 데이터베이스 검색이 속도가 가장 빠르고 간단합니다. 다음과 같은 형식으로 입력하면 됩니다.\n'
        '[가수 (검색어)]\n'
        '[노래 (검색어)]\n\n'
        '2. 웹사이트 검색은 약간 느리고 검색 결과를 모조리 보내주기 때문에 메시지 폭탄을 받으실 수 있습니다.\n'
        '[검색 (검색어)]\n\n'
        '3. 유튜브 다운로드는 검색어로 검색 결과 가장 위에 올라와 있는 동영상의 음원을 보내줍니다.(검색어에 주의하세요.)\n'
        '[유튜브 (검색어)] -> 검색어에 해당하는 유튜브 영상과 음원의 링크를 보내줍니다.'
        '[유튜브 (가수 이름)/(노래 이름)] -> 가수, 노래에 맞는 곡의 음원 링크를 보내줍니다.\n'
        '[유튜브 (pop 혹은 kpop) (가수 이름)/(노래 이름)] -> 데이터베이스에 저장되며 다음에 더욱 빠르게 불러올 수 있습니다.\n\n'
        '4. 아이튠즈에서 노래나 가수의 정보를 토대로 여러 곡을 검색할 수 있습니다\n'
        '[아이튠즈 (검색어)]\n\n'
        '대괄호와 괄호는 구분을 위해 편의상 표시했습니다. 직접 입력하실 때는 제외해주세요.')

def chart(bot, update):
    update.message.reply_text(
        '멜론 차트에 새로 올라오는 노래 알림을 받고 싶다면 [/melon_chart]를 터치해주세요.\n'
        '빌보드 차트에 새로 올라오는 노래 알림을 받고 싶다면 [/billboard_chart]를 터치해주세요.\n'
        "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")

def melon_chart(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_id = is_user(c, chat_id)
    if not user_id:
        c.execute("INSERT INTO users VALUES(NULL, '{}')".format(chat_id))
        user_id = c.lastrowid
    chart_id = 1
    c.execute("SELECT * FROM users_charts WHERE user_id = ? and charts_id = ?", (user_id, chart_id))
    if c.fetchone():
        c.execute("DELETE FROM users_charts WHERE user_id = ? and charts_id = ?", (user_id, chart_id))
        update.message.reply_text("멜론 차트에 알림을 취소하셨습니다.\n"
                                  "다시 신청하고 싶으시면 [/melon_chart]를 터치해주세요.\n"
                                  "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")
    else:
        c.execute("INSERT INTO users_charts VALUES(?, ?)", (user_id, chart_id))
        update.message.reply_text("앞으로 멜론 차트에 새로운 노래가 올라오면 보내도록 하겠습니다.\n"
                                  "취소하고 싶으시면 [/melon_chart]을 터치해주세요.\n"
                                  "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")
    conn.commit()
    c.close()
    conn.close()

def billboard_chart(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_id = is_user(c, chat_id)
    if not user_id:
        c.execute("INSERT INTO users VALUES(NULL, '{}')".format(chat_id))
        user_id = c.lastrowid
    chart_id = 2
    c.execute("SELECT * FROM users_charts WHERE user_id = ? and charts_id = ?", (user_id, chart_id))
    if c.fetchone():
        c.execute("DELETE FROM users_charts WHERE user_id = ? and charts_id = ?", (user_id, chart_id))
        update.message.reply_text("빌보드 차트에 알림을 취소하셨습니다.\n"
                                  "다시 신청하고 싶으시면 [/billboard_chart]를 터치해주세요.\n"
                                  "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")
    else:
        c.execute("INSERT INTO users_charts VALUES(?, ?)", (user_id, chart_id))
        update.message.reply_text("앞으로 빌보드 차트에 새로운 노래가 올라오면 보내도록 하겠습니다.\n"
                                  "취소하고 싶으시면 [/billboard_chart]을 터치해주세요.\n"
                                  "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")
    conn.commit()
    c.close()
    conn.close()

def new_download(bot, update):
    update.message.reply_text(
        '케이팝 신곡 알림을 받고 싶다면 [/include_kpop_artist]를 터치해주세요.\n'
        '팝송 신곡 알림을 받고 싶다면 [/include_pop_artist]를 터치해주세요.\n'
        '신청한 가수를 확인하고 싶다면 [/check_artist]를 터치해주세요.\n'
        '신청 목록에서 제외하고 싶은 가수가 있다면 [/exclude_artist]를 터치해주세요.\n\n'
        '신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.'
    )

def get_all_artists(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM kpop_artist")
    kpop_artists = sorted([artist[0] for artist in c.fetchall()])
    c.execute("SELECT artist FROM pop_artist")
    pop_artists = sorted([artist[0] for artist in c.fetchall()])
    update.message.reply_text(
        "한국 가수는 다음과 같이 있습니다.\n"
    )
    n = 5
    chosung_list = sorted(
        list(set(
            [get_chosung(artist[0]) if is_hangul(artist[0]) else artist[0].upper() if artist[0].isalpha() else artist[0]
             for artist in kpop_artists])))

    k_artists_by_chosung = ["- " + ', '.join([artist for artist in kpop_artists if startswith(chosung, artist[0])]) for chosung in chosung_list]
    k_len = len(k_artists_by_chosung)
    for artist in [k_artists_by_chosung[k_len//n*j:k_len//n*(j+1)] for j in range(n)]:
        update.message.reply_text('\n'.join(artist))


    update.message.reply_text(
        "팝송 가수는  다음과 같이 있습니다.\n"
    )
    alphabet_list = sorted(list(set([artist[0].upper() if artist[0].isalpha() else artist[0] for artist in pop_artists])))
    p_artists_by_alphabets = ["- " + ', '.join([artist for artist in pop_artists if startswith(alphabet, artist[0])]) for alphabet in alphabet_list]
    p_len = len(p_artists_by_alphabets)
    for artist in [p_artists_by_alphabets[p_len // n * j:p_len // n * (j + 1)] for j in range(n)]:
        update.message.reply_text('\n'.join(artist))

    update.message.reply_text(
                    text="다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

def include_kpop_artist(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM kpop_artist")
    chosung_list = sorted(
        list(set([get_chosung(artist[0][0]) if is_hangul(artist[0][0]) else artist[0][0].upper() if artist[0][0].isalpha()
        else artist[0][0] for artist in c.fetchall()])))
    hangul_show_list = [InlineKeyboardButton(han, callback_data="han, "+han) for han in chosung_list]
    menu = build_menu(hangul_show_list, 3)
    hangul_show_markup = InlineKeyboardMarkup(menu)
    update.message.reply_text("알림 받고 싶은 가수의 초성 또는 시작 알파벳을 선택해주세요.\n"
                              "신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.", reply_markup=hangul_show_markup)

def kpop_artist_callback(bot, update):
    data = update.callback_query.data.split(', ')
    han = data[1]
    chat_id = str(update.callback_query.message.chat_id)
    f = NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, dir='.')
    select_f_name = os.path.relpath(f.name)
    f.close()

    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_artist = get_artist_list(c, 'kpop', chat_id)
    c.execute("SELECT artist FROM kpop_artist")
    artist_option = sorted([artist[0] for artist in c.fetchall() if artist[0] not in user_artist and startswith(han, artist[0][0])])
    artist_show_list = [InlineKeyboardButton(artist, callback_data="kp" + artist + ", " + select_f_name + ', ' + han) for artist in artist_option] \
                       + [InlineKeyboardButton('선택 종료', callback_data="kp" + "선택 종료" + ", " + select_f_name + ', ' + han)]
    menu = build_menu(artist_show_list, 3)
    artist_show_markup = InlineKeyboardMarkup(menu)
    c.close()
    conn.close()

    bot.edit_message_text(text="알림 받고 싶은 가수를 선택해주세요.",
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id,
                          reply_markup=artist_show_markup)

    update.message.reply_text("알림 받고 싶은 가수를 선택해주세요.", reply_markup=artist_show_markup)

def include_kpop_callback(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    data = update.callback_query.data.split(', ')
    data_selected = data[0]
    if data_selected.startswith('kp'):
        data_selected = data_selected[2:]
    select_f_name = data[1]
    han = data[2]
    chat_id = str(update.callback_query.message.chat_id)

    c.execute("SELECT artist FROM kpop_artist")
    artist_option = sorted([artist[0] for artist in c.fetchall() if startswith(han, artist[0][0])])

    temp_file = open(select_f_name, mode='a+', encoding='utf-8')
    temp_file.seek(0)
    selected_data = temp_file.read()

    user_artist = get_artist_list(c, 'kpop', chat_id)
    if user_artist:
        callback_data = ', '.join(user_artist) + ', '
    else:
        callback_data = ''
    if selected_data:
        callback_data = callback_data + selected_data + ', ' + data_selected
        temp_file.write(', ' + data_selected)
    else:
        callback_data = callback_data + data_selected
        temp_file.write(data_selected)
    temp_file.close()

    if data_selected.split(", ")[-1] != "선택 종료" and data_selected.split(", ")[-1] != "알림 취소":
        option_artist_left = [i for i in artist_option if i not in callback_data.split(', ')]
        show_list = [InlineKeyboardButton(artist, callback_data= "kp" + artist + ", " + select_f_name + ', ' + han) for artist in option_artist_left]
        menu = build_menu(show_list, 3) + [[InlineKeyboardButton("선택 종료", callback_data="kp" + "선택 종료" + ", " + select_f_name + ', ' + han)]]
        show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}가 선택되었습니다.\n추가 가수를 선택해 주세요.".format(callback_data),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=show_markup)
        c.close()
        conn.close()

    elif data_selected == '알림 취소':
        bot.edit_message_text(text="아무것도 선택하지 않았습니다.\n새로운 노래 다운로드 링크 알림이 가지 않습니다.\n",
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        user_id = is_user(c, chat_id)
        if user_id:
            c.execute("DELETE FROM users_kpop_artist WHERE user_id = {}".format(user_id))
        os.unlink(os.path.realpath(select_f_name))
        conn.commit()
        c.close()
        conn.close()

    else:
        callback_data = callback_data[:-7]
        bot.edit_message_text(text = "선택이 종료되었습니다.\n{}이 선택되었습니다.\n새로운 곡이 올라오면 알림을 보내드릴게요.\n\n"
                                     "신청 목록에서 제외하고 싶은 가수가 있다면 [/exclude_artist]를 터치해주세요^^.\n"
                                     "이전으로 돌아가시려면 [/include_kpop_artist]를 터치해주세요.\n"
                                     "신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.\n"
                                     "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.".format(callback_data),
                              chat_id = update.callback_query.message.chat_id,
                              message_id = update.callback_query.message.message_id)
        os.unlink(os.path.realpath(select_f_name))
        artists = callback_data.split(', ')
        insert_user(c, conn, 'kpop', chat_id, artists)

def include_pop_artist(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM pop_artist")
    alphabet_list = sorted(list(set([artist[0][0].upper() if artist[0][0].isalpha() else artist[0][0] for artist in c.fetchall()])))
    alphabet_show_list = [InlineKeyboardButton(alph, callback_data="alph, "+alph) for alph in alphabet_list]
    menu = build_menu(alphabet_show_list, 3)
    alphabet_show_markup = InlineKeyboardMarkup(menu)
    update.message.reply_text("알림 받고 싶은 가수의 시작 알파벳을 선택해주세요.\n"
                              "신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.", reply_markup=alphabet_show_markup)

def pop_artist_callback(bot, update):
    data = update.callback_query.data.split(', ')
    alph = data[1]
    chat_id = str(update.callback_query.message.chat_id)

    f = NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, dir='.')
    select_f_name = os.path.relpath(f.name)
    f.close()


    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_artist = get_artist_list(c, 'pop', chat_id)
    c.execute("SELECT artist FROM pop_artist")
    artist_option = sorted([artist[0] for artist in c.fetchall() if artist[0] not in user_artist and startswith(alph, artist[0][0])])

    artist_show_list = [InlineKeyboardButton(artist, callback_data="pop" + artist + ", " + select_f_name + ', ' + alph) for artist in
                        artist_option] + [InlineKeyboardButton('선택 종료', callback_data="pop" + "선택 종료" + ", " + select_f_name + ', ' + alph)]
    menu = build_menu(artist_show_list, 3)
    artist_show_markup = InlineKeyboardMarkup(menu)
    c.close()
    conn.close()

    bot.edit_message_text(text="알림 받고 싶은 가수를 선택해주세요.",
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id,
                          reply_markup=artist_show_markup)

def include_pop_callback(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    data = update.callback_query.data.split(', ')
    data_selected = data[0]
    if data_selected.startswith('pop'):
        data_selected = data_selected[3:]
    select_f_name = data[1]
    alph = data[2]
    chat_id = str(update.callback_query.message.chat_id)

    c.execute("SELECT artist FROM pop_artist")
    artist_option = sorted([artist[0] for artist in c.fetchall() if startswith(alph, artist[0][0])])

    temp_file = open(select_f_name, mode='a+', encoding='utf-8')
    temp_file.seek(0)
    selected_data = temp_file.read()

    user_artist = get_artist_list(c, 'pop', chat_id)
    if user_artist:
        callback_data = ', '.join(user_artist) + ', '
    else:
        callback_data = ''
    if selected_data:
        callback_data = callback_data + selected_data + ', ' + data_selected
        temp_file.write(', ' + data_selected)
    else:
        callback_data = callback_data + data_selected
        temp_file.write(data_selected)
    temp_file.close()

    if data_selected.split(", ")[-1] != "선택 종료" and data_selected.split(", ")[-1] != "알림 취소":
        option_artist_left = [i for i in artist_option if i not in callback_data.split(', ')]
        show_list = [InlineKeyboardButton(artist, callback_data="pop" + artist + ", " + select_f_name + ', ' + alph) for artist in
                     option_artist_left]
        menu = build_menu(show_list, 3) + [
            [InlineKeyboardButton("선택 종료", callback_data="pop" + "선택 종료" + ", " + select_f_name + ', ' + alph)]]
        show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}가 선택되었습니다.\n추가 가수를 선택해 주세요.".format(callback_data),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=show_markup)
        c.close()
        conn.close()

    elif data_selected == '알림 취소':
        bot.edit_message_text(text="아무것도 선택하지 않았습니다.\n새로운 노래 다운로드 링크 알림이 가지 않습니다.\n",
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        user_id = is_user(c, chat_id)
        if user_id:
            c.execute("DELETE FROM users_pop_artist WHERE user_id = {}".format(user_id))
        os.unlink(os.path.realpath(select_f_name))
        conn.commit()
        c.close()
        conn.close()

    else:
        callback_data = callback_data[:-7]
        bot.edit_message_text(text="선택이 종료되었습니다.\n{}이 선택되었습니다.\n새로운 곡이 올라오면 알림을 보내드릴게요.\n\n"
                                   "신청 목록에서 제외하고 싶은 가수가 있다면 [/exclude_artist]를 터치해주세요^^.\n"
                                   "이전으로 돌아가시려면 [/include_pop_artist]를 터치해주세요.\n"
                                   "신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.\n"
                                   "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.".format(callback_data),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        os.unlink(os.path.realpath(select_f_name))
        artists = callback_data.split(', ')
        insert_user(c, conn, 'pop', chat_id, artists)

def check_artist(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_artist = get_artist_list(c, 'kpop', chat_id) + get_artist_list(c, 'pop', chat_id)
    c.close()
    conn.close()
    if user_artist:
        text = "{} 아티스트를 선택했습니다.\n".format(', '.join(user_artist))
    else:
        text = "선택하신 아티스트가 없습니다.\n"
    update.message.reply_text(text +
                              "이전으로 돌아가시려면 [/new_download]를 터치해주세요."
                              "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")

def exclude_artist(bot, update):
    chat_id = str(update.message['chat']['id'])
    f = NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, dir='.')
    rel_f_name = os.path.relpath(f.name)

    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_artist = get_artist_list(c, 'kpop', chat_id) + get_artist_list(c, 'pop', chat_id)
    f.write(', '.join(user_artist))
    f.close()
    artist_show_list = [InlineKeyboardButton(artist, callback_data='ex' + artist + ", " + rel_f_name) for artist in user_artist]\
                       + [InlineKeyboardButton('알림 취소', callback_data='ex' + '알림 취소' + ", " + rel_f_name)]
    menu = build_menu(artist_show_list, 3)
    artist_show_markup = InlineKeyboardMarkup(menu)
    c.close()
    conn.close()

    update.message.reply_text("제외하고 싶은 아티스트를 선택해주세요.", reply_markup=artist_show_markup)

def exclude_callback(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    data = update.callback_query.data.split(', ')
    data_selected = data[0]
    if data_selected.startswith('ex'):
        data_selected = data_selected[2:]
    f_name = data[1]
    chat_id = str(update.callback_query.message.chat_id)

    with open(f_name, mode='r', encoding='utf-8') as temp_file:
        temp_file.seek(0)
        temp_data = temp_file.read()
    os.unlink(os.path.realpath(f_name))
    callback_data = temp_data.split(', ')
    if data_selected != '선택 종료':
        callback_data.remove(data_selected)
    callback_data = ', '.join(callback_data)

    f = NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, dir='.')
    f_name = os.path.relpath(f.name)
    f.write(callback_data)
    f.close()

    if data_selected.split(", ")[-1] != "선택 종료" and data_selected.split(", ")[-1] != "알림 취소":
        option_artist_left = [i for i in callback_data.split(', ')]
        show_list = [InlineKeyboardButton(artist, callback_data= "ex" + artist + ", " + f_name) for artist in option_artist_left]
        menu = build_menu(show_list, 3) + [[InlineKeyboardButton("선택 종료", callback_data="ex" + "선택 종료" + ", " + f_name)]]
        show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}가 선택되었습니다.\n제외할 아티스트를 추가로 선택해 주세요.".format(callback_data),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=show_markup)
        c.close()
        conn.close()

    elif data_selected == '알림 취소':
        bot.edit_message_text(text="알림을 취소하셨습니다.\n새로운 노래 다운로드 링크 알림이 가지 않습니다.\n",
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        user_id = is_user(c, chat_id)
        if user_id:
            c.execute("DELETE FROM users_kpop_artist WHERE user_id = {}".format(user_id))
        os.unlink(os.path.realpath(f_name))
        conn.commit()
        c.close()
        conn.close()

    else:
        bot.edit_message_text(text = "선택이 종료되었습니다.\n{} 아티스트의 새로운 곡이 올라오면 알림을 보내드릴게요.\n\n"
                                     "아티스트를 다시 추가하고 싶으면 [/include_kpop_artist]를 터치해주세요^^.\n"
                                     "이전으로 돌아가시려면 [/new_download]를 터치해주세요.\n"
                                     "다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.".format(callback_data),
                              chat_id = update.callback_query.message.chat_id,
                              message_id = update.callback_query.message.message_id)
        os.unlink(os.path.realpath(f_name))
        artists = callback_data.split(', ')
        insert_user(c, conn, 'kpop', chat_id, artists)
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        insert_user(c, conn, 'pop', chat_id, artists)
        update.message.reply_text("다른 서비스를 다시 신청하고 싶으시면 [/help]를 터치해주세요.")

def search(bot, update):
    show_list = [InlineKeyboardButton('k-pop', callback_data="artist_han"), InlineKeyboardButton('pop song', callback_data="artist_alph")]
    menu = build_menu(show_list, 1)
    show_markup = InlineKeyboardMarkup(menu)
    update.message.reply_text("찾고 싶은 곡의 종류를 선택해주세요.", reply_markup=show_markup)

def kpop_artist_han_callback(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM kpop_artist")
    chosung_list = sorted(
        list(set([get_chosung(artist[0][0]) if is_hangul(artist[0][0]) else artist[0][0].upper() if artist[0][
            0].isalpha() else artist[0][0] for artist in c.fetchall()])))
    chosung_show_list = [InlineKeyboardButton(han, callback_data="st, " + "k-pop, " + han) for han in
                        chosung_list]
    menu = build_menu(chosung_show_list, 3)
    chosung_show_markup = InlineKeyboardMarkup(menu)
    bot.edit_message_text(text="알림 받고 싶은 가수의 시작 알파벳을 선택해주세요.",
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id,
                          reply_markup=chosung_show_markup)

def pop_artist_alph_callback(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM pop_artist")
    alphabet_list = sorted(
        list(set([artist[0][0].upper() if artist[0][0].isalpha() else artist[0][0] for artist in c.fetchall()])))

    alphabet_show_list = [InlineKeyboardButton(alph, callback_data="st, " + "pop song, " + alph) for alph in alphabet_list]
    menu = build_menu(alphabet_show_list, 3)
    alphabet_show_markup = InlineKeyboardMarkup(menu)
    bot.edit_message_text(text="알림 받고 싶은 가수의 시작 알파벳을 선택해주세요.",
                                     chat_id=update.callback_query.message.chat_id,
                                     message_id=update.callback_query.message.message_id,
                                     reply_markup=alphabet_show_markup)

def search_type_callback(bot, update):
    data = update.callback_query.data.split(', ')
    data_selected = data[1]
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    if data_selected == 'k-pop':
        han = data[2]
        c.execute("SELECT artist FROM kpop_artist")

        c.execute("SELECT artist FROM kpop_artist")
        artist_option = sorted([artist[0] for artist in c.fetchall() if startswith(han, artist[0][0])])
        artist_show_list = [InlineKeyboardButton(artist, callback_data="secall, kpop, " + artist)
                            for artist in artist_option]
        menu = build_menu(artist_show_list, 3) +\
               [[InlineKeyboardButton('이전', callback_data="artist_han")] + [InlineKeyboardButton('선택 취소', callback_data="secall, 선택 취소, 더미")]]
        artist_show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(han),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=artist_show_markup)

    elif data_selected == 'pop song':
        alph = data[2]
        c.execute("SELECT artist FROM pop_artist")
        option_artist = sorted([artist[0] for artist in c.fetchall() if startswith(alph, artist[0][0])])
        show_list = [InlineKeyboardButton(artist, callback_data="secall, pop, " + artist) for artist in option_artist]
        menu = build_menu(show_list, 3) +\
               [[InlineKeyboardButton('이전', callback_data="artist_alph")] + [InlineKeyboardButton('선택 취소', callback_data="secall, 선택 취소, 더미")]]
        show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(alph),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=show_markup)
    c.close()
    conn.close()

def search_callback(bot, update):
    data = update.callback_query.data.split(', ')
    song_type = data[1]
    artist = data[2]

    if song_type == '선택 취소':
        bot.edit_message_text(text="선택을 취소하셨습니다.",
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="다시 검색하시려면 [/search]를 터치해주세요\n"
                             "다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")
        return

    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    song_infos = get_song_list(c, song_type, artist)
    c.close()
    conn.close()
    if len(song_infos) > 1:
        show_list = [InlineKeyboardButton(song_info[2] + ' - ' + song_info[1], callback_data="send, " + song_type + ", " + str(song_info[0])) for song_info in song_infos] \
                    + [InlineKeyboardButton('get all', callback_data="send, " + song_type + ", " + "get all, " + str(song_infos[0][0]))]
        menu = build_menu(show_list, 1)
        show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(artist),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup = show_markup)
    else:
        song_info = song_infos[0]
        song = song_info[1]
        artist = song_info[2]
        link = song_info[3]
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(artist + ' - ' + song),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="곡 : " + artist + ' - ' + song + \
                             '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                             '\n다운로드 링크 : ' + link + "\n\n")
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="다시 검색하시려면 [/search]를 터치해주세요."
                             "다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")

def send_callback(bot, update):
    data = update.callback_query.data.split(', ')
    song_type = data[1]
    song_id = data[-1]
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    if len(data) == 3:
        c.execute("SELECT song, artist, link FROM {}_song WHERE id = {}".format(song_type, song_id))
        song, artist, link = c.fetchone()
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(artist + ' - ' + song),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="곡 : " + artist + ' - ' + song + \
                             '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                             '\n다운로드 링크 : ' + link + "\n\n")
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="다시 검색하시려면 [/search]를 터치해주세요."
                             "다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")
    else:
        c.execute("SELECT artist FROM {}_song WHERE id = {}".format(song_type, song_id))
        artist = c.fetchone()[0]
        song_infos = get_song_list(c, song_type, artist)
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(artist),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        for song_info in song_infos:
            song = song_info[1]
            link = song_info[3]
            bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                            text="곡 : " + artist + ' - ' + song + \
                                 '\n유튜브 링크 : ' + get_youtube_url(artist + ' - ' + song) + \
                                 '\n다운로드 링크 : ' + link + "\n\n")
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="다시 검색하시려면 [/search]를 터치해주세요."
                             "다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")
    c.close()
    conn.close()



def get_chosung(word):
    chosung = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
               'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    for c in word:
        cc = ord(c) - 44032
        cho = cc // (21 * 28)
        return chosung[cho]

def is_hangul(word):
    hangul_re = re.compile(r"[ㄱ - | 가-힣]")
    return hangul_re.search(word) is not None
from string import punctuation
def startswith(pattern, word):
    if pattern in punctuation:
        pattern = "\\" + pattern
    if is_hangul(word):
        word = get_chosung(word)
    return re.match(pattern, word, re.I)

if __name__=='__main__':
    token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
    # token = "790146878:AAFKnWCnBV9WMSMYPnfcRXukmftgDyV_BlY" #this is a test bot

    bot = Bot(token=token)

    updater = Updater(token)

    updater.dispatcher.add_handler(MessageHandler(Filters.text, get_message))
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('drive', drive))
    updater.dispatcher.add_handler(CommandHandler('command', command))
    updater.dispatcher.add_handler(CommandHandler('all_artists', get_all_artists))
    updater.dispatcher.add_handler(CommandHandler('search', search))
    updater.dispatcher.add_handler(CommandHandler('chart', chart))
    updater.dispatcher.add_handler(CommandHandler('check_service', check_service))
    updater.dispatcher.add_handler(CommandHandler('melon_chart', melon_chart))
    updater.dispatcher.add_handler(CommandHandler('billboard_chart', billboard_chart))
    updater.dispatcher.add_handler(CommandHandler('new_download', new_download))
    updater.dispatcher.add_handler(CommandHandler('include_kpop_artist', include_kpop_artist))
    updater.dispatcher.add_handler(CommandHandler('include_pop_artist', include_pop_artist))
    updater.dispatcher.add_handler(CommandHandler('check_artist', check_artist))
    updater.dispatcher.add_handler(CommandHandler('exclude_artist', exclude_artist))

    updater.dispatcher.add_handler(CallbackQueryHandler(drive_callback,
                                                        pattern='^drive'))
    updater.dispatcher.add_handler(CallbackQueryHandler(drive_selected,
                                                        pattern='^drsel'))
    updater.dispatcher.add_handler(CallbackQueryHandler(download_url,
                                                        pattern='^url'))

    updater.dispatcher.add_handler(CallbackQueryHandler(include_kpop_callback,
                                                        pattern='^kp'))
    updater.dispatcher.add_handler(CallbackQueryHandler(kpop_artist_callback,
                                                        pattern='^han'))
    updater.dispatcher.add_handler(CallbackQueryHandler(include_pop_callback,
                                                        pattern='^pop'))
    updater.dispatcher.add_handler(CallbackQueryHandler(pop_artist_callback,
                                                        pattern='^alph'))

    updater.dispatcher.add_handler(CallbackQueryHandler(exclude_callback,
                                                        pattern='^ex'))

    updater.dispatcher.add_handler(CallbackQueryHandler(pop_artist_alph_callback,
                                                        pattern='^artist_alph'))
    updater.dispatcher.add_handler(CallbackQueryHandler(kpop_artist_han_callback,
                                                        pattern='^artist_han'))
    updater.dispatcher.add_handler(CallbackQueryHandler(search_type_callback,
                                                        pattern='^st'))
    updater.dispatcher.add_handler(CallbackQueryHandler(search_callback,
                                                        pattern='^secall'))
    updater.dispatcher.add_handler(CallbackQueryHandler(send_callback,
                                                        pattern='^send'))

    updater.start_polling()
    updater.idle()