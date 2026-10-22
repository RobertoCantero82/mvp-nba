FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY datos_consultas/ datos_consultas/
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 7860
CMD ["python", "-m", "uvicorn", "backend.consulta_api:app", "--host", "0.0.0.0", "--port", "7860", "--no-access-log", "--log-level", "warning"]
