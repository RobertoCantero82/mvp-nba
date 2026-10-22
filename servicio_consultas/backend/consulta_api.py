"""sirvo consultas en memoria, sin historial, cookies ni registros de acceso."""
from __future__ import annotations
import json
import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from .consultas import responder, ConsultaNoDisponible, cargar_copia

class Pregunta(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    pregunta:str=Field(min_length=3,max_length=800)

app=FastAPI(title="Pregunta a M.V.P.",docs_url=None,redoc_url=None,openapi_url=None)
origenes=[s.strip() for s in os.environ.get("ORIGENES_PERMITIDOS",
    "https://robertocantero-mvp-nba.static.hf.space,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173").split(',') if s.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origenes,allow_methods=["POST","GET"],allow_headers=["Content-Type"],allow_credentials=False)
_plazas=threading.BoundedSemaphore(2)

@app.middleware("http")
async def sin_cache(request, call_next):
    resp=await call_next(request)
    resp.headers["Cache-Control"]="no-store, max-age=0"
    resp.headers["Pragma"]="no-cache"
    resp.headers["X-Content-Type-Options"]="nosniff"
    return resp

@app.get("/api/salud")
def salud():
    try:
        copia=cargar_copia()
        datos={"datos_disponibles":True,"datos_actualizados":copia["actualizado"],"corte":copia["corte"]}
    except ConsultaNoDisponible:
        datos={"datos_disponibles":False}
    return {"estado":"ok","almacenamiento_consultas":False,"configurado":bool(os.environ.get("GROQ_API_KEY")),"modo_datos":"copia_diaria","revision":os.environ.get("RENDER_GIT_COMMIT","local"),**datos}

@app.post("/api/preguntar")
async def preguntar(request:Request):
    if not request.headers.get('content-type','').lower().startswith('application/json'):
        return JSONResponse({"detail":"Envía la pregunta como JSON."},status_code=415)
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>4096:
            return JSONResponse({"detail":"La pregunta es demasiado larga."},status_code=413)
    try:
        pregunta=Pregunta.model_validate_json(bytes(raw)).pregunta
    except (ValidationError,ValueError):
        return JSONResponse({"detail":"Escribe una pregunta de entre 3 y 800 caracteres."},status_code=422)
    if not _plazas.acquire(blocking=False):
        return JSONResponse({"detail":"Estoy atendiendo otras consultas. Prueba de nuevo en unos segundos."},status_code=429)
    try:
        resultado=await run_in_threadpool(responder,pregunta)
        return JSONResponse(resultado)
    except ConsultaNoDisponible as exc:
        return JSONResponse({"detail":str(exc)},status_code=503)
    except Exception:
        return JSONResponse({"detail":"No he podido completar la consulta. No dispongo de una respuesta verificada."},status_code=503)
    finally:
        _plazas.release()
