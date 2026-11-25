from db import connect

QUERIES = {
    "outlets (harus 6466)": "SELECT COUNT(*) FROM outlets",
    "main dealers (harus 24)": "SELECT COUNT(*) FROM main_dealers",
    "outlet per sales": "SELECT sales_owner, COUNT(*) FROM outlet_scope GROUP BY sales_owner",
    "FU tanpa scope (harus kosong)":
        "SELECT f.outlet_id FROM followup_current f "
        "LEFT JOIN outlet_scope s ON s.outlet_id=f.outlet_id WHERE s.outlet_id IS NULL",
    "owner FU beda dengan scope (harus kosong)":
        "SELECT f.outlet_id, f.sales_owner, s.sales_owner FROM followup_current f "
        "JOIN outlet_scope s ON s.outlet_id=f.outlet_id WHERE f.sales_owner<>s.sales_owner",
    "versi history tidak cocok (harus kosong)":
        "SELECT c.id FROM followup_current c LEFT JOIN "
        "(SELECT current_id, MAX(version) mv FROM followup_history GROUP BY current_id) h "
        "ON h.current_id=c.id WHERE h.mv IS NULL OR h.mv<>c.version",
}

conn = connect()
for label, sql in QUERIES.items():
    print(label, "=>", conn.execute(sql).fetchall())