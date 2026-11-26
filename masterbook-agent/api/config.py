import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.environ.get("MB_DB", ROOT / "masterbook_agent.db"))
API_SECRET = os.environ.get("MB_API_SECRET", "")
TOKEN_TTL_HOURS = int(os.environ.get("MB_TOKEN_TTL_HOURS", "12"))

STATUSES = ["BELUM_FU", "SUDAH_DIHUBUNGI", "MENUNGGU_RESPONS", "TERTARIK", "WON", "TIDAK_POTENSIAL"]
CLOSED = ("WON", "TIDAK_POTENSIAL")