from datetime import datetime
from zoneinfo import ZoneInfo

WITA = ZoneInfo("Asia/Makassar")


def now_wita():
    return datetime.now(WITA)


def today_wita():
    return now_wita().date().isoformat()


def now_ts():
    return now_wita().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]