from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from tempfile import NamedTemporaryFile
import sqlite3
from make_db import insert_user, is_user, get_song_list, get_artist_list
from new_song_crawl import get_youtube_url
import string
import os, re

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
        '차트에 새로 올라오는 노래 알림을 받고 싶다면 [/chart]를 터치해주세요.\n'
        '새로운 곡 다운로드 링크 알림을 받고 싶으시면 [/new_download]를 터치해주세요\n'
        '도움이 필요하시면 [/help]를 터치해주세요.')

def stop(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()

    user = is_user(c, chat_id)
    if user:
        user_id = user[0]
        c.execute("DELETE FROM users_kpop WHERE user_id = {}".format(user_id))
        c.execute("DELETE FROM users_pop WHERE user_id = {}".format(user_id))
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
        '노래를 찾고 싶으시면 [/search]를 터치해주세요.')

def chart(bot, update):
    update.message.reply_text(
        '멜론 차트에 새로 올라오는 노래 알림을 받고 싶다면 [/melon_chart]를 터치해주세요.\n'
        '빌보드 차트에 새로 올라오는 노래 알림을 받고 싶다면 [/billboard_chart]를 터치해주세요.\n')

def melon_chart(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    user_id = is_user(c, chat_id)
    if not user_id:
        c.execute("INSERT INTO users VALUES(NULL, '{}')".format(chat_id))
        user_id = c.lastrowid
    artist_id = 1
    c.execute("SELECT * FROM users_charts WHERE user_id = {}".format(user_id))
    if c.fetchone():
        c.execute("DELETE FROM users_charts WHERE user_id = {}".format(user_id))
        update.message.reply_text("멜론 차트에 알림을 취소하셨습니다.\n"
                                  "다시 신청하고 싶으시면 [/melon_chart]를 터치해주세요.")
    else:
        c.execute("INSERT INTO users_charts VALUES(?, ?)", (user_id, artist_id))
        update.message.reply_text("앞으로 멜론 차트에 새로운 노래가 올라오면 보내도록 하겠습니다.\n"
                                  "취소하고 싶으시면 [/melon_chart]을 터치해주세요.")
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
    artist_id = 2
    c.execute("SELECT * FROM users_charts WHERE user_id = {}".format(user_id))
    if c.fetchone():
        c.execute("DELETE FROM users_charts WHERE user_id = {}".format(user_id))
        update.message.reply_text("빌보드 차트에 알림을 취소하셨습니다.\n"
                                  "다시 신청하고 싶으시면 [/billboard_chart]를 터치해주세요.")
    else:
        c.execute("INSERT INTO users_charts VALUES(?, ?)", (user_id, artist_id))
        update.message.reply_text("앞으로 빌보드 차트에 새로운 노래가 올라오면 보내도록 하겠습니다.\n"
                                  "취소하고 싶으시면 [/billboard_chart]을 터치해주세요.")
    conn.commit()
    c.close()
    conn.close()

def new_download(bot, update):
    update.message.reply_text(
        '케이팝 신곡 알림을 받고 싶다면 [/include_kpop_artist]를 터치해주세요.\n'
        '팝송 신곡 알림을 받고 싶다면 [/include_pop_artist]를 터치해주세요.\n'
        '신청한 가수를 확인하고 싶다면 [/check_artist]를 터치해주세요.\n'
        '신청 목록에서 제외하고 싶은 가수가 있다면 [/exclude_artist]를 터치해주세요.\n\n'
        '신청 가능한 가수들이 궁금하다면 [/artist]를 터치해주세요.'
    )

def artist(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM kpop_artist")
    kpop_artists = [artist[0] for artist in c.fetchall()]
    c.execute("SELECT artist FROM pop_artist")
    pop_artists = [artist[0] for artist in c.fetchall()]
    update.message.reply_text(
        "한국 가수는 다음과 같이 있습니다.\n" +
        ', '.join(kpop_artists) + '\n\n' +
        "팝송 가수는  다음과 같이 있습니다.\n" +
        ', '.join(pop_artists)
    )

def include_kpop_artist(bot, update):
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT artist FROM kpop_artist")
    chosung_list = sorted(
        list(set([get_chosung(artist[0][0]) if is_hangul(artist[0][0]) else artist[0][0].upper() if artist[0][0].isalpha() else artist[0][0] for artist in c.fetchall()])))
    hangul_show_list = [InlineKeyboardButton(han, callback_data="han, "+han) for han in chosung_list]
    menu = build_menu(hangul_show_list, 3)
    hangul_show_markup = InlineKeyboardMarkup(menu)
    update.message.reply_text("알림 받고 싶은 가수의 시작 초성 또는 알파벳을 선택해주세요.", reply_markup=hangul_show_markup)

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
    artist_show_list = [InlineKeyboardButton(artist, callback_data="kp" + artist + ", " + select_f_name + ', ' + han)
                        for artist in artist_option] + [InlineKeyboardButton('선택 종료', callback_data="kp" + "선택 종료"
                                                                                                    + ", " + select_f_name + ', ' + han)]
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
                                     "이전으로 돌아가시려면 [/new_download]를 터치해주세요.\n"
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
    update.message.reply_text("알림 받고 싶은 가수의 시작 알파벳을 선택해주세요.", reply_markup=alphabet_show_markup)

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
                                   "이전으로 돌아가시려면 [/new_download]를 터치해주세요.\n"
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
                            for artist in artist_option] + [InlineKeyboardButton('선택 취소', callback_data="secall, 선택 취소, 더미")]
        menu = build_menu(artist_show_list, 3)
        artist_show_markup = InlineKeyboardMarkup(menu)
        bot.edit_message_text(text="{}이(가) 선택되었습니다.".format(han),
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id,
                              reply_markup=artist_show_markup)

    elif data_selected == 'pop song':
        alph = data[2]
        c.execute("SELECT artist FROM pop_artist")
        option_artist = sorted([artist[0] for artist in c.fetchall() if startswith(alph, artist[0][0])])
        show_list = [InlineKeyboardButton(artist, callback_data="secall, pop, " + artist) for artist in option_artist]+\
                         [InlineKeyboardButton('선택 취소', callback_data="secall, 선택 취소, 더미")]
        menu = build_menu(show_list, 3)
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
    data_selected = data[2]
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    if song_type == '선택 취소':
        print('선택이 취소되었습니다')
        bot.edit_message_text(text="선택을 취소하셨습니다.",
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="다시 검색하시려면 [/search]를 터치해주세요\n"
                             "다른 서비스를 신청하고 싶으시면 [/help]를 터치해주세요.")
        c.close()
        conn.close()
        return
    bot.edit_message_text(text="{}가 선택되었습니다.".format(data_selected),
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)
    song_infos = get_song_list(c, song_type, data_selected)
    for song_info in song_infos:
        song_name = song_info[0]
        song_artist = song_info[1]
        song_link = song_info[2]
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="곡 : " + song_artist + ' - ' + song_name + \
                             '\n유튜브 링크 : ' + get_youtube_url(song_name + ' ' + song_artist) + \
                             '\n다운로드 링크 : ' + song_link + "\n\n")
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
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('artist', artist))
    updater.dispatcher.add_handler(CommandHandler('search', search))
    updater.dispatcher.add_handler(CommandHandler('chart', chart))
    updater.dispatcher.add_handler(CommandHandler('melon_chart', melon_chart))
    updater.dispatcher.add_handler(CommandHandler('billboard_chart', billboard_chart))
    updater.dispatcher.add_handler(CommandHandler('new_download', new_download))
    updater.dispatcher.add_handler(CommandHandler('include_kpop_artist', include_kpop_artist))
    updater.dispatcher.add_handler(CommandHandler('include_pop_artist', include_pop_artist))
    updater.dispatcher.add_handler(CommandHandler('check_artist', check_artist))
    updater.dispatcher.add_handler(CommandHandler('exclude_artist', exclude_artist))
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



    updater.dispatcher.add_handler(CallbackQueryHandler(search_callback,
                                                        pattern='^secall'))
    updater.dispatcher.add_handler(CallbackQueryHandler(pop_artist_alph_callback,
                                                        pattern='^artist_alph'))
    updater.dispatcher.add_handler(CallbackQueryHandler(kpop_artist_han_callback,
                                                        pattern='^artist_han'))
    updater.dispatcher.add_handler(CallbackQueryHandler(search_type_callback,
                                                        pattern='^st'))

    updater.start_polling()
    updater.idle()