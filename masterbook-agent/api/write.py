import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import config
from .auth import User, current_user
from .db import get_conn
from .timeutil import now_ts, today_wita

router = APIRouter(prefix="/api")


class Draft(BaseModel):
    outlet_id: str
    status: str
    note: str = Field(default="", max_length=1000)
    next_followup: Optional[str] = None
    source: str = Field(default="telegram", pattern="^(telegram|api)$")


class Commit(Draft):
    expected_version: int = Field(ge=0)


def _bad(code, msg):
    return HTTPException(422, detail={"code": code, "message": msg})


def normalize(d: Draft):
    if d.status not in config.STATUSES:
        raise _bad("bad_status", f"Status harus salah satu dari {config.STATUSES}")
    note = d.note.strip()
    nxt = d.next_followup or None
    if nxt:
        try:
            parsed = date.fromisoformat(nxt)
        except ValueError:
            raise _bad("bad_date", "Format tanggal harus YYYY-MM-DD")
        if d.status in config.CLOSED:
            raise _bad("date_on_closed", "Status WON atau TIDAK_POTENSIAL tidak boleh punya tanggal FU")
        if parsed.isoformat() < today_wita():
            raise _bad("date_in_past", "Tanggal FU tidak boleh di masa lalu (WITA)")
    return d.status, note, nxt


def require_sales_in_scope(c, user: User, outlet_id: str):
    if user.role != "sales":
        raise HTTPException(403, detail={"code": "read_only_role"})
    ok = c.execute("SELECT 1 FROM outlet_scope WHERE outlet_id = ? AND sales_owner = ?",
                   (outlet_id, user.sales)).fetchone()
    if not ok:
        raise HTTPException(404, detail={"code": "outlet_not_found"})


def current_row(c, outlet_id):
    r = c.execute("SELECT status, note, next_followup, version, updated_at "
                  "FROM followup_current WHERE outlet_id = ?", (outlet_id,)).fetchone()
    return dict(r) if r else None


def conflict(c, outlet_id):
    return HTTPException(409, detail={"code": "version_conflict", "current": current_row(c, outlet_id)})


@router.post("/followups/preview")
def preview(d: Draft, user: User = Depends(current_user), c=Depends(get_conn)):
    require_sales_in_scope(c, user, d.outlet_id)
    status, note, nxt = normalize(d)
    cur = current_row(c, d.outlet_id)
    proposed = {"status": status, "note": note, "next_followup": nxt}
    changes = [k for k, v in proposed.items() if not cur or cur[k] != v]
    return {"outlet_id": d.outlet_id, "current": cur, "proposed": proposed,
            "expected_version": cur["version"] if cur else 0, "changes": changes}


@router.post("/followups")
def commit(d: Commit, user: User = Depends(current_user), c=Depends(get_conn)):
    require_sales_in_scope(c, user, d.outlet_id)
    status, note, nxt = normalize(d)
    now = now_ts()
    try:
        if d.expected_version == 0:
            c.execute(
                "INSERT INTO followup_current (outlet_id, sales_owner, status, note, next_followup, "
                "version, updated_at, created_at, actor, source) VALUES (?,?,?,?,?,1,?,?,?,?)",
                (d.outlet_id, user.sales, status, note, nxt, now, now, user.actor, d.source))
            version = 1
        else:
            res = c.execute(
                "UPDATE followup_current SET status=?, note=?, next_followup=?, version=version+1, "
                "updated_at=?, actor=?, source=? WHERE outlet_id=? AND version=?",
                (status, note, nxt, now, user.actor, d.source, d.outlet_id, d.expected_version))
            if res.rowcount != 1:
                c.rollback()
                raise conflict(c, d.outlet_id)
            version = d.expected_version + 1
        c.commit()
    except sqlite3.IntegrityError:
        c.rollback()
        raise conflict(c, d.outlet_id)
    return {"outlet_id": d.outlet_id, "version": version, "status": status,
            "note": note, "next_followup": nxt, "updated_at": now}