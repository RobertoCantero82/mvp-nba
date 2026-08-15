"""
Capa 1 - Ingesta de datos (nba_api).

Responsabilidad UNICA: traer de la API oficial los partidos de una jornada y sus
box scores por jugador, y devolverlos como objetos `Jornada` (ver modelos.py).
Aqui NO se detecta nada ni se razona: solo se leen y se estructuran datos crudos
verificados.

Todo lo que entra al resto del pipeline pasa por aqui. Si un numero no lo
devuelve esta capa, el sistema NO lo conoce.

Cache: para desarrollar sin martillear stats.nba.com, cada jornada se guarda en
`datos/jornada_AAAA-MM-DD.json`. Usa `usar_cache=True` (por defecto) para leer de
disco si existe; `refrescar=True` para forzar una descarga nueva.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from nba_api.stats.endpoints import scoreboardv3, boxscoretraditionalv3

from .modelos import (
    Jornada,
    Partido,
    LineaJugador,
    jornada_a_dict,
    jornada_desde_dict,
)

# directorio de cache: mvp_nba_web/datos/
_DIR_DATOS = Path(__file__).resolve().parents[2] / "datos"

# nba_api a veces tarda o corta; le doy margen y reintentos suaves.
_TIMEOUT = 30
_REINTENTOS = 3
_PAUSA_ENTRE_LLAMADAS = 0.6  # segundos, para no disparar el rate-limit


# ---------------------------------------------------------------------------
# helpers de parseo
# ---------------------------------------------------------------------------

def _min_a_decimal(valor) -> float:
    """Convierte el campo MIN de la API a minutos decimales.

    La API devuelve "34:30", "34.000000", "" o None segun el endpoint/version.
    """
    if valor is None or valor == "":
        return 0.0
    valor = str(valor).strip()
    if ":" in valor:
        mm, ss = valor.split(":")[:2]
        try:
            return round(int(mm) + int(ss) / 60.0, 1)
        except ValueError:
            return 0.0
    try:
        return round(float(valor), 1)
    except ValueError:
        return 0.0


def _entero(valor, defecto: int = 0) -> int:
    if valor is None:
        return defecto
    try:
        return int(valor)
    except (ValueError, TypeError):
        return defecto


def _llamar_con_reintentos(fabrica_endpoint):
    """Ejecuta una llamada a nba_api con reintentos y backoff simple.

    `fabrica_endpoint` es un callable sin argumentos que crea el endpoint (asi
    reintentamos la construccion, que es donde nba_api dispara la peticion HTTP).
    """
    ultimo_error: Optional[Exception] = None
    for intento in range(1, _REINTENTOS + 1):
        try:
            return fabrica_endpoint()
        except Exception as e:  # noqa: BLE001 - nba_api lanza tipos variados
            ultimo_error = e
            espera = _PAUSA_ENTRE_LLAMADAS * intento * 2
            print(f"  [ingesta] intento {intento}/{_REINTENTOS} fallo: {e}. "
                  f"Reintento en {espera:.1f}s...")
            time.sleep(espera)
    raise RuntimeError(f"nba_api no respondio tras {_REINTENTOS} intentos") from ultimo_error


# ---------------------------------------------------------------------------
# descarga
# ---------------------------------------------------------------------------

def _descargar_partidos_del_dia(fecha: str) -> list[dict]:
    """Devuelve las cabeceras de partido + marcadores de la jornada (ScoreboardV3).

    V3 entrega homeTeam/awayTeam con tricode, ciudad, nombre y score directos,
    sin necesidad de cruzar tablas.
    """
    sb = _llamar_con_reintentos(
        lambda: scoreboardv3.ScoreboardV3(
            game_date=fecha, league_id="00", timeout=_TIMEOUT
        )
    )
    games = sb.get_dict().get("scoreboard", {}).get("games", [])

    def _nombre_completo(t: dict) -> str:
        ciudad = (t.get("teamCity") or "").strip()
        nombre = (t.get("teamName") or "").strip()
        return f"{ciudad} {nombre}".strip()

    def _score(t: dict):
        s = t.get("score")
        return _entero(s) if s not in (None, "", 0) or t.get("score") == 0 else None

    partidos: list[dict] = []
    for g in games:
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        partidos.append({
            "game_id": str(g.get("gameId")),
            "estado": (g.get("gameStatusText") or "").strip(),
            "local_id": _entero(home.get("teamId")),
            "local_abbr": (home.get("teamTricode") or "").strip(),
            "local_nombre": _nombre_completo(home),
            "visit_id": _entero(away.get("teamId")),
            "visit_abbr": (away.get("teamTricode") or "").strip(),
            "visit_nombre": _nombre_completo(away),
            "pts_local": _score(home),
            "pts_visit": _score(away),
        })
    return partidos


def _descargar_box_score(game_id: str) -> list[LineaJugador]:
    """Descarga el box score de un partido (BoxScoreTraditionalV3) -> LineaJugador.

    V3 anida los jugadores en boxScoreTraditional.{homeTeam,awayTeam}.players[],
    cada uno con su bloque `statistics`. El campo `position` viene relleno solo
    para los titulares.
    """
    bs = _llamar_con_reintentos(
        lambda: boxscoretraditionalv3.BoxScoreTraditionalV3(
            game_id=game_id, timeout=_TIMEOUT
        )
    )
    box = bs.get_dict().get("boxScoreTraditional", {})
    jugadores: list[LineaJugador] = []
    for lado in ("homeTeam", "awayTeam"):
        equipo = box.get(lado, {})
        equipo_id = _entero(equipo.get("teamId"))
        equipo_abbr = (equipo.get("teamTricode") or "").strip()
        for j in equipo.get("players", []):
            est = j.get("statistics", {}) or {}
            nombre = (j.get("nameI") or
                      f"{j.get('firstName','')} {j.get('familyName','')}").strip()
            jugadores.append(LineaJugador(
                player_id=_entero(j.get("personId")),
                nombre=nombre,
                equipo_id=equipo_id,
                equipo_abbr=equipo_abbr,
                titular=bool((j.get("position") or "").strip()),
                minutos=_min_a_decimal(est.get("minutes")),
                pts=_entero(est.get("points")),
                reb=_entero(est.get("reboundsTotal")),
                ast=_entero(est.get("assists")),
                stl=_entero(est.get("steals")),
                blk=_entero(est.get("blocks")),
                tov=_entero(est.get("turnovers")),
                fgm=_entero(est.get("fieldGoalsMade")),
                fga=_entero(est.get("fieldGoalsAttempted")),
                fg3m=_entero(est.get("threePointersMade")),
                fg3a=_entero(est.get("threePointersAttempted")),
                ftm=_entero(est.get("freeThrowsMade")),
                fta=_entero(est.get("freeThrowsAttempted")),
                plus_minus=_entero(est.get("plusMinusPoints"), None)
                if est.get("plusMinusPoints") is not None else None,
            ))
    return jugadores


# ---------------------------------------------------------------------------
# la API publica que expongo del modulo
# ---------------------------------------------------------------------------

def _ruta_cache(fecha: str) -> Path:
    return _DIR_DATOS / f"jornada_{fecha}.json"


def obtener_jornada(
    fecha: str,
    usar_cache: bool = True,
    refrescar: bool = False,
    guardar: bool = True,
) -> Jornada:
    """Devuelve la Jornada completa (partidos + box scores) de una fecha.

    Args:
        fecha: 'AAAA-MM-DD'.
        usar_cache: si True y existe cache en disco, la usa (salvo `refrescar`).
        refrescar: fuerza descarga nueva aunque haya cache.
        guardar: escribe/actualiza el JSON de cache tras descargar.
    """
    ruta = _ruta_cache(fecha)
    if usar_cache and not refrescar and ruta.exists():
        print(f"[ingesta] Cargando jornada {fecha} desde cache: {ruta.name}")
        with ruta.open(encoding="utf-8") as fh:
            return jornada_desde_dict(json.load(fh))

    print(f"[ingesta] Descargando jornada {fecha} de nba_api...")
    cabeceras = _descargar_partidos_del_dia(fecha)
    print(f"[ingesta] {len(cabeceras)} partidos encontrados. Descargando box scores...")

    partidos: list[Partido] = []
    for i, c in enumerate(cabeceras, 1):
        print(f"[ingesta]   ({i}/{len(cabeceras)}) {c['visit_abbr']} @ {c['local_abbr']} "
              f"[{c['game_id']}]")
        jugadores = _descargar_box_score(c["game_id"])
        time.sleep(_PAUSA_ENTRE_LLAMADAS)
        partidos.append(Partido(
            game_id=c["game_id"],
            fecha=fecha,
            equipo_local_id=c["local_id"],
            equipo_local_abbr=c["local_abbr"],
            equipo_local_nombre=c["local_nombre"],
            equipo_visitante_id=c["visit_id"],
            equipo_visitante_abbr=c["visit_abbr"],
            equipo_visitante_nombre=c["visit_nombre"],
            puntos_local=c["pts_local"],
            puntos_visitante=c["pts_visit"],
            estado=c["estado"],
            jugadores=jugadores,
        ))

    jornada = Jornada(fecha=fecha, partidos=partidos)

    if guardar:
        _DIR_DATOS.mkdir(parents=True, exist_ok=True)
        with ruta.open("w", encoding="utf-8") as fh:
            json.dump(jornada_a_dict(jornada), fh, ensure_ascii=False, indent=2)
        print(f"[ingesta] Cache guardada en {ruta}")

    return jornada


# ---------------------------------------------------------------------------
# prueba manual rapida: python -m agente.herramientas.ingesta 2026-02-26
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass

    fecha = sys.argv[1] if len(sys.argv) > 1 else "2026-02-26"
    jornada = obtener_jornada(fecha, refrescar="--refrescar" in sys.argv)
    print(f"\n=== Jornada {jornada.fecha}: {jornada.num_partidos} partidos ===")
    for p in jornada.partidos:
        marcador = (
            f"{p.puntos_visitante}-{p.puntos_local}"
            if p.puntos_local is not None else "—"
        )
        print(f"  {p.equipo_visitante_abbr} @ {p.equipo_local_abbr}  {marcador}  "
              f"({p.estado})  |  {len(p.jugadores)} jugadores")
    # comprobacion rapida: miro el maximo anotador de la noche
    lineas = jornada.todas_las_lineas()
    if lineas:
        top = max(lineas, key=lambda l: l.pts)
        print(f"\n  Maximo anotador de la noche: {top.nombre} ({top.equipo_abbr}) "
              f"{top.pts} pts")
