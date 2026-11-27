import sqlite3
from datetime import timedelta

from api.auth import mint_token
from api import config
from api.timeutil import now_wita



def hdr(actor="lenny", sales="Lenny", role="sales"):
    return {"Authorization": f"Bearer {mint_token(actor, sales, role)}"}


def draft(**kw):
    base = {"outlet_id": "O1", "status": "SUDAH_DIHUBUNGI", "note": "sudah telepon",
            "next_followup": "2099-01-01"}
    base.update(kw)
    return base


def test_no_token(client):
    assert client.get("/api/progress").status_code == 401


def test_preview_does_not_write(client):
    r = client.post("/api/followups/preview", json=draft(), headers=hdr())
    assert r.status_code == 200 and r.json()["expected_version"] == 0
    assert client.get("/api/outlets/O1", headers=hdr()).json()["followup"] is None


def test_stale_version_gives_409(client):
    r1 = client.post("/api/followups", json=draft(expected_version=0), headers=hdr())
    assert r1.status_code == 200 and r1.json()["version"] == 1
    r2 = client.post("/api/followups", json=draft(note="lagi", expected_version=1), headers=hdr())
    assert r2.status_code == 200 and r2.json()["version"] == 2
    r3 = client.post("/api/followups", json=draft(note="basi", expected_version=1), headers=hdr())
    assert r3.status_code == 409
    assert r3.json()["detail"]["code"] == "version_conflict"
    assert r3.json()["detail"]["current"]["version"] == 2


def test_create_twice_with_version_zero_gives_409(client):
    client.post("/api/followups", json=draft(expected_version=0), headers=hdr())
    r = client.post("/api/followups", json=draft(expected_version=0), headers=hdr())
    assert r.status_code == 409


def test_other_sales_outlet_is_404(client):
    r = client.post("/api/followups", json=draft(outlet_id="O2", expected_version=0), headers=hdr())
    assert r.status_code == 404


def test_management_cannot_write(client):
    h = hdr(actor="boss", sales=None, role="management")
    r = client.post("/api/followups", json=draft(expected_version=0), headers=h)
    assert r.status_code == 403


def test_history_written_by_trigger(client):
    client.post("/api/followups", json=draft(expected_version=0), headers=hdr())
    client.post("/api/followups", json=draft(note="lagi", expected_version=1), headers=hdr())
    items = client.get("/api/outlets/O1/history", headers=hdr()).json()["items"]
    assert len(items) == 2
    assert items[0]["version"] == 2 and items[0]["actor"] == "lenny" and items[0]["source"] == "telegram"


def test_closed_status_rejects_date(client):
    r = client.post("/api/followups/preview", json=draft(status="WON"), headers=hdr())
    assert r.status_code == 422 and r.json()["detail"]["code"] == "date_on_closed"


def test_sales_sees_only_own_scope(client):
    ids = [i["id"] for i in client.get("/api/outlets/search?q=Outlet", headers=hdr()).json()["items"]]
    assert ids == ["O1"]

def _sql(q):
    c = sqlite3.connect(config.DB_PATH)
    c.execute(q)
    c.commit()
    c.close()


def test_province_is_exact(client):
    _sql("UPDATE outlets SET province='Riau' WHERE id='O1'")
    _sql("INSERT INTO outlets (id,name,main_dealer_code,dealer_code,city,province) "
         "VALUES ('O3','Outlet Tiga','MD1','D3','Batam','Kepulauan Riau')")
    _sql("INSERT INTO outlet_scope (outlet_id,main_dealer_code,sales_owner) VALUES ('O3','MD1','Lenny')")
    r = client.get("/api/outlets/query?province=Riau", headers=hdr()).json()
    assert [i["id"] for i in r["items"]] == ["O1"]


def test_status_filter_includes_won(client):
    client.post("/api/followups", json=draft(status="WON", next_followup=None, expected_version=0), headers=hdr())
    assert client.get("/api/outlets/query?status=WON", headers=hdr()).json()["total"] == 1
    assert client.get("/api/outlets/query?status=BELUM_FU", headers=hdr()).json()["total"] == 0


def test_window_next_week(client):
    d = now_wita().date()
    monday_next = d - timedelta(days=d.weekday()) + timedelta(days=7)
    client.post("/api/followups", json=draft(next_followup=monday_next.isoformat(), expected_version=0), headers=hdr())
    nxt = client.get("/api/outlets/query?window=next_week", headers=hdr()).json()
    assert [i["id"] for i in nxt["items"]] == ["O1"]
    assert client.get("/api/outlets/query?window=this_week", headers=hdr()).json()["total"] == 0


def test_contact_filter_and_endpoint(client):
    _sql("UPDATE outlets SET whatsapp='081234567890' WHERE id='O1'")
    r = client.get("/api/outlets/query?contact=wa", headers=hdr()).json()
    assert [i["id"] for i in r["items"]] == ["O1"] and r["items"][0]["has_wa"] is True
    assert "whatsapp" not in r["items"][0]
    assert client.get("/api/outlets/query?contact=none", headers=hdr()).json()["total"] == 0
    assert client.get("/api/outlets/O1/contact", headers=hdr()).json()["whatsapp"] == "081234567890"
    assert client.get("/api/outlets/O2/contact", headers=hdr()).status_code == 404