import sqlite3

connection = sqlite3.connect("jose.db")

connection.execute(
    """
    INSERT INTO match_frame VALUES (1, 'match-tick-4600', 4600, 'home', 3, 8, 1)

    """
)

connection.commit()
connection.close()