from telegram import Bot
from telegram.ext import Updater, CommandHandler
import sqlite3
from make_db import insert_user_kpop

token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
bot = Bot(token=token)

def start(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    insert_user_kpop(c, chat_id)
    update.message.reply_text(
        '안녕하세요.\n'
        '새로운 노래 알림봇을 추가해주셔서 감사합니다.\n'
        '새로운 노래가 올라올 때마다 알림을 보내도록 하겠습니다.\n')
    conn.commit()
    c.close()
    conn.close()

def stop(bot, update):
    chat_id = str(update.message['chat']['id'])
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE user = {}".format(chat_id))
    user = c.fetchone()
    if user:
        user_id = user[0]
        c.execute("DELETE FROM users_kpop WHERE user_id = {}".format(user_id))
    conn.commit()
    c.close()
    conn.close()
    update.message.reply_text(
        '이용해주셔서 감사합니다.\n'
        '이제부터 새로운 노래 알림을 보내지 않습니다.\n')

updater = Updater(token)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('stop', stop))
updater.start_polling()
updater.idle()