import sqlite3
con = sqlite3.connect('svos.db')
cur = con.cursor()
rows = cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print('DB: svos.db')
for name, sql in rows:
    print(f'-- {name}')
    print(sql)
    print()
