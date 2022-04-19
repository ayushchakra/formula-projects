import sqlite3

conn = sqlite3.connect('database.db')

conn.execute("CREATE TABLE kicad_artifacts (board_name TEXT, commits TEXT, schematic TEXT, layout TEXT, bom TEXT)")

conn.close()
