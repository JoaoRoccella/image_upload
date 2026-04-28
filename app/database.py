"""
Módulo de banco de dados — inicializa SQLite e a pasta de uploads.
"""

import sqlite3
from pathlib import Path
from app.logger import server_log


# Caminhos base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data.db"
UPLOADS_DIR = BASE_DIR / "uploads"


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco SQLite com row_factory configurado."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    Cria o banco de dados e a pasta de uploads na primeira execução.
    Idempotente — seguro para chamar múltiplas vezes.
    """
    # Garante que a pasta de uploads existe
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,          -- UUID v4
                created_at  TEXT NOT NULL              -- ISO-8601 timestamp
            );

            CREATE TABLE IF NOT EXISTS images (
                id          TEXT PRIMARY KEY,          -- UUID v4
                session_id  TEXT NOT NULL
                                REFERENCES sessions(id) ON DELETE CASCADE,
                filename    TEXT NOT NULL,             -- nome do arquivo em disco
                filepath    TEXT NOT NULL,             -- caminho relativo a BASE_DIR
                mime_type   TEXT NOT NULL,
                size_bytes  INTEGER NOT NULL,
                created_at  TEXT NOT NULL
            );
            """
        )
    server_log(f"Banco inicializado em: {DB_PATH}")
    server_log(f"Pasta de uploads: {UPLOADS_DIR}")
