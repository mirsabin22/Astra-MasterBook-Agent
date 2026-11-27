import json
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from .auth import User, current_user
from .db import get_conn
from .timeutil import today_wita
from .filters import DUE, EFF, HAS_TEL, HAS_WA, build_where 

router = APIRouter(prefix="/api")

FROM = """FROM outlet_scope s
JOIN outlets o ON o.id = s.outlet_id
LEFT JOIN followup_current f ON f.outlet_id = s.outlet_id"""
NOFU = "(f.outlet_id IS NULL OR f.status = 'BELUM_FU')"
STATUSES = ["BELUM_FU", "SUDAH_DIHUBUNGI", "MENUNGGU_RESPONS", "TERTARIK", "WON", "TIDAK_POTENSIAL"]


def scope_sql(user: User):
    if user.role == "management":
        return "1=1", {}
    return "s.sales_owner = :who", {"who": user.sales}


@router.get("/outlets/search")
def search(q: str = Query(min_length=2, max_length=60), limit: int = Query(10, ge=1, le=20),
           user: User = Depends(current_user), c=Depends(get_conn)):
    sc, p = scope_sql(user)
    like = "%" + q.strip().replace("%", "").replace("_", "") + "%"
    rows = c.execute(
        f"SELECT o.id, o.name, o.city, o.dealer_code, s.sales_owner, f.status, f.next_followup "
        f"{FROM} WHERE {sc} AND (o.name LIKE :q OR o.city LIKE :q OR o.dealer_code LIKE :q) "
        f"ORDER BY o.name LIMIT :lim", {**p, "q": like, "lim": limit}).fetchall()
    return {"items": [dict(r) for r in rows]}

ORDERS = {"due": "(f.next_followup IS NULL), f.next_followup, o.name",
          "name": "o.name",
          "updated": "(f.updated_at IS NULL), f.updated_at DESC, o.name"}


@router.get("/outlets/query")
def query(status: List[str] = Query(default=[]), province: List[str] = Query(default=[]),
          city: List[str] = Query(default=[]), q: Optional[str] = Query(None, max_length=60),
          contact: Optional[str] = Query(None, pattern="^(wa|telp|any|none)$"),
          window: Optional[str] = None, due_from: Optional[str] = None, due_to: Optional[str] = None,
          sort: str = Query("due", pattern="^(due|name|updated)$"),
          page: int = Query(1, ge=1), page_size: int = Query(6, ge=1, le=20),
          user: User = Depends(current_user), c=Depends(get_conn)):
    sc, p = scope_sql(user)
    w, fp = build_where(status, province, city, q, contact, window, due_from, due_to)
    cond = " AND ".join([sc] + w)
    params = {**p, **fp}
    total = c.execute(f"SELECT COUNT(*) {FROM} WHERE {cond}", params).fetchone()[0]
    pages = max(1, math.ceil(total / page_size))
    page = min(page, pages)
    rows = c.execute(
        f"SELECT o.id, o.name, o.city, o.province, o.dealer_code, s.sales_owner, "
        f"{EFF} AS status, f.next_followup, {HAS_WA} AS has_wa, {HAS_TEL} AS has_phone "
        f"{FROM} WHERE {cond} ORDER BY {ORDERS[sort]} LIMIT :lim OFFSET :off",
        {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    items = [{**dict(r), "has_wa": bool(r["has_wa"]), "has_phone": bool(r["has_phone"])} for r in rows]
    return {"page": page, "pages": pages, "total": total, "items": items}


@router.get("/regions")
def regions(by: str = Query("province", pattern="^(province|city)$"),
            user: User = Depends(current_user), c=Depends(get_conn)):
    sc, p = scope_sql(user)
    col = "o.province" if by == "province" else "o.city"
    rows = c.execute(f"SELECT COALESCE({col},'(kosong)') AS name, COUNT(*) AS total "
                     f"{FROM} WHERE {sc} GROUP BY name ORDER BY total DESC LIMIT 60", p).fetchall()
    return {"items": [dict(r) for r in rows]}

@router.get("/followups/due")
def due(page: int = Query(1, ge=1), page_size: int = Query(6, ge=1, le=20),
        user: User = Depends(current_user), c=Depends(get_conn)):
    sc, p = scope_sql(user)
    t = today_wita()
    p = {**p, "today": t}
    where = f"{sc} AND ({DUE} OR {NOFU})"
    total = c.execute(f"SELECT COUNT(*) {FROM} WHERE {where}", p).fetchone()[0]
    pages = max(1, math.ceil(total / page_size))
    page = min(page, pages)
    rows = c.execute(
        f"SELECT o.id, o.name, o.city, o.dealer_code, s.sales_owner, f.status, f.next_followup, "
        f"CASE WHEN {DUE} THEN 'due' ELSE 'nofu' END AS kind "
        f"{FROM} WHERE {where} "
        f"ORDER BY (kind = 'nofu'), (f.next_followup IS NULL), f.next_followup, o.id "
        f"LIMIT :lim OFFSET :off", {**p, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    return {"today": t, "page": page, "pages": pages, "total": total,
            "items": [dict(r) for r in rows]}


@router.get("/progress")
def progress(province: List[str] = Query(default=[]), city: List[str] = Query(default=[]),
             group_by: Optional[str] = Query(None, pattern="^(province|city)$"),
             user: User = Depends(current_user), c=Depends(get_conn)):
    sc, p = scope_sql(user)
    w, fp = build_where(province=province, city=city)
    cond = " AND ".join([sc] + w)
    params = {**p, **fp}
    counts = dict(c.execute(
        f"SELECT {EFF}, COUNT(*) {FROM} WHERE {cond} GROUP BY {EFF}", params).fetchall())
    due_n = c.execute(f"SELECT COUNT(*) {FROM} WHERE {cond} AND {DUE}", params).fetchone()[0]
    total = sum(counts.values())
    out = {"date": params["today"], "total": total, "done": total - counts.get("BELUM_FU", 0),
           "due": due_n, "by_status": {s: counts.get(s, 0) for s in STATUSES}}
    if group_by:
        col = "o.province" if group_by == "province" else "o.city"
        rows = c.execute(f"SELECT {col} AS g, {EFF} AS st, COUNT(*) AS n {FROM} "
                         f"WHERE {cond} GROUP BY g, st", params).fetchall()
        groups = {}
        for g, st, n in rows:
            d = groups.setdefault(g or "(kosong)", {"total": 0, "done": 0, "by_status": {}})
            d["total"] += n
            d["by_status"][st] = n
            if st != "BELUM_FU":
                d["done"] += n
        out["by_group"] = dict(sorted(groups.items(), key=lambda kv: -kv[1]["total"])[:30])
    return out


def _outlet_row(c, user, outlet_id):
    sc, p = scope_sql(user)
    row = c.execute(
        f"SELECT o.id, o.name, o.main_dealer_code, o.dealer_code, o.address, o.city, o.province, "
        f"o.services, s.sales_owner {FROM} WHERE o.id = :oid AND {sc}",
        {**p, "oid": outlet_id}).fetchone()
    if not row:
        raise HTTPException(404, detail={"code": "outlet_not_found"})
    return row


@router.get("/outlets/{outlet_id}")
def outlet_detail(outlet_id: str, user: User = Depends(current_user), c=Depends(get_conn)):
    row = _outlet_row(c, user, outlet_id)
    o = dict(row)
    try:
        o["services"] = json.loads(o["services"] or "[]")
    except ValueError:
        o["services"] = []
    f = c.execute("SELECT status, note, next_followup, version, updated_at FROM followup_current "
                  "WHERE outlet_id = ?", (outlet_id,)).fetchone()
    return {"outlet": o, "followup": dict(f) if f else None}


@router.get("/outlets/{outlet_id}/history")
def outlet_history(outlet_id: str, limit: int = Query(20, ge=1, le=100),
                   user: User = Depends(current_user), c=Depends(get_conn)):
    _outlet_row(c, user, outlet_id)
    rows = c.execute(
        "SELECT version, status, note, next_followup, changed_at, actor, source "
        "FROM followup_history WHERE outlet_id = ? ORDER BY version DESC, id DESC LIMIT ?",
        (outlet_id, limit)).fetchall()
    return {"items": [dict(r) for r in rows]}

@router.get("/outlets/{outlet_id}/contact")
def outlet_contact(outlet_id: str, user: User = Depends(current_user), c=Depends(get_conn)):
    row = _outlet_row(c, user, outlet_id)
    r = c.execute("SELECT whatsapp, phone FROM outlets WHERE id = ?", (outlet_id,)).fetchone()
    return {"name": row["name"], "whatsapp": (r["whatsapp"] or "").strip() or None,
            "phone": (r["phone"] or "").strip() or None}