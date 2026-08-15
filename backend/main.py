"""
Backend FastAPI de SOLO LECTURA + servidor del frontend.

Sirve el contenido que el pipeline nocturno dejo en datos/contenido_<fecha>.json.
NUNCA llama al LLM ni a nba_api al atender una peticion: solo lee ficheros ya
generados. Toda la inteligencia esta en el pipeline; esta capa es un lector.

Dos responsabilidades:
  1. API JSON bajo el prefijo /api (para el frontend y para consumo directo).
  2. Servir el frontend ya construido (frontend/dist) si existe, para desplegar
     todo en un unico contenedor (Hugging Face Spaces). En desarrollo ese dist no
     existe y se usa el dev server de Vite, que proxya /api aqui.

El toggle de spoilers (?spoilers=true|false) decide QUE version se sirve:
  - con resultados: analisis completo con nombres + pieza contrafactual.
  - sin spoilers:  analisis cualitativo y SIN contrafactual (no puede existir sin
    revelar antes el resultado real).

Las respuestas del quiz viven en /api/jornada/{fecha}/respuestas (revelado opt-in)
para que cargar el contenido en modo sin-spoilers nunca desvele resultados.

Arranque local:  uvicorn backend.main:app --reload   (desde mvp_nba_web/)
Scheduler embebido: exporta HABILITAR_SCHEDULER=1 para disparar el pipeline cada
noche desde el propio proceso del servidor (util en el contenedor).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_RAIZ = Path(__file__).resolve().parents[1]
_DIR_DATOS = _RAIZ / "datos"
_DIR_DIST = _RAIZ / "frontend" / "dist"

app = FastAPI(
    title="M.V.P. — Analista NBA",
    description="API de solo lectura del contenido generado por el pipeline nocturno.",
    version="0.1.0",
)

# dejo CORS abierto en desarrollo (Vite en :5173). en un unico contenedor no hace
# falta, pero no molesta; restringir con origenes concretos en produccion si se separa.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# acceso a datos
# ---------------------------------------------------------------------------

def _cargar_contenido(fecha: str) -> dict:
    # prefiero la BD SQLite; si no esta, caigo al JSON en disco (compatibilidad).
    try:
        from agente.herramientas import persistencia
        desde_db = persistencia.cargar_contenido(fecha)
        if desde_db is not None:
            return desde_db
    except Exception:
        pass  # si la BD falla, sigo con el JSON
    ruta = _DIR_DATOS / f"contenido_{fecha}.json"
    if not ruta.exists():
        raise HTTPException(status_code=404,
                            detail=f"No hay contenido generado para la jornada {fecha}")
    with ruta.open(encoding="utf-8") as fh:
        return json.load(fh)


def _quiz_sin_respuestas(quiz: dict) -> dict:
    return {
        "intro": quiz.get("intro", ""),
        "preguntas": [
            {"pregunta": p["pregunta"], "opciones": p["opciones"]}
            for p in quiz.get("preguntas", [])
        ],
    }


def _moldear(contenido: dict, spoilers: bool) -> dict:
    analisis = contenido.get("analisis", {})
    return {
        "fecha": contenido.get("fecha"),
        "modo": "con_resultados" if spoilers else "sin_spoilers",
        "quiz": _quiz_sin_respuestas(contenido.get("quiz", {})),
        # los marcadores son spoilers: solo en la version con resultados.
        "resultados": contenido.get("resultados") if spoilers else None,
        "analisis": analisis.get("con_resultados" if spoilers else "sin_spoilers", ""),
        "contrafactual": contenido.get("contrafactual") if spoilers else None,
    }


# ---------------------------------------------------------------------------
# endpoints de la API (prefijo /api)
# ---------------------------------------------------------------------------

@api.get("/salud")
def salud():
    return {"estado": "ok"}


@api.get("/jornadas")
def listar_jornadas() -> list[str]:
    """Fechas con contenido generado, mas recientes primero (union de BD + JSON)."""
    fechas = {p.stem.replace("contenido_", "")
              for p in _DIR_DATOS.glob("contenido_*.json")}
    try:
        from agente.herramientas import persistencia
        fechas.update(persistencia.listar_jornadas())
    except Exception:
        pass
    return sorted(fechas, reverse=True)


@api.get("/jornada/{fecha}")
def obtener_jornada(
    fecha: str,
    spoilers: bool = Query(True, description="true = con resultados; false = sin spoilers"),
):
    """Contenido de una jornada en la version elegida (sin desvelar el quiz)."""
    return _moldear(_cargar_contenido(fecha), spoilers)


@api.get("/jornada/{fecha}/respuestas")
def respuestas_quiz(fecha: str):
    """Respuestas del quiz (revelado opt-in), con el indice correcto para puntuar."""
    preguntas = _cargar_contenido(fecha).get("quiz", {}).get("preguntas", [])
    return {
        "fecha": fecha,
        "respuestas": [
            {"pregunta": p["pregunta"], "correcta": p["correcta"],
             "correcta_idx": p["correcta_idx"], "explicacion": p["explicacion"]}
            for p in preguntas
        ],
    }


app.include_router(api)


# ---------------------------------------------------------------------------
# frontend estatico (produccion / contenedor)
# ---------------------------------------------------------------------------

if _DIR_DIST.exists():
    # sirvo el build de Vite en la raiz. las rutas /api ya estan registradas antes,
    # asi que tienen prioridad; el resto cae al frontend (SPA de una sola pagina).
    app.mount("/", StaticFiles(directory=str(_DIR_DIST), html=True), name="frontend")
else:
    @app.get("/")
    def raiz_dev():
        return {"servicio": "M.V.P. — Analista NBA",
                "nota": "Frontend no construido; en desarrollo usa Vite (:5173).",
                "api": ["/api/jornadas", "/api/jornada/{fecha}?spoilers=true|false",
                        "/api/jornada/{fecha}/respuestas"]}


# ---------------------------------------------------------------------------
# scheduler embebido opcional (para el contenedor de un solo proceso)
# ---------------------------------------------------------------------------

_scheduler = None


@app.on_event("startup")
def _quiza_arrancar_scheduler():
    global _scheduler
    if os.environ.get("HABILITAR_SCHEDULER", "").lower() in ("1", "true", "si"):
        from backend.scheduler import crear_scheduler_background
        _scheduler = crear_scheduler_background()
