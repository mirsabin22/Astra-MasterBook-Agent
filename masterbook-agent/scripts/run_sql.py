import sys
from db import connect

conn = connect()
conn.executescript(open(sys.argv[1], encoding="utf-8").read())
conn.commit()
conn.close()