# Agente M.V.P. — Analista NBA con IA

**M.V.P. = Modelo · Veredicto · Predicción.** Un agente que cada jornada NBA analiza
la noche completa y genera contenido casi listo para publicar: crónica partido a
partido, quiz, una pieza contrafactual ("qué hubiera pasado") y una **predicción de
machine learning** del partido a seguir de mañana.

🔗 **Web en vivo:** https://robertocantero-mvp-nba.static.hf.space

Combina tres disciplinas: **ingeniería de datos** (nba_api), **LLM** (redacción con
Groq/Qwen) y **machine learning** (modelo de predicción propio).

---

## Qué hace

La web tiene dos modos, y arranca **sin spoilers** por defecto:

**Sin spoilers**
- Lo más destacado de la noche (el *tipo* de gesta, sin nombres ni marcadores).
- Recomendación de un partido para ver en diferido, sin desvelar el resultado.
- **La predicción para mañana**: el partido a seguir con la lectura del modelo de ML
  (favorito, probabilidad y margen).
- Un reto de trivia: aciértalo para desbloquear los resultados.

**Con resultados**
- Portada con el hito de la noche.
- Quiz de una pregunta curiosa.
- Crónica partido a partido (marcador + análisis por partido).
- Contrafactual: la actuación más fuera de lo normal, con su rango esperado.

---

## Cómo funciona: arquitectura de 3 capas

**Regla de oro (innegociable):** el LLM nunca inventa ni estima una cifra. Todo número
sale de datos verificados o de un modelo determinista.

1. **Datos** (`agente/herramientas/`): Python determinista.
   - `ingesta.py` — trae la jornada de `nba_api` (endpoints V3).
   - `deteccion.py` — detecta hitos, rachas y récords de carrera.
   - `prediccion.py` — **modelo de ML** (scikit-learn) que predice partidos.
2. **Razonamiento** (`priorizacion.py`): el LLM ordena las historias por peso
   editorial. No calcula.
3. **Redacción** (`redaccion.py`): el LLM escribe las piezas; cada cifra es trazable
   a la capa 1. También narra la predicción del modelo (sin inventarla).

### El modelo de ML

Regresión logística + Ridge entrenados con miles de partidos reales, usando features
*pre-partido* (net rating, forma reciente, descanso) **sin data leakage**. Predice
favorito, probabilidad y margen esperado, usando solo la temporada hasta esa fecha.
~67% de acierto (frente al 56% de "siempre gana el local"). Es un **pronóstico
analítico, nunca un consejo de apuesta** (el proyecto excluye cualquier cosa de apuestas).

---

## Stack

- **Datos:** Python · `nba_api`
- **ML:** `scikit-learn` · `pandas`
- **LLM:** Groq (`qwen/qwen3.6-27b`)
- **Web:** React + Vite (estática) · desplegada gratis en Hugging Face Spaces (Static)
- **Persistencia:** JSON + SQLite

La web es **estática**: el pipeline genera el contenido (JSON) y el frontend lo
muestra; no hay servidor en producción.

---

## Puesta en marcha

```bash
# 1. entorno
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r backend/requirements.txt
# copia .env.example a .env y pon tu GROQ_API_KEY

# 2. entrena el modelo de predicción (una sola vez)
python -m agente.herramientas.prediccion --entrenar

# 3. genera + publica una jornada (todo en un comando)
python noche.py 2026-02-26
```

`noche.py` hace los tres pasos: **genera** el contenido con la IA
(`python -m agente.mvp --jornada ...`), **construye** la web (`publicar.py`) y la
**sube** a Hugging Face. Las jornadas se acumulan solas en un desplegable de fechas.

Para ver el frontend en local: `cd frontend && npm install && npm run dev`.

---

## Estructura

```
mvp_nba_web/
├── agente/
│   ├── mvp.py                 # orquestador del pipeline
│   └── herramientas/
│       ├── ingesta.py         # nba_api
│       ├── deteccion.py       # hitos y rachas
│       ├── prediccion.py      # modelo de ML
│       ├── priorizacion.py    # LLM: prioriza
│       ├── redaccion.py       # LLM: redacta + narra la predicción
│       └── persistencia.py    # SQLite
├── frontend/                  # React + Vite (web estática)
├── backend/                   # API FastAPI (opcional, uso local)
├── noche.py                   # genera + publica + sube, en un comando
├── publicar.py               # construye la web estática
└── datos/                     # contenido generado (JSON)
```

---

## Fuera de alcance (por diseño)

Cualquier contenido relacionado con apuestas, en cualquier forma. La predicción es un
pronóstico analítico, sin cuotas. En modo sin-spoilers no se revela ningún resultado.

---

Redacción asistida por LLM con cifras verificadas.
