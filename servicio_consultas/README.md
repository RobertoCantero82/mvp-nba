---
title: Pregunta a MVP
emoji: 🏀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

Servicio de consultas efímeras a NBA Stats. No crea archivos de preguntas ni resultados, no usa base de datos ni caché de respuestas y no registra peticiones de acceso.

La clave `GROQ_API_KEY` se configura como Secret del Space. `MODELO_LLM` se configura como variable y debe identificar un modelo disponible en tu cuenta de Groq. La URL del frontend se autoriza con `ORIGENES_PERMITIDOS`.

Salud: GET /api/salud. Consultas: POST /api/preguntar con JSON {"pregunta":"..."}.
El almacenamiento y los registros propios de los proveedores de alojamiento o IA están sujetos a sus políticas.
