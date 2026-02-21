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
DATA_DIR = Path(os.environ.get("LCAI_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data")))
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

# Dev CORS (UI runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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

@app.get("/api/auth/me")
def me(user: str = Depends(_require_user)) -> dict:
    return {"username": user}

@app.get("/api/cases", response_model=List[CaseOut])
def list_cases(user: str = Depends(_require_user)) -> List[CaseOut]:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cases WHERE archived_at IS NULL ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    out: List[CaseOut] = []
    for r in rows:
        out.append(CaseOut(
            id=r["id"],
            title=r["title"],
            jurisdiction=r["jurisdiction"],
            tags=json.loads(r["tags_json"] or "[]"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            archived_at=r["archived_at"],
        ))
    return out

@app.post("/api/cases", response_model=CaseOut)
def create_case(inp: CaseCreateIn, user: str = Depends(_require_user)) -> CaseOut:
    cid = _new_id("case")
    now = int(time.time())
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cases(id, title, jurisdiction, tags_json, created_at, updated_at, archived_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
        (cid, inp.title, inp.jurisdiction, json.dumps(inp.tags), now, now),
    )
    conn.commit()
    conn.close()
    _write_journal(cid, user, "case.created", {"title": inp.title, "jurisdiction": inp.jurisdiction, "tags": inp.tags})
    return CaseOut(id=cid, title=inp.title, jurisdiction=inp.jurisdiction, tags=inp.tags, created_at=now, updated_at=now, archived_at=None)

@app.post("/api/cases/{case_id}/archive")
def archive_case(case_id: str, user: str = Depends(_require_user)) -> dict:
    now = int(time.time())
    conn = _db()
    cur = conn.cursor()
    cur.execute("UPDATE cases SET archived_at = ?, updated_at = ? WHERE id = ?", (now, now, case_id))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")
    conn.commit()
    conn.close()
    _write_journal(case_id, user, "case.archived", {"archived_at": now})
    return {"ok": True}

@app.get("/api/cases/{case_id}/documents", response_model=List[DocumentOut])
def list_documents(case_id: str, user: str = Depends(_require_user)) -> List[DocumentOut]:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE case_id = ? ORDER BY imported_at DESC", (case_id,))
    rows = cur.fetchall()
    conn.close()
    return [DocumentOut(
        id=r["id"],
        case_id=r["case_id"],
        filename=r["filename"],
        mime=r["mime"],
        sha256=r["sha256"],
        imported_at=r["imported_at"],
    ) for r in rows]

@app.post("/api/cases/{case_id}/documents/upload", response_model=DocumentOut)
async def upload_document(case_id: str, file: UploadFile = File(...), user: str = Depends(_require_user)) -> DocumentOut:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    raw = await file.read()
    sha = hashlib.sha256(raw).hexdigest()
    doc_id = _new_id("doc")
    now = int(time.time())

    # store
    case_dir = STORAGE_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    safe_name = file.filename.replace("\\", "_").replace("/", "_")
    relpath = f"{case_id}/{doc_id}__{safe_name}"
    abspath = STORAGE_DIR / relpath
    abspath.write_bytes(raw)

    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documents(id, case_id, filename, mime, sha256, imported_at, storage_relpath) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_id, case_id, safe_name, file.content_type or "application/octet-stream", sha, now, relpath),
    )
    conn.commit()
    conn.close()

    _write_journal(case_id, user, "document.uploaded", {"document_id": doc_id, "filename": safe_name, "sha256": sha})
    return DocumentOut(id=doc_id, case_id=case_id, filename=safe_name, mime=file.content_type or "application/octet-stream", sha256=sha, imported_at=now)

@app.get("/api/cases/{case_id}/journal", response_model=List[JournalOut])
def list_journal(case_id: str, user: str = Depends(_require_user)) -> List[JournalOut]:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM journal_entries WHERE case_id = ? ORDER BY ts DESC LIMIT 200", (case_id,))
    rows = cur.fetchall()
    conn.close()
    out: List[JournalOut] = []
    for r in rows:
        out.append(JournalOut(
            id=r["id"],
            case_id=r["case_id"],
            ts=r["ts"],
            actor=r["actor"],
            action_type=r["action_type"],
            payload=json.loads(r["payload_json"] or "{}"),
            payload_hash=r["payload_hash"],
        ))
    return out

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("LCAI_PORT", "8787")), reload=(os.environ.get("LCAI_RELOAD","0")=="1"))
