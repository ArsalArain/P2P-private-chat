"""Optional manual entry point for initializing the local database."""

from persistence import initialize_database


if __name__ == "__main__":
    initialize_database()
    print("SQLite database initialized")