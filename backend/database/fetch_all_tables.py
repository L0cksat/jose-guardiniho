import sqlite3

connection = sqlite3.connect("jose.db")

print(connection.execute("SELECT name FROM sqlite_master").fetchall())

print(connection.execute("SELECT * FROM match_frame").fetchall())

