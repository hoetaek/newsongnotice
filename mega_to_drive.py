from music_file import upload_get_link, download_mega_link
import sqlite3
import os

conn = sqlite3.connect("user_info.db")
c = conn.cursor()
for song_type in ["kpop", "pop"]:
    c.execute("SELECT id, link FROM {}_song".format(song_type))
    links = [link for link in c.fetchall()]

    for link_data in links:
        print(link_data)
        link_id = link_data[0]
        link = link_data[1]
        file_path = download_mega_link(link)
        print(file_path)
        open_link = upload_get_link(file_path)
        print(open_link)
        os.unlink(file_path)
        c.execute("UPDATE {}_song SET link = ? WHERE id = ?".format(song_type), (open_link, link[0]))
        conn.commit()
        c.close()
        conn.close()
        break
    break