from datetime import date, timedelta

from fastapi import HTTPException

from . import config
from .timeutil import today_wita

EFF = "COALESCE(f.status,'BELUM_FU')"
DUE = ("(f.next_followup IS NOT NULL AND f.next_followup <= :today "
       "AND f.status NOT IN ('WON','TIDAK_POTENSIAL'))")
HAS_WA = "(COALESCE(TRIM(o.whatsapp),'') <> '')"
HAS_TEL = "(COALESCE(TRIM(o.phone),'') <> '')"
WINDOWS = ("due", "today", "this_week", "next_week", "this_month")


def _bad(code, msg):
    return HTTPException(422, detail={"code": code, "message": msg})


def _in(col, values, prefix, params):
    keys = []
    for i, v in enumerate(values):
        params[f"{prefix}{i}"] = v
        keys.append(f":{prefix}{i}")
    return f"{col} IN ({','.join(keys)})"


def _range(window, today):
    start = today - timedelta(days=today.weekday())
    if window == "today":
        return today, today
    if window == "this_week":
        return start, start + timedelta(days=6)
    if window == "next_week":
        return start + timedelta(days=7), start + timedelta(days=13)
    first = today.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return first, last


def build_where(status=None, province=None, city=None, q=None, contact=None,
                window=None, due_from=None, due_to=None):
    where, p = [], {"today": today_wita()}
    if status:
        bad = [s for s in status if s not in config.STATUSES]
        if bad:
            raise _bad("bad_status", f"Status tidak dikenal: {bad}")
        where.append(_in(EFF, status, "st", p))
    if province:
        where.append(_in("LOWER(o.province)", [x.strip().lower() for x in province], "pv", p))
    if city:
        ors = []
        for i, x in enumerate(city):
            p[f"ct{i}"] = "%" + x.strip().lower().replace("%", "").replace("_", "") + "%"
            ors.append(f"LOWER(o.city) LIKE :ct{i}")
        where.append("(" + " OR ".join(ors) + ")")
    if q:
        p["q"] = "%" + q.strip().replace("%", "").replace("_", "") + "%"
        where.append("(o.name LIKE :q OR o.city LIKE :q OR o.dealer_code LIKE :q)")
    if contact:
        where.append({"wa": HAS_WA, "telp": HAS_TEL, "any": f"({HAS_WA} OR {HAS_TEL})",
                      "none": f"(NOT {HAS_WA} AND NOT {HAS_TEL})"}[contact])
    if window:
        if window not in WINDOWS:
            raise _bad("bad_window", f"Window harus salah satu dari {WINDOWS}")
        if window == "due":
            where.append(DUE)
        else:
            a, b = _range(window, date.fromisoformat(p["today"]))
            p["w_from"], p["w_to"] = a.isoformat(), b.isoformat()
            where.append("(f.next_followup BETWEEN :w_from AND :w_to "
                         "AND f.status NOT IN ('WON','TIDAK_POTENSIAL'))")
    for key, op, v in (("due_from", ">=", due_from), ("due_to", "<=", due_to)):
        if v:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise _bad("bad_date", "Format tanggal harus YYYY-MM-DD")
            where.append(f"f.next_followup {op} :{key}")
            p[key] = v
    return where, p