from music_file import upload_get_link, download_mega_link
import sqlite3
import time
from multiprocessing import Pool
import os


def start_working(data):
    conn = sqlite3.connect("user_info.db")
    c = conn.cursor()
    link_data = data[0]
    song_type = data[1]
    link_id = link_data[0]
    link = link_data[1]
    if link.startswith("https://mega."):
        file_path = download_mega_link(link)
        open_link = upload_get_link(file_path)
        os.unlink(file_path)
        c.execute("UPDATE {}_song SET link = ? WHERE id = ?".format(song_type), (open_link, link_id))
    conn.commit()
    c.close()
    conn.close()
    time.sleep(2)


for song_type in ["kpop", "pop"]:
    conn = sqlite3.connect("user_info.db")
    c = conn.cursor()
    c.execute("SELECT id, link FROM {}_song".format(song_type))
    links = [[link, song_type] for link in c.fetchall()]
    c.close()
    conn.close()
    pool = Pool(processes=3)
    pool.map(start_working, links)
    # for link in links:
    #     start_working(link)
