"""
Cliente LLM (Groq) compartido por las capas de razonamiento y redaccion.

Centraliza tres cosas para que priorizacion.py y redaccion.py no se repitan:
  1. Crear el cliente de Groq leyendo GROQ_API_KEY del entorno/.env.
  2. Elegir el modelo via MODELO_LLM (Llama se retira de Groq; por defecto Qwen).
  3. Gestionar el razonamiento de Qwen: es un modelo que emite bloques
     <think>...</think>. Usamos reasoning_format='parsed' para que Groq lo
     separe en un campo aparte y `content` llegue limpio; ademas dejamos un
     fallback que limpia el <think> por si otro modelo no soporta el parametro.

Este modulo NO sabe nada de NBA: solo habla con el LLM. Toda la logica de datos
sigue en la capa 1. El LLM nunca recibe la API ni calcula cifras.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # cargo mvp_nba_web/.env si existe

MODELO = os.environ.get("MODELO_LLM", "qwen/qwen3.6-27b")

_RE_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_RE_JSON = re.compile(r"\{.*\}", re.DOTALL)
# dejo una red de seguridad para los preambulos de razonamiento que algunos
# modelos vuelcan en el texto (p.ej. "**razonamiento interno:** ...") pese a
# reasoning_format='parsed'.
_RE_PREAMBULO = re.compile(
    r"^\s*\**\s*(razonamiento(?:\s+interno)?|pensamiento|analisis|reasoning)\s*\**\s*:.*?"
    r"(?:\n\n|\Z)", re.IGNORECASE | re.DOTALL)


@lru_cache(maxsize=1)
def cliente():
    """Devuelve un cliente de Groq (cacheado). Lanza si falta la clave."""
    from groq import Groq

    clave = os.environ.get("GROQ_API_KEY")
    if not clave:
        raise RuntimeError(
            "Falta GROQ_API_KEY. Copia .env.example a .env y pon tu clave de Groq."
        )
    return Groq(api_key=clave)


def _limpiar(texto: str) -> str:
    """Quita bloques <think> y preambulos de razonamiento volcados en el texto."""
    limpio = _RE_THINK.sub("", texto or "").strip()
    # elimino un preambulo de razonamiento al inicio, solo si queda contenido util.
    sin_preambulo = _RE_PREAMBULO.sub("", limpio, count=1).strip()
    return sin_preambulo if sin_preambulo else limpio


def _chat(system: str, user: str, temperature: float, max_tokens: int,
          json_mode: bool) -> str:
    """Llamada base a Groq con razonamiento separado. Devuelve `content` limpio."""
    kwargs = {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # con reasoning_format='parsed' saco el <think> fuera del content (modelos Qwen).
    try:
        resp = cliente().chat.completions.create(reasoning_format="parsed", **kwargs)
    except Exception:
        # si el modelo no soporta reasoning_format, hago la llamada normal y limpio.
        resp = cliente().chat.completions.create(**kwargs)
    return _limpiar(resp.choices[0].message.content)


def completar_texto(system: str, user: str, temperature: float = 0.7,
                    max_tokens: int = 1500) -> str:
    """Genera prosa. Para la capa de redaccion."""
    return _chat(system, user, temperature, max_tokens, json_mode=False)


def completar_json(system: str, user: str, temperature: float = 0.2,
                   max_tokens: int = 2000) -> dict:
    """Genera y parsea un objeto JSON. Para razonamiento estructurado.

    No usamos el response_format json estricto de Groq porque choca con el
    razonamiento de Qwen; en su lugar pedimos JSON en el prompt y lo extraemos.
    """
    system_json = (system + "\n\nResponde EXCLUSIVAMENTE con un objeto JSON valido, "
                   "sin texto antes ni despues, sin bloques de codigo markdown.")
    bruto = _chat(system_json, user, temperature, max_tokens, json_mode=True)
    return _extraer_json(bruto)


def _extraer_json(texto: str) -> dict:
    """Parsea JSON tolerando adornos (```json ... ``` o texto alrededor)."""
    limpio = texto.strip()
    if limpio.startswith("```"):
        limpio = limpio.strip("`")
        if limpio.lower().startswith("json"):
            limpio = limpio[4:]
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        m = _RE_JSON.search(limpio)
        if m:
            return json.loads(m.group(0))
        raise
