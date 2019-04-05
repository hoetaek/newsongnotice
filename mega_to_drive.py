import sqlite3
from music_file import download_mega_link, upload_get_link, download_youtube_link
import schedule, time, os
from server import change_ip
from telegram import Bot
from telegram.error import NetworkError


def get_links():
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()

    c.execute("SELECT id, link, song, artist FROM kpop_song WHERE link LIKE '%mega%'")
    kpop_songs = [i for i in c.fetchall()]
    c.execute("SELECT id, link, song, artist FROM pop_song WHERE link LIKE '%mega%'")
    pop_songs = [i for i in c.fetchall()]
    c.close()
    conn.close()
    return kpop_songs, pop_songs

def get_mega_file(link, song="", artist=""):
    file, err = download_mega_link(link)
    if not file:
        if err.endswith("Can't determine download url"):
            conn = sqlite3.connect('user_info.db')
            c = conn.cursor()
            c.execute("SELECT song, artist FROM pop_song WHERE link LIKE '%mega%'")
            c.close()
            conn.close()
            file = download_youtube_link(song, artist, itunes=False)
        elif err.endswith("giving up"):
            bot.sendMessage(chat_id="580916113",
                            text="giving up, try again 300 sec later\n" + str(err))
            time.sleep(200)
            return get_mega_file(link)


        elif err.endswith("returned 509"):
            print("change the ip of the server and try again")
            change_ip()
            bot.sendMessage(chat_id="580916113",
                            text="change the ip of the server and try again\n" + str(err))
            return get_mega_file(link)
        else:
            bot.sendMessage(chat_id="580916113",
                            text="unknown error program exit\n" + str(err))
            raise SystemExit
    return file

def mega_to_drive(link):
    file = get_mega_file(link)
    return upload_get_link(file)

def every_mega_to_drive():
    kpop_songs, pop_songs = get_links()
    for kpop, pop in zip(kpop_songs[:1], pop_songs[:1]):
        kpop_id = kpop[0]
        kpop_link = kpop[1]
        pop_id = pop[0]
        pop_link = pop[1]

        print(kpop_id, pop_id)
        k_drive_link = mega_to_drive(kpop_link)
        p_drive_link = mega_to_drive(pop_link)
        conn = sqlite3.connect('user_info.db')
        c = conn.cursor()
        c.execute("UPDATE kpop_song SET link = ? WHERE id = ?", (k_drive_link, kpop_id))
        c.execute("UPDATE pop_song SET link = ? WHERE id = ?", (p_drive_link, pop_id))
        conn.commit()
        c.close()
        conn.close()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
token = '751248768:AAEJB5JcAh52nWfrSyKTEISGX8_teJIxNFw'
bot = Bot(token=token)

if __name__=='__main__':
    mega_to_drive()
    print("done")
    schedule.every(30).minutes.do(mega_to_drive)

    while True:
        schedule.run_pending()
        time.sleep(1)
