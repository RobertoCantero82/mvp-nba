---
title: MVP Analista NBA
emoji: 🏀
colorFrom: orange
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# M.V.P. — Analista NBA

Agente que analiza cada jornada NBA y genera contenido casi listo para publicar
(quiz, resultados + análisis y una pieza contrafactual "qué hubiera pasado"), en
doble versión **con resultados** / **sin spoilers**.

## Arquitectura de 3 capas (regla innegociable)

1. **Datos** (`agente/herramientas/ingesta.py`, `deteccion.py`): Python
   determinista sobre `nba_api`. Es lo único que calcula cifras.
2. **Razonamiento** (`priorizacion.py`): el LLM ordena las historias por peso
   editorial. No calcula.
3. **Redacción** (`redaccion.py`): el LLM escribe las piezas; cada cifra es
   trazable a la capa 1. El LLM nunca inventa ni estima un número.

## Puesta en marcha

### 1. Entorno Python

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r backend/requirements.txt
```

Copia `.env.example` a `.env` y pon tu `GROQ_API_KEY` (modelo por defecto:
`qwen/qwen3.6-27b`, configurable con `MODELO_LLM`).

### 2. Generar el contenido de una jornada (pipeline nocturno)

```bash
python -m agente.mvp --jornada 2026-02-26
```

Genera `datos/contenido_<fecha>.json`. Opciones: `--refrescar` (ignora caché de
ingesta), `--sin-carrera` (salta hitos históricos), `--solo-datos` (para tras la
detección, sin LLM).

### 3. Backend (API de solo lectura)

```bash
uvicorn backend.main:app --reload
```

Sirve en `http://localhost:8000`. Endpoints: `/jornadas`,
`/jornada/{fecha}?spoilers=true|false`, `/jornada/{fecha}/respuestas`.

### 4. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173` (proxya `/api` al backend). Toggle con-resultados /
sin-spoilers y quiz jugable.

## Despliegue en Hugging Face Spaces (Docker)

Un único contenedor sirve la API (`/api`), el frontend construido y el scheduler
nocturno embebido, en el puerto 7860.

Probar la imagen en local:

```bash
docker build -t mvp-nba .
docker run -p 7860:7860 -e GROQ_API_KEY=tu_clave mvp-nba
# abre http://localhost:7860
```

Desplegar:

1. Crea un Space de tipo **Docker** en Hugging Face.
2. En *Settings → Variables and secrets*, añade el secret `GROQ_API_KEY`.
3. Sube el contenido de `mvp_nba_web/` al repo del Space (incluye el
   `datos/contenido_*.json` de demo; el `.env` NO se sube). HF lee el frontmatter
   del README y construye el `Dockerfile` automáticamente.

El scheduler embebido (`HABILITAR_SCHEDULER=1`, ya fijado en el Dockerfile) dispara
el pipeline cada noche; ajusta la hora con `SCHEDULER_HORA`/`SCHEDULER_TZ`.

## Fuera de alcance (por diseño)

Cualquier contenido de apuestas. La versión sin-spoilers omite por completo la
pieza contrafactual (no puede existir sin revelar antes el resultado real).
