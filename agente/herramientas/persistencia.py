"""
Persistencia en SQLite (la base de datos prototipo del proyecto).

Guardo dos cosas por cada jornada que procesa el pipeline:
  1. Las lineas de box score de cada jugador (tabla `lineas`), que dejan el
     historico partido a partido en local. De momento las rachas las calculo con
     el gamelog de nba_api, pero tener esto persistido abre la puerta a rachas de
     equipo o de liga (cruzando varias noches) sin depender de la API.
  2. El contenido ya redactado de la jornada (tabla `contenido`), que es lo que
     sirve el backend.

Uso sqlite3 de la libreria estandar; el fichero vive en datos/mvp.db. Si el
historico crece, el plan es migrar a PostgreSQL (Supabase/Neon) sin cambiar esta
interfaz.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .modelos import PaqueteJornada

_DB = Path(__file__).resolve().parents[2] / "datos" / "mvp.db"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS lineas (
    game_id     TEXT NOT NULL,
    fecha       TEXT NOT NULL,
    player_id   INTEGER NOT NULL,
    nombre      TEXT NOT NULL,
    equipo_abbr TEXT NOT NULL,
    pts INTEGER, reb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER,
    fg3m INTEGER, minutos REAL,
    PRIMARY KEY (game_id, player_id)
);
CREATE INDEX IF NOT EXISTS idx_lineas_jugador ON lineas (player_id, fecha);
CREATE INDEX IF NOT EXISTS idx_lineas_fecha ON lineas (fecha);

CREATE TABLE IF NOT EXISTS contenido (
    fecha       TEXT PRIMARY KEY,
    json        TEXT NOT NULL,
    generado_en TEXT NOT NULL
);
"""


def conectar(db_path: Path = _DB) -> sqlite3.Connection:
    """Abro (creando el fichero y el esquema si hace falta) la BD y la devuelvo."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_ESQUEMA)
    return conn


# ---------------------------------------------------------------------------
# escritura
# ---------------------------------------------------------------------------

def guardar_jornada(paquete: PaqueteJornada, conn: Optional[sqlite3.Connection] = None) -> int:
    """Persisto las lineas de todos los jugadores de la jornada. Devuelvo cuantas."""
    propio = conn is None
    conn = conn or conectar()
    filas = [
        (p.game_id, paquete.fecha, l.player_id, l.nombre, l.equipo_abbr,
         l.pts, l.reb, l.ast, l.stl, l.blk, l.fg3m, l.minutos)
        for p in paquete.partidos for l in p.jugadores
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO lineas "
        "(game_id, fecha, player_id, nombre, equipo_abbr, pts, reb, ast, stl, blk, "
        "fg3m, minutos) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        filas,
    )
    conn.commit()
    if propio:
        conn.close()
    return len(filas)


def guardar_contenido(fecha: str, contenido: dict,
                      conn: Optional[sqlite3.Connection] = None) -> None:
    """Persisto (o actualizo) el contenido redactado de una jornada."""
    propio = conn is None
    conn = conn or conectar()
    conn.execute(
        "INSERT OR REPLACE INTO contenido (fecha, json, generado_en) VALUES (?,?,?)",
        (fecha, json.dumps(contenido, ensure_ascii=False), datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    if propio:
        conn.close()


# ---------------------------------------------------------------------------
# lectura (la usa el backend)
# ---------------------------------------------------------------------------

def cargar_contenido(fecha: str, conn: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    """Devuelvo el contenido de una jornada, o None si no esta en la BD."""
    propio = conn is None
    conn = conn or conectar()
    fila = conn.execute("SELECT json FROM contenido WHERE fecha = ?", (fecha,)).fetchone()
    if propio:
        conn.close()
    return json.loads(fila["json"]) if fila else None


def listar_jornadas(conn: Optional[sqlite3.Connection] = None) -> list[str]:
    """Fechas con contenido en la BD, mas recientes primero."""
    propio = conn is None
    conn = conn or conectar()
    filas = conn.execute("SELECT fecha FROM contenido ORDER BY fecha DESC").fetchall()
    if propio:
        conn.close()
    return [f["fecha"] for f in filas]


def historial_jugador(player_id: int, conn: Optional[sqlite3.Connection] = None) -> list[dict]:
    """Todas las lineas persistidas de un jugador, por fecha (para futuras rachas
    cruzando noches sin depender de nba_api)."""
    propio = conn is None
    conn = conn or conectar()
    filas = conn.execute(
        "SELECT fecha, pts, reb, ast, fg3m FROM lineas WHERE player_id = ? ORDER BY fecha",
        (player_id,),
    ).fetchall()
    if propio:
        conn.close()
    return [dict(f) for f in filas]
