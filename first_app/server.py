"""
TNR 流浪动物管理系统 - 后端服务
FastAPI + SQLite 实现
"""
import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Try FastAPI first, fall back to simple HTTP server
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    import uvicorn

    app = FastAPI(title="TNR 流浪动物管理系统")
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    DB_PATH = Path(__file__).parent / "tnr.db"

    def get_db():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        conn = get_db()
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS animals (
                id TEXT PRIMARY KEY,
                community TEXT,
                status TEXT DEFAULT 'in_transit',
                photo TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS materials (
                id TEXT PRIMARY KEY,
                type TEXT,
                quantity INTEGER DEFAULT 0,
                unit TEXT,
                batch TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS treatments (
                id TEXT PRIMARY KEY,
                animal_id TEXT,
                hospital TEXT,
                surgery INTEGER DEFAULT 0,
                vaccine INTEGER DEFAULT 0,
                deworm INTEGER DEFAULT 0,
                chip TEXT,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS transfers (
                id TEXT PRIMARY KEY,
                animal_ids TEXT,
                from_location TEXT,
                to_hospital TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS adoptions (
                id TEXT PRIMARY KEY,
                applicant TEXT,
                phone TEXT,
                animal_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        conn.commit()
        conn.close()

    init_db()

    @app.get("/api/health")
    def health():
        return {"status": "ok", "time": datetime.now().isoformat()}

    @app.get("/api/animals")
    def list_animals(status: str = None):
        conn = get_db()
        if status:
            rows = conn.execute("SELECT * FROM animals WHERE status = ?", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM animals").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @app.post("/api/animals")
    def create_animal(data: dict):
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO animals (id, community, status) VALUES (?, ?, ?)",
                  (data.get("id"), data.get("community", ""), data.get("status", "in_transit")))
        conn.commit()
        conn.close()
        return {"message": "created", "id": data.get("id")}

    # Serve static files
    static_dir = Path(__file__).parent
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    CLIENT = "uvicorn"

except ImportError:
    # Fallback: simple HTTP server
    import http.server
    import socketserver
    
    PORT = 8889
    
    class TNRHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
        
        def log_message(self, format, *args):
            print(f"[TNR] {datetime.now().strftime('%H:%M:%S')} {args[0]} {args[1]} {args[2]}")
    
    CLIENT = "simple"

if __name__ == "__main__":
    print("=" * 50)
    print("  TNR 流浪动物管理系统")
    print("  访问地址: http://localhost:8889")
    print("=" * 50)
    
    if CLIENT == "uvicorn":
        uvicorn.run(app, host="0.0.0.0", port=8889, log_level="info")
    else:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), TNRHandler) as httpd:
            httpd.serve_forever()
