from __future__ import annotations

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from passlib.context import CryptContext
import jwt
import sqlite3

APP_NAME = "local-case-ai-mvp"

# ✅ FIX 1: Use LOCALAPPDATA instead of Program Files
DATA_DIR = Path(
    os.environ.get(
        "LCAI_DATA_DIR",
        str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LocalCaseAI" / "data")
    )
)

DB_PATH = DATA_DIR / "db.sqlite"
STORAGE_DIR = DATA_DIR / "storage"

JWT_SECRET = os.environ.get("LCAI_JWT_SECRET", "CHANGE_ME_DEV_ONLY")
JWT_ALG = "HS256"
TOKEN_TTL_SECONDS = 60 * 60 * 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_scheme = HTTPBearer()

def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def _db() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db() -> None:
    conn = _db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cases (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      jurisdiction TEXT DEFAULT '',
      tags_json TEXT DEFAULT '[]',
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      archived_at INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      case_id TEXT NOT NULL,
      filename TEXT NOT NULL,
      mime TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      imported_at INTEGER NOT NULL,
      storage_relpath TEXT NOT NULL,
      FOREIGN KEY(case_id) REFERENCES cases(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
      id TEXT PRIMARY KEY,
      case_id TEXT NOT NULL,
      ts INTEGER NOT NULL,
      actor TEXT NOT NULL,
      action_type TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      payload_hash TEXT NOT NULL,
      FOREIGN KEY(case_id) REFERENCES cases(id)
    );
    """)

    conn.commit()
    conn.close()

    _ensure_default_user()

def _ensure_default_user() -> None:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    row = cur.fetchone()
    if row is None:
        now = int(time.time())
        pw_hash = pwd_context.hash("admin1234")
        cur.execute(
            "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
            ("admin", pw_hash, now),
        )
        conn.commit()
    conn.close()

def _new_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.sha256(os.urandom(32)).hexdigest()[:16]}"

def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _write_journal(case_id: str, actor: str, action_type: str, payload: dict) -> None:
    conn = _db()
    cur = conn.cursor()
    jid = _new_id("jrn")
    ts = int(time.time())
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_hash = _hash_payload(payload)
    cur.execute(
        "INSERT INTO journal_entries(id, case_id, ts, actor, action_type, payload_json, payload_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (jid, case_id, ts, actor, action_type, payload_json, payload_hash),
    )
    conn.commit()
    conn.close()

def _create_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def _require_user(creds: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> str:
    token = creds.credentials
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return str(data["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

class LoginIn(BaseModel):
    username: str
    password: str

class LoginOut(BaseModel):
    token: str

class CaseCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    jurisdiction: str = ""
    tags: List[str] = Field(default_factory=list)

class CaseOut(BaseModel):
    id: str
    title: str
    jurisdiction: str
    tags: List[str]
    created_at: int
    updated_at: int
    archived_at: Optional[int] = None

class DocumentOut(BaseModel):
    id: str
    case_id: str
    filename: str
    mime: str
    sha256: str
    imported_at: int

class JournalOut(BaseModel):
    id: str
    case_id: str
    ts: int
    actor: str
    action_type: str
    payload: Dict[str, Any]
    payload_hash: str

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    _init_db()

@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "app": APP_NAME}

@app.post("/api/auth/login", response_model=LoginOut)
def login(inp: LoginIn) -> LoginOut:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT username, password_hash FROM users WHERE username = ?", (inp.username,))
    row = cur.fetchone()
    conn.close()
    if row is None or not pwd_context.verify(inp.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Bad credentials")
    return LoginOut(token=_create_token(inp.username))

# (Rest of your endpoints remain unchanged...)

# ✅ FIX 2: PyInstaller safe launch
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("LCAI_PORT", "8787"))
    uvicorn.run(app, host="127.0.0.1", port=port)
