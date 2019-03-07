import sqlite3


def make_db():
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `user` INTEGER )"
    )

    c.execute(
        "CREATE TABLE IF NOT EXISTS kpop ( `id` INTEGER PRIMARY KEY AUTOINCREMENT, `KPOP` TEXT )"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS users_kpop ( `user_id` INTEGER, `kpop_id` INTEGER, FOREIGN KEY(`user_id`)"
        " REFERENCES `users`(`id`), FOREIGN KEY(`kpop_id`) REFERENCES `kpop`(`id`) )"
    )

def insert_query():
    conn = sqlite3.connect('user_info.db')
    c = conn.cursor()
    c.execute("SELECT * FROM kpop WHERE KPOP = '신청'")
    kpop_entry = c.fetchone()
    if not kpop_entry:
        c.execute("INSERT INTO kpop VALUES(NULL, '{}')".format("신청"))
    conn.commit()
    c.close()
    conn.close()

def insert_user_kpop(c, user):
    c.execute("SELECT id FROM users WHERE user = {}".format(user))
    me_entry = c.fetchone()
    if not me_entry:
        c.execute("INSERT INTO users VALUES(NULL, {})".format(user))
        user_id = c.lastrowid
    else:
        user_id = me_entry[0]

    c.execute("DELETE FROM users_kpop WHERE user_id = {}".format(user_id))
    c.execute("INSERT INTO users_kpop VALUES({}, {})".format(user_id, '1'))

def user_list(c, genre):
    user = []
    if genre == 'kpop':
        c.execute(
            "SELECT user FROM users, kpop, users_kpop WHERE kpop.id = users_kpop.kpop_id AND"
            " users.id = users_kpop.user_id AND KPOP = '{}'".format('신청')
        )
        user = [row[0] for row in c.fetchall()]
    return user
