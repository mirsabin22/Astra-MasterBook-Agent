import time
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Header, HTTPException

from . import config

ALG = "HS256"


@dataclass
class User:
    actor: str
    sales: Optional[str]
    role: str


def mint_token(actor, sales, role, hours=None):
    hours = hours or config.TOKEN_TTL_HOURS
    payload = {"sub": actor, "sales": sales, "role": role, "exp": int(time.time()) + 3600 * hours}
    return jwt.encode(payload, config.API_SECRET, algorithm=ALG)


def current_user(authorization: str = Header(default="")) -> User:
    if not config.API_SECRET:
        raise HTTPException(500, detail={"code": "server_misconfigured"})
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={"code": "no_token"})
    try:
        p = jwt.decode(authorization[7:], config.API_SECRET, algorithms=[ALG],
                       options={"require": ["exp", "sub", "role"]})
    except jwt.PyJWTError:
        raise HTTPException(401, detail={"code": "bad_token"})
    if p["role"] not in ("sales", "management"):
        raise HTTPException(401, detail={"code": "bad_role"})
    if p["role"] == "sales" and not p.get("sales"):
        raise HTTPException(401, detail={"code": "sales_missing"})
    return User(actor=p["sub"], sales=p.get("sales"), role=p["role"])