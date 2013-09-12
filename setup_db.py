import sqlite3
db = sqlite3.connect('slow-screen.db')

c = db.cursor()

# Drop old tables
c.execute("DROP TABLE IF EXISTS config")

c.execute("CREATE TABLE config (key text, value text)")

default_config = [
    ('lastupdate',       '0'),
    ('stream',           'http://slowerinternet.com/slow-screen/playlist.json'),
    ('videodirectory',   'videos'),
    ('updateinterval',   '1000'), # in milliseconds
    ('playlist',         ''),
    ('nextplaylist',     ''),
]

c.executemany("INSERT INTO config VALUES(?,?)", default_config)

db.commit()
db.close()
