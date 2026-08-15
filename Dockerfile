# ---- stage 1: construyo el frontend (React + Vite) ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- stage 2: runtime Python (API + scheduler + estaticos) ----
FROM python:3.12-slim
WORKDIR /app

# instalo las dependencias del backend
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# copio codigo y datos (contenido ya generado; los caches grandes los filtra .dockerignore)
COPY agente/ agente/
COPY backend/ backend/
COPY datos/ datos/

# traigo el frontend ya construido desde la stage anterior
COPY --from=frontend /app/frontend/dist frontend/dist

# dejo el scheduler nocturno corriendo embebido en el proceso del servidor
ENV HABILITAR_SCHEDULER=1
ENV PYTHONUNBUFFERED=1
# Hugging Face Spaces espera el puerto 7860
EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
