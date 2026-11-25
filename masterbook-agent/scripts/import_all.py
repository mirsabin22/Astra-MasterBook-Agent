import csv
import json
import sys
from db import connect

def nul(x):
    return None if x in ("NULL", "") else x

def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)

def main(data_path, current_csv, history_csv, sample_scope_csv=None):
    with open(data_path, encoding="utf-8") as f:
        d = json.load(f)
    print({k: (v if not isinstance(v, (list, dict)) else f"{type(v).__name__}[{len(v)}]")
           for k, v in d.items()})

    owner = {code: s for s, codes in d["salesAssignments"].items() for code in codes}
    mds, outlets = d["mainDealers"], d["outlets"]
    no_owner = [o["id"] for o in outlets if o["mainDealerCode"] not in owner]
    print("outlets:", len(outlets), "| main dealers:", len(mds), "| tanpa owner:", len(no_owner))

    conn = connect()
    cur = conn.cursor()
    for t in ("followup_history", "followup_current", "outlet_scope", "outlets", "main_dealers"):
        cur.execute(f"DELETE FROM {t}")

    cur.executemany(
        "INSERT INTO main_dealers (code,name,territory,provinces) VALUES (?,?,?,?)",
        [(m["code"], m.get("name") or "", m.get("territory"),
          json.dumps(m.get("provinces") or [], ensure_ascii=False)) for m in mds])
    cur.executemany(
        "INSERT INTO outlets (id,name,main_dealer_code,dealer_code,address,city,province,"
        "services,whatsapp,phone,company_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(o["id"], o.get("name") or "", o["mainDealerCode"], o.get("dealerCode"),
          o.get("address"), o.get("city"), o.get("province"),
          json.dumps(o.get("services") or []), o.get("whatsapp"), o.get("phone"),
          None if o.get("companyId") is None else str(o["companyId"])) for o in outlets])
    cur.executemany(
        "INSERT INTO outlet_scope (outlet_id,main_dealer_code,sales_owner) VALUES (?,?,?)",
        [(o["id"], o["mainDealerCode"], owner[o["mainDealerCode"]])
         for o in outlets if o["mainDealerCode"] in owner])

    cur.executemany(
        "INSERT INTO followup_current (id,outlet_id,sales_owner,status,note,next_followup,"
        "version,updated_at,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        [(r["id"], r["outlet_id"], r["sales_owner"], r["status"], r["note"],
          nul(r["next_followup"]), r["version"], r["updated_at"], r["created_at"])
         for r in read(current_csv)])
    cur.executemany(
        "INSERT INTO followup_history (id,current_id,outlet_id,sales_owner,status,note,"
        "next_followup,version,changed_at) VALUES (?,?,?,?,?,?,?,?,?)",
        [(r["id"], r["current_id"], r["outlet_id"], r["sales_owner"], r["status"], r["note"],
          nul(r["next_followup"]), r["version"], r["changed_at"])
         for r in read(history_csv)])
    conn.commit()

    for t in ("outlets", "main_dealers", "outlet_scope", "followup_current", "followup_history"):
        print(t, cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    conn.close()

    if sample_scope_csv:
        ids = {o["id"] for o in outlets}
        bad = [r for r in read(sample_scope_csv)
               if r["outlet_id"] not in ids or owner.get(r["main_dealer_code"]) != r["sales_owner"]]
        print("selisih dengan sample outlet_scope.csv:", bad)

if __name__ == "__main__":
    main(*sys.argv[1:])