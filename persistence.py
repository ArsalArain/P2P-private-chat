from contextlib import contextmanager
from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).resolve().parent / "user.db"


@contextmanager
def _connection():
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                NAME TEXT UNIQUE NOT NULL,
                PASSWORD TEXT NOT NULL,
                IPADDRESS TEXT,
                PORT INTEGER
            );
            """
        )


def get_all_users():
    initialize_database()
    with _connection() as connection:
        rows = connection.execute("SELECT NAME FROM users;")
        return [row[0] for row in rows]


def get_user_password(username):
    initialize_database()
    with _connection() as connection:
        row = connection.execute(
            "SELECT PASSWORD FROM users WHERE NAME = ?;",
            (username,),
        ).fetchone()
        return row[0] if row else None


def add_new_user(username, password):
    initialize_database()
    try:
        with _connection() as connection:
            connection.execute(
                "INSERT INTO users (NAME, PASSWORD) VALUES (?, ?);",
                (username, password),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def delete_user(username):
    initialize_database()
    with _connection() as connection:
        cursor = connection.execute(
            "DELETE FROM users WHERE NAME = ?;",
            (username,),
        )
        return cursor.rowcount > 0


def update_user_password(username, password):
    initialize_database()
    with _connection() as connection:
        cursor = connection.execute(
            "UPDATE users SET PASSWORD = ? WHERE NAME = ?;",
            (password, username),
        )
        return cursor.rowcount > 0


def update_user_address_port(username, ipaddress, port):
    initialize_database()
    with _connection() as connection:
        cursor = connection.execute(
            "UPDATE users SET IPADDRESS = ?, PORT = ? WHERE NAME = ?;",
            (ipaddress, port, username),
        )
        return cursor.rowcount > 0


def get_all_table():
    initialize_database()
    with _connection() as connection:
        return connection.execute("SELECT * FROM users;").fetchall()


def delete_all_users():
    initialize_database()
    with _connection() as connection:
        connection.execute("DELETE FROM users;")


initialize_database()
