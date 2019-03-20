import sqlite3


def make_db():
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `user` INTEGER )"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS charts ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `chart` TEXT )"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS users_charts ( `user_id` INTEGER, `charts_id` INTEGER, FOREIGN KEY(`user_id`)"
        " REFERENCES `users`(`id`), FOREIGN KEY(`charts_id`) REFERENCES `charts`(`id`) )"
    )
    c.execute("SELECT * FROM users_charts")
    if not c.fetchone():
        for chart in ['melon', 'billboard']:
            c.execute("INSERT INTO charts VALUES(NULL, '{}')".format(chart))

    c.execute(
        "CREATE TABLE IF NOT EXISTS kpop_artist ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `artist` TEXT )"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS users_kpop_artist ( `user_id` INTEGER, `kpop_artist_id` INTEGER, FOREIGN KEY(`user_id`)"
        " REFERENCES `users`(`id`), FOREIGN KEY(`kpop_artist_id`) REFERENCES `kpop_artist`(`id`) )"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS kpop_song ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `song` TEXT, `artist` TEXT, `link` TEXT )"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS kpop_song_artist ( `kpop_song_id` INTEGER, `kpop_artist_id` INTEGER, FOREIGN KEY(`kpop_artist_id`)"
        " REFERENCES `kpop_artist`(`id`), FOREIGN KEY(`kpop_song_id`) REFERENCES `kpop_song`(`id`) )"
    )


    c.execute(
        "CREATE TABLE IF NOT EXISTS pop_artist ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `artist` TEXT )"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS users_pop_artist ( `user_id` INTEGER, `pop_artist_id` INTEGER, FOREIGN KEY(`user_id`)"
        " REFERENCES `users`(`id`), FOREIGN KEY(`pop_artist_id`) REFERENCES `pop_artist`(`id`) )"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS pop_song ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `song` TEXT, `artist` TEXT, `link` TEXT )"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS pop_song_artist ( `pop_song_id` INTEGER, `pop_artist_id` INTEGER, FOREIGN KEY(`pop_artist_id`)"
        " REFERENCES `pop_artist`(`id`), FOREIGN KEY(`pop_song_id`) REFERENCES `pop_song`(`id`) )"
    )
    conn.commit()
    c.close()
    conn.close()

def insert_song(c, type, song_info):
    song = song_info[0]
    artist = song_info[1]
    artistss = artist.split(', ')
    link = song_info[2]

    if type == 'kpop':
        c.execute("INSERT INTO kpop_song VALUES(NULL, ?, ?, ?)", (song, artist, link))
        song_id = c.lastrowid
        for artists in artistss:
            artist_id = is_artist(c, type, artists)
            if not artist_id:
                artist_id = insert_artist(c, type, artists)
            c.execute("INSERT INTO kpop_song_artist VALUES(?, ?)", (song_id, artist_id))

    elif type == 'pop':
        c.execute("INSERT INTO pop_song VALUES(NULL, ?, ?, ?)", (song, artist, link))
        song_id = c.lastrowid
        for artists in artistss:
            artist_id = is_artist(c, type, artists)
            if not artist_id:
                artist_id = insert_artist(c, type, artists)
            c.execute("INSERT INTO pop_song_artist VALUES(?, ?)", (song_id, artist_id))

def insert_artist(c, type, artist):
    if type == 'kpop':
        if not is_artist(c, type, artist):
            c.execute("INSERT INTO kpop_artist VALUES(NULL, '{}')".format(artist))
            return c.lastrowid
        else:
            return
    elif type == 'pop':
        if not is_artist(c, type, artist):
            c.execute("INSERT INTO pop_artist VALUES(NULL, '{}')".format(artist))
            return c.lastrowid

def insert_user(c, conn, type, user, artists):
    user_id = is_user(c, user)
    if not user_id:
        c.execute("INSERT INTO users VALUES(NULL, '{}')".format(user))
        user_id = c.lastrowid
    if type == 'kpop':
        c.execute("DELETE FROM users_kpop_artist WHERE user_id = '{}'".format(user_id))
        for artist in artists:
            c.execute("SELECT id FROM kpop_artist WHERE artist = '{}'".format(artist))
            artist_id = c.fetchone()
            if artist_id:
                artist_id = artist_id[0]
                c.execute("INSERT INTO users_kpop_artist VALUES(?, ?)", (user_id, artist_id))
    elif type == 'pop':
        c.execute("DELETE FROM users_pop_artist WHERE user_id = '{}'".format(user_id))
        for artist in artists:
            c.execute("SELECT id FROM pop_artist WHERE artist = '{}'".format(artist))
            artist_id = c.fetchone()
            if artist_id:
                artist_id = artist_id[0]
                c.execute("INSERT INTO users_pop_artist VALUES(?, ?)", (user_id, artist_id))
    conn.commit()
    c.close()
    conn.close()

def get_song_list(c, type, artist):
    song = []
    if type == 'kpop':
        c.execute(
            "SELECT song, kpop_song.artist, link FROM kpop_song, kpop_artist, kpop_song_artist WHERE kpop_artist.id = kpop_song_artist.kpop_artist_id AND"
            " kpop_song.id = kpop_song_artist.kpop_song_id AND kpop_artist.artist = '{}'".format(artist)
        )
        song = [row for row in c.fetchall()]
    elif type == 'pop':
        c.execute(
            "SELECT song, pop_song.artist, link FROM pop_song, pop_artist, pop_song_artist WHERE pop_artist.id = pop_song_artist.pop_artist_id AND"
            " pop_song.id = pop_song_artist.pop_song_id AND pop_artist.artist = '{}'".format(artist)
        )
        song = [row for row in c.fetchall()]
    return song

def get_artist_list(c, type, user):
    artists = []
    if type == 'kpop':
        c.execute(
            "SELECT artist FROM users, kpop_artist, users_kpop_artist WHERE kpop_artist.id = users_kpop_artist.kpop_artist_id AND"
            " users.id = users_kpop_artist.user_id AND user = '{}'".format(user)
        )
        artists = [row[0] for row in c.fetchall()]
    elif type == 'pop':
        c.execute(
            "SELECT artist FROM users, pop_artist, users_pop_artist WHERE pop_artist.id = users_pop_artist.pop_artist_id AND"
            " users.id = users_pop_artist.user_id AND user = '{}'".format(user)
        )
        artists = [row[0] for row in c.fetchall()]
    return artists

def get_user_list(c, type, artist):
    user = []
    if type == 'kpop':
        c.execute(
            "SELECT user FROM users, kpop_artist, users_kpop WHERE kpop_artist.id = users_kpop.kpop_artist_id AND"
            " users.id = users_kpop.user_id AND artist = '{}'".format(artist)
        )
        user = [row[0] for row in c.fetchall()]
    elif type == 'pop':
        c.execute(
            "SELECT user FROM users, pop_artist, users_pop WHERE pop.id = users_pop.pop_artist_id AND"
            " users.id = users_pop.user_id AND artist = '{}'".format(artist)
        )
        user = [row[0] for row in c.fetchall()]
    return user

def is_song(c, type, song_info):
    song = song_info[0]
    artist = song_info[1]
    if type == 'kpop':
        c.execute("SELECT id FROM kpop_song WHERE song = ? and artist = ?", (song, artist))
    elif type == 'pop':
        c.execute("SELECT id FROM pop_song WHERE song = ? and artist = ?", (song, artist))
    return c.fetchone()

def is_artist(c, type, artist):
    if type == 'kpop':
        c.execute("SELECT id FROM kpop_artist WHERE artist = '{}'".format(artist))
    elif type == 'pop':
        c.execute("SELECT id FROM pop_artist WHERE artist = '{}'".format(artist))
    artist_id = c.fetchone()
    if artist_id:
        return artist_id[0]
    else:
        return None

def is_user(c, user):
    c.execute("SELECT id FROM users WHERE user = '{}'".format(user))
    user_id = c.fetchone()
    if user_id:
        return user_id[0]
    else:
        return None