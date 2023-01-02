import sqlite3

conn =sqlite3.connect("mydatabase.db")

c = conn.cursor()

c.execute('''
    CREATE TABLE users (
        id INT NOT NULL,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    )
'''
)

c.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        name TEXT,
        description TEXT,
        size INTEGER,
        download_count INTEGER
    )
''')

conn.commit()

# Close the connection
conn.close()