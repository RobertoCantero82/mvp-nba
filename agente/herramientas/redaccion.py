"""
Capa 3 - Redaccion (LLM: genera las piezas de contenido).

A partir de las historias YA priorizadas (capa 2) y los datos verificados (capa 1)
genera el paquete de contenido de la jornada. El LLM SOLO pone en palabras hechos
que ya vienen calculados; nunca inventa una cifra (ver sistema.GUARDARRAILES).

Piezas (orden del briefing):
    1. Quiz: Python construye las opciones de forma determinista (la correcta y
       distractores que son datos REALES de OTROS partidos de la misma noche), y
       el LLM solo aporta una intro con gancho. Asi los distractores nunca se
       inventan ni se pueden descartar por logica simple.
    2. Resultados + analisis (el hito de portada primero).
    3. "Que hubiera pasado": Python calcula la desviacion estadistica real de la
       noche (z-score frente a la media de temporada del jugador) y el LLM la
       traduce a texto. Solo version con-resultados.
    4. Respuestas del quiz (las genera Python; siempre correctas).

Doble version por pieza (una sola llamada): con_resultados / sin_spoilers. Para
prosa larga usamos texto plano con delimitadores (mas robusto que meterla en JSON
y mas barato en tokens que dos llamadas). La capa gratuita de Groq limita ~8000
tokens/minuto, por eso las piezas se generan espaciadas (`_PAUSA_TPM`).
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .modelos import PaqueteJornada, Evento
from ..sistema import VOZ_EDITORIAL, GUARDARRAILES
from . import llm

_DIR_DATOS = Path(__file__).resolve().parents[2] / "datos"
_PAUSA_TPM = 20  # segundos entre llamadas (limite tokens/minuto de la capa gratis)

# uso esta instruccion para que Qwen no vuelque su razonamiento en el texto.
# (el razonamiento ya se separa via reasoning_format='parsed'; pedirlo aqui hacia
# que el modelo escribiera secciones visibles tipo "razonamiento interno:".)
_BREVE = ("\nResponde DIRECTAMENTE con el contenido pedido, sin ningun encabezado "
          "ni seccion de razonamiento (nada de 'Razonamiento interno:', 'Pensamiento:', etc.).")


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def _contexto_historias(historias: list[Evento], n: int = 8) -> str:
    return "\n".join(f"- [{e.tipo}] {e.titular}" for e in historias[:n])


# unidad legible para el numero grande de la portada segun el tipo de hito.
_PORTADA_UNIDAD = {
    "hito_pts_carrera": "puntos de carrera",
    "hito_fg3m_carrera": "triples de carrera",
    "hito_ast_carrera": "asistencias de carrera",
    "hito_reb_carrera": "rebotes de carrera",
    "anotacion_alta": "puntos",
    "festival_triples": "triples",
}


def portada_desde_evento(evento: Evento) -> dict:
    """Extraigo de la historia principal los datos para el 'hero' de portada:
    el numero grande, su unidad y el contexto. Datos puros; el LLM no interviene."""
    d = evento.datos
    numero, unidad, contexto = "", _PORTADA_UNIDAD.get(evento.tipo, ""), ""
    if "umbral" in d:  # hitos de carrera (puntos, triples, ...)
        numero = f"{d['umbral']:,}".replace(",", ".")
        if d.get("rank_historico_aprox"):
            contexto = f"Nº {d['rank_historico_aprox']} de la historia"
    elif evento.tipo == "anotacion_alta":
        numero = str(d.get("pts", ""))
    elif evento.tipo == "festival_triples":
        numero = str(d.get("fg3m", ""))
    elif evento.tipo.startswith("racha_"):
        numero = str(d.get("longitud", ""))
        unidad = "partidos seguidos"
    return {
        "tipo": evento.tipo, "jugador": evento.jugador, "equipo": evento.equipo_abbr,
        "numero": numero, "unidad": unidad, "contexto": contexto,
        "titular": evento.titular,
    }


def resultados_jornada(paquete: PaqueteJornada) -> list[dict]:
    """Marcadores de todos los partidos (datos puros, sin LLM). Son 'con resultados'
    por naturaleza: un marcador es un spoiler, asi que el backend solo los sirve en
    esa version."""
    return [
        {
            "game_id": p.game_id,
            "visitante": p.equipo_visitante_abbr,
            "visitante_nombre": p.equipo_visitante_nombre,
            "pts_visitante": p.puntos_visitante,
            "local": p.equipo_local_abbr,
            "local_nombre": p.equipo_local_nombre,
            "pts_local": p.puntos_local,
            "ganador": p.ganador_abbr,
            "estado": p.estado,
        }
        for p in paquete.partidos
    ]


def _partir_versiones(texto: str) -> dict:
    """Separa la salida del LLM en con_resultados / sin_spoilers por delimitadores."""
    con, sin = "", ""
    if "===SIN===" in texto:
        antes, sin = texto.split("===SIN===", 1)
    else:
        antes, sin = texto, ""
    con = antes.split("===CON===", 1)[-1]
    return {"con_resultados": con.strip(), "sin_spoilers": sin.strip()}


# ---------------------------------------------------------------------------
# pieza 2: resultados + analisis (doble version, una sola llamada)
# ---------------------------------------------------------------------------

def redactar_analisis(historias: list[Evento], paquete: PaqueteJornada) -> dict:
    """Analisis de la jornada en dos versiones. -> {con_resultados, sin_spoilers}."""
    system = VOZ_EDITORIAL + "\n" + GUARDARRAILES + _BREVE
    user = (
        f"Jornada NBA del {paquete.fecha} ({paquete.num_partidos} partidos).\n\n"
        f"HISTORIAS PRIORIZADAS (usa SOLO estos hechos y sus cifras; la primera es "
        f"la portada):\n{_contexto_historias(historias)}\n\n"
        "Escribe el analisis en DOS versiones, separadas EXACTAMENTE por lineas con "
        "'===CON===' (antes de la primera) y '===SIN===' (entre ambas):\n"
        "- Version con-resultados: 3-4 parrafos. Abre con la portada y encadena el "
        "resto con gancho. Nombres y cifras exactas de arriba.\n"
        "- Version sin-spoilers: el MISMO fondo pero SIN nombres de equipo, SIN "
        "marcadores, SIN el nombre del protagonista y SIN cifras exactas que "
        "delaten (nada de '40 puntos' ni '14/28'). Describe el TIPO y la MAGNITUD "
        "de la gesta cualitativamente ('entro en un club que solo 6 jugadores han "
        "pisado', 'una exhibicion anotadora de eficiencia insultante'). Manten la "
        "intriga: que el lector sepa QUE clase de noche fue, no QUIEN ni CUANTO.\n"
    )
    texto = llm.completar_texto(system, user, temperature=0.7, max_tokens=7000)
    versiones = _partir_versiones(texto)
    # la doble version roza el limite de tokens; si el sin-spoilers sale vacio
    # (truncado antes de ===SIN===), reintento una vez tras pausar por el TPM.
    if versiones["con_resultados"] and not versiones["sin_spoilers"]:
        print("[redaccion]   sin-spoilers vacio; reintento una vez...")
        time.sleep(_PAUSA_TPM)
        texto = llm.completar_texto(system, user, temperature=0.7, max_tokens=7000)
        versiones = _partir_versiones(texto)
    return versiones


# ---------------------------------------------------------------------------
# pieza 1: quiz (opciones deterministas + intro del LLM)
# ---------------------------------------------------------------------------

# tipos de evento aptos como "gesta" con protagonista claro para preguntar.
_TIPOS_PREGUNTABLES = {
    "hito_pts_carrera": "superar los {umbral} puntos de carrera",
    "hito_fg3m_carrera": "superar los {umbral} triples de carrera",
    "anotacion_alta": "anotar {pts} puntos en un partido",
    "festival_triples": "meter {fg3m} triples en un partido",
}


def construir_quiz(paquete: PaqueteJornada, historias: list[Evento],
                   n_preguntas: int = 4) -> list[dict]:
    """Construye el quiz de forma determinista (sin LLM).

    Cada pregunta: una gesta real (respuesta correcta) y 3 distractores que son
    jugadores DESTACADOS y REALES de OTROS partidos de la noche (>=18 pts), para
    que sean creibles y no se descarten por logica simple. Nada inventado.
    """
    # armo el pool de jugadores destacados por partido (candidatos a distractor creible).
    destacados_por_partido: dict[str, list[str]] = {}
    for p in paquete.partidos:
        nombres = []
        for l in sorted(p.jugadores, key=lambda x: x.pts, reverse=True):
            if l.pts >= 18 and l.nombre not in nombres:
                nombres.append(l.nombre)
        destacados_por_partido[p.game_id] = nombres

    preguntas: list[dict] = []
    usados_como_gesta: set[str] = set()
    for e in historias:
        if len(preguntas) >= n_preguntas:
            break
        if e.tipo not in _TIPOS_PREGUNTABLES or not e.jugador or not e.game_id:
            continue
        if e.jugador in usados_como_gesta:
            continue
        # distractores: destacados de OTROS partidos, rotando por nº de pregunta
        # para que no se repitan siempre los mismos nombres.
        pool = [nom for gid, noms in destacados_por_partido.items()
                if gid != e.game_id for nom in noms if nom != e.jugador]
        vistos: set[str] = set()
        pool = [d for d in pool if not (d in vistos or vistos.add(d))]
        if len(pool) < 3:
            continue
        desfase = (len(preguntas) * 3) % len(pool)
        rotado = pool[desfase:] + pool[:desfase]
        distractores = rotado[:3]

        gesta = _TIPOS_PREGUNTABLES[e.tipo].format(
            umbral=f"{e.datos.get('umbral', ''):,}".replace(",", ".")
                   if "umbral" in e.datos else "",
            pts=e.datos.get("pts", ""), fg3m=e.datos.get("fg3m", ""),
        )
        # coloco la correcta en una posicion que varia por pregunta (no siempre igual).
        opciones = list(distractores)
        pos = len(preguntas) % 4
        opciones.insert(pos, e.jugador)
        preguntas.append({
            "pregunta": f"¿Que jugador logro {gesta} en esta jornada?",
            "opciones": opciones,
            "correcta": e.jugador,
            "correcta_idx": pos,
            "explicacion": e.titular,
        })
        usados_como_gesta.add(e.jugador)
    return preguntas


def redactar_intro_quiz(quiz: list[dict]) -> str:
    """Una intro breve y con gancho para el quiz (el LLM no toca las opciones)."""
    if not quiz:
        return ""
    system = VOZ_EDITORIAL + _BREVE
    user = (
        f"Vas a presentar un quiz de {len(quiz)} preguntas sobre la jornada NBA, "
        "sin desvelar respuestas. Escribe SOLO una intro de 2-3 frases, con tu "
        "toque de humor, que rete al lector a jugar. No enumeres las preguntas."
    )
    try:
        return llm.completar_texto(system, user, temperature=0.8, max_tokens=2500).strip()
    except Exception as e:  # noqa: BLE001
        print(f"[redaccion] intro del quiz fallo ({e}); uso intro por defecto.")
        return "Cuatro preguntas, cero pistas gratis. A ver cuanto sabes de la noche."


# ---------------------------------------------------------------------------
# pieza 3: "que hubiera pasado" (proyeccion determinista + narracion LLM)
# ---------------------------------------------------------------------------

def _cargar_gamelog_cache(player_id: int, season: str) -> Optional[list[dict]]:
    ruta = _DIR_DATOS / f"carrera_{player_id}_{season}.json"
    if not ruta.exists():
        return None
    try:
        with ruta.open(encoding="utf-8") as fh:
            return json.load(fh).get("gamelog")
    except Exception:
        return None


def calcular_contrafactual(paquete: PaqueteJornada, historias: list[Evento],
                           season: str) -> Optional[dict]:
    """Elige la actuacion de mayor desviacion real y calcula su rango esperado.

    Proyeccion determinista: media y desviacion tipica de puntos del jugador en la
    temporada (de la cache de gamelog). El z-score mide cuanto se salio de lo
    esperado. El LLM NO calcula esto; solo lo narrara.
    """
    objetivo = datetime.strptime(paquete.fecha, "%Y-%m-%d").strftime("%b %d, %Y")
    mejor = None
    # candidatos: protagonistas anotadores con cache de temporada disponible.
    for e in historias:
        if e.tipo not in ("anotacion_alta", "hito_pts_carrera") or not e.jugador:
            continue
        # localizo su linea y su player_id
        linea = next((l for p in paquete.partidos for l in p.jugadores
                      if l.nombre == e.jugador and p.game_id == e.game_id), None)
        if not linea:
            continue
        gl = _cargar_gamelog_cache(linea.player_id, season)
        if not gl or len(gl) < 5:
            continue
        pts_temporada = [g["pts"] for g in gl]
        pts_noche = next((g["pts"] for g in gl if g["fecha"] == objetivo), None)
        if pts_noche is None:
            continue
        media = statistics.mean(pts_temporada)
        sigma = statistics.pstdev(pts_temporada) or 1.0
        z = (pts_noche - media) / sigma
        if mejor is None or abs(z) > abs(mejor["z"]):
            mejor = {
                "jugador": e.jugador, "equipo": linea.equipo_abbr,
                "pts_noche": pts_noche, "media": round(media, 1),
                "sigma": round(sigma, 1), "z": round(z, 2),
                "rango_esperado": [round(media - sigma), round(media + sigma)],
                "game_id": e.game_id,
            }
    return mejor


def redactar_contrafactual(cf: dict) -> str:
    """Narra la pieza contrafactual (solo con_resultados) a partir del calculo."""
    system = VOZ_EDITORIAL + "\n" + GUARDARRAILES + _BREVE
    rango = cf["rango_esperado"]
    user = (
        "Escribe una pieza breve (2 parrafos) de 'que hubiera pasado' sobre esta "
        "actuacion, usando SOLO estas cifras ya calculadas (no inventes ni "
        "recalcules nada):\n"
        f"- Jugador: {cf['jugador']} ({cf['equipo']}).\n"
        f"- Anoto {cf['pts_noche']} puntos esta noche.\n"
        f"- Su media esta temporada es {cf['media']} y lo esperable rondaba el "
        f"rango {rango[0]}-{rango[1]} puntos.\n"
        f"- Se desvio {cf['z']} desviaciones tipicas de su media.\n"
        "Plantea que habria pasado si hubiese rendido en su rango normal: como "
        "cambia la lectura del partido. Con tu toque de humor, pero fiel a los datos."
    )
    return llm.completar_texto(system, user, temperature=0.75, max_tokens=4000).strip()


# ---------------------------------------------------------------------------
# orquestador
# ---------------------------------------------------------------------------

def _season_desde_fecha(fecha: str) -> str:
    d = datetime.strptime(fecha, "%Y-%m-%d")
    inicio = d.year - 1 if d.month <= 8 else d.year
    return f"{inicio}-{str(inicio + 1)[-2:]}"


def redactar(historias: list[Evento], paquete: PaqueteJornada,
             pausas: bool = True) -> dict:
    """Genera el paquete de contenido completo de la jornada (doble version).

    Args:
        pausas: si True, espera `_PAUSA_TPM` s entre llamadas para respetar el
            limite de tokens/minuto de la capa gratuita de Groq.
    """
    season = _season_desde_fecha(paquete.fecha)
    contenido: dict = {"fecha": paquete.fecha}

    # incluyo los marcadores de la jornada (datos puros; el backend los sirve solo con-resultados).
    contenido["resultados"] = resultados_jornada(paquete)

    # portada: la historia principal (la primera priorizada) para el hero.
    contenido["portada"] = portada_desde_evento(historias[0]) if historias else None

    def _pausa():
        if pausas:
            time.sleep(_PAUSA_TPM)

    # pieza 1: quiz (opciones deterministas + intro del LLM)
    print("[redaccion] Construyendo quiz (opciones deterministas)...")
    quiz = construir_quiz(paquete, historias)
    print("[redaccion] Escribiendo intro del quiz...")
    intro = redactar_intro_quiz(quiz)
    contenido["quiz"] = {"intro": intro, "preguntas": quiz}
    _pausa()

    # pieza 2: analisis (doble version)
    print("[redaccion] Escribiendo analisis (doble version)...")
    contenido["analisis"] = redactar_analisis(historias, paquete)
    _pausa()

    # pieza 3: contrafactual (solo con_resultados; se omite en sin_spoilers)
    print("[redaccion] Calculando y escribiendo contrafactual...")
    cf = calcular_contrafactual(paquete, historias, season)
    if cf:
        cf["texto"] = redactar_contrafactual(cf)
        contenido["contrafactual"] = cf
    else:
        contenido["contrafactual"] = None
        print("[redaccion]   (sin datos suficientes para el contrafactual)")

    # pieza 4: respuestas del quiz (deterministas)
    contenido["quiz_respuestas"] = [
        {"pregunta": q["pregunta"], "correcta": q["correcta"],
         "explicacion": q["explicacion"]}
        for q in quiz
    ]
    return contenido
