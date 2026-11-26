import sqlite3

connection = sqlite3.connect("jose.db")
connection.execute(
    """
    CREATE TABLE IF NOT EXISTS match_frame (
        id INTEGER PRIMARY KEY,
        match_id TEXT,
        tick INTEGER,
        user_team TEXT,
        flank_below INTEGER,
        flank_above INTEGER,
        press_count INTEGER,
        UNIQUE (match_id, tick)
    )
    """
)

connection.commit()
connection.close()

