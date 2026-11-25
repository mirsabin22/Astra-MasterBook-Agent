import json
import math
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB = ROOT / "masterbook_agent.db"
STATE = ROOT / ".mb_state.json"
PAGE_SIZE = 6
VALID = {"Lenny", "Kus", "Ardi", "Indra", "Widya"}
STATUSES = ["BELUM_FU", "SUDAH_DIHUBUNGI", "MENUNGGU_RESPONS", "TERTARIK", "WON", "TIDAK_POTENSIAL"]

FROM = """FROM outlet_scope s
JOIN outlets o ON o.id = s.outlet_id
LEFT JOIN followup_current f ON f.outlet_id = s.outlet_id"""
DUE = ("(f.next_followup IS NOT NULL AND f.next_followup <= :today "
       "AND f.status NOT IN ('WON','TIDAK_POTENSIAL'))")
NOFU = "(f.outlet_id IS NULL OR f.status = 'BELUM_FU')"
HELP = """Perintah yang tersedia:
/list : daftar outlet yang perlu di follow up
/next : halaman berikutnya
/progress : ringkasan progres follow up
/menu : tampilkan bantuan ini"""

def conn():
    return sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)


def today():
    return datetime.now(ZoneInfo("Asia/Makassar")).date().isoformat()


def list_page(who, page):
    t = today()
    p = {"who": who, "today": t}
    where = f"s.sales_owner = :who AND ({DUE} OR {NOFU})"
    c = conn()
    total = c.execute(f"SELECT COUNT(*) {FROM} WHERE {where}", p).fetchone()[0]
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(page, 1), pages)
    rows = c.execute(
        f"SELECT o.name, o.city, o.dealer_code, f.next_followup, "
        f"CASE WHEN {DUE} THEN 0 ELSE 1 END AS pr "
        f"{FROM} WHERE {where} "
        f"ORDER BY pr, (f.next_followup IS NULL), f.next_followup, o.id "
        f"LIMIT :lim OFFSET :off",
        {**p, "lim": PAGE_SIZE, "off": (page - 1) * PAGE_SIZE}).fetchall()
    STATE.write_text(json.dumps({"page": page, "pages": pages}))
    lines = [f"Daftar kontak {who}: halaman {page} dari {pages}, total {total}",
             f"Filter: FU jatuh tempo dulu, lalu belum FU. Tanggal {t} WITA"]
    for i, (name, city, dealer, nxt, pr) in enumerate(rows, 1 + (page - 1) * PAGE_SIZE):
        tag = f"jatuh tempo {nxt}" if pr == 0 else "belum FU"
        lines.append(f"{i}. {name}, {city or '-'}, dealer {dealer or '-'} ({tag})")
    if page < pages:
        lines.append("Ketik /next untuk halaman berikutnya")
    return "\n".join(lines)


def progress(who):
    t = today()
    c = conn()
    counts = dict(c.execute(
        "SELECT COALESCE(f.status,'BELUM_FU'), COUNT(*) FROM outlet_scope s "
        "LEFT JOIN followup_current f ON f.outlet_id = s.outlet_id "
        "WHERE s.sales_owner = :who GROUP BY COALESCE(f.status,'BELUM_FU')",
        {"who": who}).fetchall())
    due = c.execute(
        f"SELECT COUNT(*) FROM outlet_scope s JOIN followup_current f "
        f"ON f.outlet_id = s.outlet_id WHERE s.sales_owner = :who AND {DUE}",
        {"who": who, "today": t}).fetchone()[0]
    total = sum(counts.values())
    done = total - counts.get("BELUM_FU", 0)
    lines = [f"Progres {who} per {t} WITA", f"Sudah diproses: {done} dari {total}",
             f"FU jatuh tempo: {due}"]
    lines += [f"{s}: {counts.get(s, 0)}" for s in STATUSES]
    return "\n".join(lines)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "menu"
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if cmd not in ("list", "next", "progress"):
        print(HELP)
        return
    who = os.environ.get("MB_IDENTITY", "")
    if who not in VALID:
        print("MB_IDENTITY belum diisi dengan nama sales yang valid")
        return
    if cmd == "list":
        print(list_page(who, int(arg) if arg.isdigit() else 1))
    elif cmd == "next":
        page = json.loads(STATE.read_text())["page"] + 1 if STATE.exists() else 1
        print(list_page(who, page))
    else:
        print(progress(who))


main()