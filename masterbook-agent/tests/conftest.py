import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    from api import config
    db = tmp_path / "t.db"
    c = sqlite3.connect(db)
    c.executescript((ROOT / "db/01_schema.sql").read_text(encoding="utf-8"))
    c.executescript((ROOT / "db/02_migration.sql").read_text(encoding="utf-8"))
    for code in ("MD1", "MD2"):
        c.execute("INSERT INTO main_dealers (code,name,territory,provinces) VALUES (?,?,?,?)",
                  (code, code, "T", "[]"))
    c.execute("INSERT INTO outlets (id,name,main_dealer_code,dealer_code,city) VALUES ('O1','Outlet Satu','MD1','D1','Makassar')")
    c.execute("INSERT INTO outlets (id,name,main_dealer_code,dealer_code,city) VALUES ('O2','Outlet Dua','MD2','D2','Gowa')")
    c.execute("INSERT INTO outlet_scope (outlet_id,main_dealer_code,sales_owner) VALUES ('O1','MD1','Lenny')")
    c.execute("INSERT INTO outlet_scope (outlet_id,main_dealer_code,sales_owner) VALUES ('O2','MD2','Kus')")
    c.commit()
    c.close()
    monkeypatch.setattr(config, "DB_PATH", db)
    monkeypatch.setattr(config, "API_SECRET", "test-secret")
    from api.main import app
    return TestClient(app)