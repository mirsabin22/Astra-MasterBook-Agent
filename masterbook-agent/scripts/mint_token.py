import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.auth import mint_token

actor, sales, role = sys.argv[1], sys.argv[2], sys.argv[3]
print(mint_token(actor, None if sales == "none" else sales, role))