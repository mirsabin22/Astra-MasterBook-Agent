from datetime import datetime, timezone
from zoneinfo import ZoneInfo

WITA = ZoneInfo("Asia/Makassar")


def now_wita():
    return datetime.now(WITA)


def today_wita():
    return now_wita().date().isoformat()


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]