import sqlite3

def initialize_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Create a table for user data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        cookies TEXT,
        otp TEXT,
        authenticity_token TEXT
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()