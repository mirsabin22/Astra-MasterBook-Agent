import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "masterbook_agent.db"

def connect():
    return sqlite3.connect(DB_PATH)