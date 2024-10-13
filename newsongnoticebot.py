from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, MessageHandler, CommandHandler, CallbackQueryHandler, Filters
from pydrive.drive import GoogleDrive
import sqlite3, json
from make_db import is_artist, get_song_list
from media_manager import g_auth_bot, upload_get_link, list_folder
import media_manager
from new_data_manager import NewNotice
from telegram.ext.dispatcher import run_async

import os, re, difflib
import requests
from bs4 import BeautifulSoup


@run_async
def get_message(bot, update):
    chat_id = str(update.message['chat']['id'])
    text = update.message.text
    if len(text) == 57:
        file_name = 'gauth_code.json'
        with open(file_name, 'w') as f:
            json.dump({chat_id: text}, f)


    elif text.startswith("https://www.you") or text.startswith("https://you"):
        link = text
        show_list = [InlineKeyboardButton("동영상", callback_data="url, 동영상, " + link), InlineKeyboardButton("음원",
                                                                                                          callback_data="url, 음원, " + link)]
        menu = build_menu(show_list, 2)
        show_markup = InlineKeyboardMarkup(menu)
        bot.sendMessage(text="동영상 또는 음원을 골라주세요.",
                        chat_id=chat_id,
                        reply_markup=show_markup)


def show_dif(a, b):
    result = difflib.ndiff(a, b)
    result = ''.join(result)
    return (result.count('+') + result.count('-')) / (len(result) + 1)


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
        '노래를 찾고 싶으시면 [/search]를 터치해주세요\n'
        '텍스트로 검색하는 방법을 알고 싶으시면 [/command]를 터치해주세요.\n'
        '드라이브 업로드 폴더를 설정하고 싶으시면 [/drive]를 터치해주세요.\n'
        '도움이 필요하시면 [/help]를 터치해주세요.')


def help(bot, update):
    update.message.reply_text(
        '노래를 찾고 싶으시면 [/search]를 터치해주세요.\n'
        '텍스트로 검색하는 방법을 알고 싶으시면 [/command]를 터치해주세요.\n\n'
        '신청 가능한 가수들이 궁금하시면 [/all_artists]를 터치해주세요.')


@run_async
def download_url(bot, update):
    data = update.callback_query.data.split(', ')
    down_type = data[1]
    link = data[2]
    chat_id = str(update.callback_query.message.chat_id)
    print(f'link {link}')
    bot.edit_message_text(text="{}을(를) 유튜브에서 다운로드 받는 중입니다.".format(link),
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)
    if down_type == '동영상':
        video_file_name = media_manager.YoutubeUtil(link=link).download_youtube_video()
        bot.edit_message_text(text="{}을(를) 유튜브에서 다운로드 받았습니다.".format(video_file_name),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        drive_auth = g_auth_bot(update, chat_id)
        if drive_auth:
            update.callback_query.message.reply_text("{}을(를) 드라이브에 업로드 중입니다.".format(video_file_name))
            print(video_file_name)
            try:
                upload_get_link(video_file_name, 'video')
            except Exception as e:
                print(e)
            update.callback_query.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                                     "구글 드라이브에서 확인해주세요.".format(video_file_name))
        else:
            drive_auth = g_auth_bot(update, 'my')
            update.callback_query.message.reply_text("인증에 실패하셨습니다.")
            update.callback_query.message.reply_text("{}을(를) 드라이브에 업로드 중입니다.".format(video_file_name))
            video_drive_link = upload_get_link(drive_auth, video_file_name, chat_id)
            update.callback_query.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                                     "동영상 링크 : {}".format(video_file_name, video_drive_link))
    else:
        music_file_name = media_manager.YoutubeUtil(link=link).download_youtube_music_get_info()
        bot.edit_message_text(text="{}을(를) 유튜브에서 다운로드 받았습니다.".format(music_file_name),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        drive_auth = g_auth_bot(update, chat_id)
        if drive_auth:
            try:
                upload_get_link(music_file_name, 'music')
            except Exception as e:
                print(e)
            update.callback_query.message.reply_text("{}을(를) 업로드 완료했습니다.\n"
                                                     "구글 드라이브에서 확인해주세요.".format(music_file_name))


@run_async
def auth(bot, update):
    chat_id = str(update.message['chat']['id'])
    file = os.path.join("creds", chat_id + "creds.txt")
    if os.path.exists(file):
        os.unlink(file)
    g_auth_bot(update, chat_id)


@run_async
def drive(bot, update):
    chat_id = str(update.message['chat']['id'])
    gauth = g_auth_bot(update, chat_id)
    if gauth:
        drive = GoogleDrive(gauth)
        folder_list = list_folder(drive, 'root')
        if not folder_list:
            update.message.reply_text("폴더가 존재하지 않습니다.")
        children = list()
        for folder in folder_list:
            data = {'title': folder['title'],
                    'id': folder['id']}
            children.append(data)
        with open('drive_folder.json', 'w') as f:
            json.dump({'title': 'root', 'id': None, 'children': children}, f)
        titles_show_list = [InlineKeyboardButton(child['title'], callback_data="drive, " + str(i)) for i, child in
                            enumerate(children)]
        menu = build_menu(titles_show_list, 3) + [[InlineKeyboardButton("선택", callback_data="drive, " + "선택")]]
        titles_show_markup = InlineKeyboardMarkup(menu)
        update.message.reply_text("어느 폴더에 업로드할 지 선택해주세요.\n", reply_markup=titles_show_markup)
    else:
        update.message.reply_text("인증에 실패하셨습니다")


@run_async
def drive_callback(bot, update):
    chat_id = str(update.callback_query.message.chat_id)
    data = update.callback_query.data.split(', ')
    try:
        folder_idx = int(data[1])
    except ValueError:
        os.unlink('drive_folder.json')
        with open('creds/folder_id.json', 'r') as f:
            data = json.load(f)
        with open('creds/folder_id.json', 'w') as f:
            data.pop(chat_id, None)
            json.dump(data, f)
        bot.edit_message_text(text="기본 폴더가 선택되었습니다.",
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        return
    gauth = g_auth_bot(update, chat_id)
    if gauth:
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
                json.dump({'title': folder_title, 'id': folder_id, 'children': children}, f)
            titles_show_list = [InlineKeyboardButton(child['title'], callback_data="drive, " + str(i)) for i, child in
                                enumerate(children)]
            menu = build_menu(titles_show_list, 3) + [[InlineKeyboardButton('선택', callback_data='drsel')]]
            titles_show_markup = InlineKeyboardMarkup(menu)
            bot.edit_message_text(text="{}가 선택되었습니다.".format(folder_title),
                                  chat_id=update.callback_query.message.chat_id,
                                  message_id=update.callback_query.message.message_id,
                                  reply_markup=titles_show_markup)
        else:
            os.unlink('drive_folder.json')
            with open('creds/folder_id.json', 'r') as f:
                data = json.load(f)
            with open('creds/folder_id.json', 'w') as f:
                data.update({chat_id: folder_id})
                json.dump(data, f)
            bot.edit_message_text(text="{}가 선택되었습니다.".format(folder_title),
                                  chat_id=update.callback_query.message.chat_id,
                                  message_id=update.callback_query.message.message_id)
    else:
        update.message.reply_text("인증에 실패했습니다.")


def drive_selected(bot, update):
    chat_id = str(update.callback_query.message.chat_id)
    with open('drive_folder.json', 'r') as f:
        data = json.load(f)
        folder_title = data['title']
        folder_id = data['id']
    os.unlink('drive_folder.json')
    with open('creds/folder_id.json', 'r') as f:
        data = json.load(f)
    with open('creds/folder_id.json', 'w') as f:
        data.update({chat_id: folder_id})
        json.dump(data, f)
    bot.edit_message_text(text="{}가 선택되었습니다.".format(folder_title),
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)


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


def new_chart(bot, update):
    new_songs = NewNotice('songs.json')
    update.message.reply_text("\n".join([i + ' - ' + j for i, j in new_songs.get_data('kpop')]))
    update.message.reply_text("\n".join(new_songs.get_data('pop')))


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
    n = 20
    chosung_list = sorted(
        list(set(
            [get_chosung(artist[0]) if is_hangul(artist[0]) else artist[0].upper() if artist[0].isalpha() else artist[0]
             for artist in kpop_artists])))

    k_artists_by_chosung = ["- " + ', '.join([artist for artist in kpop_artists if startswith(chosung, artist[0])]) for
                            chosung in chosung_list]
    k_len = len(k_artists_by_chosung)
    for artist in [k_artists_by_chosung[k_len // n * j:k_len // n * (j + 1)] for j in range(n)]:
        update.message.reply_text('\n'.join(artist))

    update.message.reply_text(
        "팝송 가수는  다음과 같이 있습니다.\n"
    )
    alphabet_list = sorted(
        list(set([artist[0].upper() if artist[0].isalpha() else artist[0] for artist in pop_artists])))
    p_artists_by_alphabets = ["- " + ', '.join([artist for artist in pop_artists if startswith(alphabet, artist[0])])
                              for alphabet in alphabet_list]
    p_len = len(p_artists_by_alphabets)
    for artist in [p_artists_by_alphabets[p_len // n * j:p_len // n * (j + 1)] for j in range(n)]:
        update.message.reply_text('\n'.join(artist))

    update.message.reply_text(
        text="다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")


def search(bot, update):
    show_list = [InlineKeyboardButton('k-pop', callback_data="artist_han"),
                 InlineKeyboardButton('pop song', callback_data="artist_alph")]
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

    alphabet_show_list = [InlineKeyboardButton(alph, callback_data="st, " + "pop song, " + alph) for alph in
                          alphabet_list]
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
        menu = build_menu(artist_show_list, 3) + \
               [[InlineKeyboardButton('이전', callback_data="artist_han")] + [
                   InlineKeyboardButton('선택 취소', callback_data="secall, 선택 취소, 더미")]]
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
        menu = build_menu(show_list, 3) + \
               [[InlineKeyboardButton('이전', callback_data="artist_alph")] + [
                   InlineKeyboardButton('선택 취소', callback_data="secall, 선택 취소, 더미")]]
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
        artist_id = is_artist(c, song_type, artist)
        show_list = [InlineKeyboardButton(song_info[2] + ' - ' + song_info[1],
                                          callback_data="send, " + song_type + ", " + str(song_info[0])) for song_info
                     in song_infos] \
                    + [InlineKeyboardButton('get all',
                                            callback_data="send, " + song_type + ", " + "get all, " + str(artist_id))]
        menu = build_menu(show_list, 1)
        show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(artist),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=show_markup)
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
        c.execute("SELECT artist FROM {}_artist WHERE id = {}".format(song_type, song_id))
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


import urllib.parse


def get_youtube_url(keyword, limit=1):
    url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote_plus(keyword)
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


if __name__ == '__main__':
    token = 'YOUR_BOT_TOKEN_HERE'

    bot = Bot(token=token)

    updater = Updater(token)

    updater.dispatcher.add_handler(MessageHandler(Filters.text, get_message))
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('auth', auth))
    updater.dispatcher.add_handler(CommandHandler('drive', drive))
    updater.dispatcher.add_handler(CommandHandler('command', command))
    updater.dispatcher.add_handler(CommandHandler('all_artists', get_all_artists))
    updater.dispatcher.add_handler(CommandHandler('search', search))
    updater.dispatcher.add_handler(CommandHandler('new_chart', new_chart))

    updater.dispatcher.add_handler(CallbackQueryHandler(drive_callback,
                                                        pattern='^drive'))
    updater.dispatcher.add_handler(CallbackQueryHandler(drive_selected,
                                                        pattern='^drsel'))
    updater.dispatcher.add_handler(CallbackQueryHandler(download_url,
                                                        pattern='^url'))
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
