"""
Capa 1.5 - Deteccion determinista de hitos.

Convierte los datos crudos de una `Jornada` (ver modelos.py) en una lista de
`Evento`: hechos verificados y dignos de mencion. TODO se calcula aqui en Python.
El LLM recibira estos eventos ya cerrados y solo decidira su peso editorial y los
pondra en palabras -- nunca recalcula ni completa una cifra.

Familias de detectores:
  A. BOX SCORE (solo la noche, sin API extra): dobles, anotacion alta, festival
     de triples, lideres de la jornada, duelos estelares, margenes de partido,
     casi-triple-dobles y eficiencia elite.
  B. HISTORICOS (acumulados de carrera, con API extra cacheada): hitos de puntos,
     triples, asistencias y rebotes de carrera (mismo metodo de resta verificado).
  C. RACHAS multi-jornada: TODO -- necesitan historico persistido de varias noches.

Cada detector asigna una `rareza` (0-100) determinista; esa cifra ordena la
priorizacion editorial posterior.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .modelos import Jornada, Partido, LineaJugador, Evento

_DIR_DATOS = Path(__file__).resolve().parents[2] / "datos"
_TIMEOUT = 30
_MIN_JUGADO = 1.0  # minutos minimos para considerar que un jugador jugo


# ===========================================================================
# a. detectores de box score (solo estadisticas de la noche)
# ===========================================================================

_CATEGORIAS_DOBLE = [
    ("pts", "puntos"),
    ("reb", "rebotes"),
    ("ast", "asistencias"),
    ("stl", "robos"),
    ("blk", "tapones"),
]


def _cats_por_encima(l: LineaJugador, umbral: int) -> list[str]:
    return [nombre for attr, nombre in _CATEGORIAS_DOBLE if getattr(l, attr) >= umbral]


def _ts_pct(l: LineaJugador) -> Optional[float]:
    """True Shooting %: pts / (2 * (TCI + 0.44*TLI)). None si no tiro."""
    intentos = l.fga + 0.44 * l.fta
    if intentos <= 0:
        return None
    return round(l.pts / (2 * intentos) * 100, 1)


def detectar_dobles(jornada: Jornada) -> list[Evento]:
    """Doble-dobles, triple-dobles y cuadruple-dobles (solo box score)."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        for l in p.jugadores:
            cats = _cats_por_encima(l, 10)
            n = len(cats)
            if n < 2:
                continue
            if n == 2:
                tipo, etq, rareza = "doble_doble", "doble-doble", 30
            elif n == 3:
                tipo, etq, rareza = "triple_doble", "triple-doble", 82
            else:
                tipo, etq, rareza = "cuadruple_doble", "cuadruple-doble", 99
            eventos.append(Evento(
                tipo=tipo,
                titular=f"{l.nombre} ({l.equipo_abbr}) firma un {etq}: "
                        + ", ".join(f"{getattr(l, a)} {n2}"
                                    for a, n2 in _CATEGORIAS_DOBLE if getattr(l, a) >= 10),
                jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=p.game_id,
                datos={"categorias": cats, "pts": l.pts, "reb": l.reb, "ast": l.ast,
                       "stl": l.stl, "blk": l.blk, "min": l.minutos},
                rareza=rareza, distractor_apto=True,
            ))
    return eventos


def detectar_casi_triple_doble(jornada: Jornada) -> list[Evento]:
    """Se queda a un suspiro del triple-doble: 2 categorias >=10 y una tercera 8-9."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        for l in p.jugadores:
            if len(_cats_por_encima(l, 10)) != 2:
                continue
            casi = [(nombre, getattr(l, a)) for a, nombre in _CATEGORIAS_DOBLE
                    if 8 <= getattr(l, a) <= 9]
            if not casi:
                continue
            nombre_cat, valor = casi[0]
            eventos.append(Evento(
                tipo="casi_triple_doble",
                titular=f"{l.nombre} ({l.equipo_abbr}) se queda a {10 - valor} de un "
                        f"triple-doble ({l.pts} pts, {l.reb} reb, {l.ast} ast)",
                jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=p.game_id,
                datos={"pts": l.pts, "reb": l.reb, "ast": l.ast,
                       "categoria_a_falta": nombre_cat, "valor": valor},
                rareza=56, distractor_apto=True,
            ))
    return eventos


def detectar_anotacion_alta(jornada: Jornada, umbral: int = 30) -> list[Evento]:
    """Partidos de anotacion alta (>= umbral puntos)."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        for l in p.jugadores:
            if l.pts < umbral:
                continue
            rareza = 95 if l.pts >= 50 else 72 if l.pts >= 40 else 45
            eventos.append(Evento(
                tipo="anotacion_alta",
                titular=f"{l.nombre} ({l.equipo_abbr}) anota {l.pts} puntos "
                        f"({l.fgm}/{l.fga} TC, {l.fg3m}/{l.fg3a} T3, {l.ftm}/{l.fta} TL)",
                jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=p.game_id,
                datos={"pts": l.pts, "fgm": l.fgm, "fga": l.fga, "fg3m": l.fg3m,
                       "fg3a": l.fg3a, "ftm": l.ftm, "fta": l.fta, "min": l.minutos,
                       "ts_pct": _ts_pct(l)},
                rareza=rareza, distractor_apto=True,
            ))
    return eventos


def detectar_eficiencia_elite(jornada: Jornada, umbral_pts: int = 25,
                              umbral_ts: float = 68.0) -> list[Evento]:
    """Anotacion notable con puntería sobresaliente (TS% muy alto)."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        for l in p.jugadores:
            ts = _ts_pct(l)
            if l.pts < umbral_pts or ts is None or ts < umbral_ts:
                continue
            eventos.append(Evento(
                tipo="eficiencia_elite",
                titular=f"{l.nombre} ({l.equipo_abbr}) firma {l.pts} pts con un "
                        f"{ts}% de tiro real (TS%), puntería de élite",
                jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=p.game_id,
                datos={"pts": l.pts, "ts_pct": ts, "fgm": l.fgm, "fga": l.fga,
                       "fg3m": l.fg3m, "fg3a": l.fg3a, "ftm": l.ftm, "fta": l.fta},
                rareza=62, distractor_apto=True,
            ))
    return eventos


def detectar_festival_triples(jornada: Jornada, umbral: int = 6) -> list[Evento]:
    """Jugadores con muchos triples anotados (>= umbral)."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        for l in p.jugadores:
            if l.fg3m < umbral:
                continue
            rareza = 40 + min(50, (l.fg3m - umbral) * 8)
            eventos.append(Evento(
                tipo="festival_triples",
                titular=f"{l.nombre} ({l.equipo_abbr}) enchufa {l.fg3m} triples "
                        f"(de {l.fg3a} intentos)",
                jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=p.game_id,
                datos={"fg3m": l.fg3m, "fg3a": l.fg3a, "pts": l.pts},
                rareza=rareza, distractor_apto=True,
            ))
    return eventos


def detectar_lideres_jornada(jornada: Jornada) -> list[Evento]:
    """El mejor de TODA la noche en puntos, rebotes, asistencias y triples.

    Util para el quiz ("quien lidero la jornada en...") y como distractores.
    """
    lineas = [l for l in jornada.todas_las_lineas() if l.minutos >= _MIN_JUGADO]
    if not lineas:
        return []
    categorias = [
        ("pts", "anotador", "puntos", 58),
        ("reb", "reboteador", "rebotes", 52),
        ("ast", "asistente", "asistencias", 52),
        ("fg3m", "triplista", "triples", 50),
    ]
    game_por_jugador = {l.player_id: p.game_id
                        for p in jornada.partidos for l in p.jugadores}
    eventos: list[Evento] = []
    for attr, rol, unidad, rareza in categorias:
        lider = max(lineas, key=lambda l: getattr(l, attr))
        valor = getattr(lider, attr)
        if valor <= 0:
            continue
        eventos.append(Evento(
            tipo="lider_jornada",
            titular=f"Mejor {rol} de la jornada: {lider.nombre} ({lider.equipo_abbr}) "
                    f"con {valor} {unidad}",
            jugador=lider.nombre, equipo_abbr=lider.equipo_abbr,
            game_id=game_por_jugador.get(lider.player_id),
            datos={"categoria": unidad, "valor": valor},
            rareza=rareza, distractor_apto=True,
        ))
    return eventos


def detectar_duelos(jornada: Jornada, umbral: int = 25) -> list[Evento]:
    """Duelo estelar: un jugador de cada equipo con >= umbral puntos en el mismo partido."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        locales = [l for l in p.jugadores
                   if l.equipo_abbr == p.equipo_local_abbr and l.pts >= umbral]
        visit = [l for l in p.jugadores
                 if l.equipo_abbr == p.equipo_visitante_abbr and l.pts >= umbral]
        if not locales or not visit:
            continue
        a = max(locales, key=lambda l: l.pts)
        b = max(visit, key=lambda l: l.pts)
        eventos.append(Evento(
            tipo="duelo_estelar",
            titular=f"Duelo de anotadores: {b.nombre} ({b.equipo_abbr}, {b.pts}) vs "
                    f"{a.nombre} ({a.equipo_abbr}, {a.pts})",
            jugador=None, equipo_abbr=None, game_id=p.game_id,
            datos={"jugador_a": a.nombre, "pts_a": a.pts, "equipo_a": a.equipo_abbr,
                   "jugador_b": b.nombre, "pts_b": b.pts, "equipo_b": b.equipo_abbr},
            rareza=58, distractor_apto=True,
        ))
    return eventos


def detectar_margenes(jornada: Jornada) -> list[Evento]:
    """Palizas (margen >= 25) y finales de infarto (margen <= 4)."""
    eventos: list[Evento] = []
    for p in jornada.partidos:
        if p.puntos_local is None or p.puntos_visitante is None:
            continue
        margen = abs(p.puntos_local - p.puntos_visitante)
        ganador = p.ganador_abbr
        if margen >= 25:
            eventos.append(Evento(
                tipo="paliza", titular=f"Paliza: {ganador} gana por {margen} "
                f"({p.equipo_visitante_abbr} {p.puntos_visitante}-{p.puntos_local} "
                f"{p.equipo_local_abbr})",
                jugador=None, equipo_abbr=ganador, game_id=p.game_id,
                datos={"margen": margen, "ganador": ganador,
                       "pts_local": p.puntos_local, "pts_visit": p.puntos_visitante},
                rareza=38, distractor_apto=True,
            ))
        elif margen <= 4:
            eventos.append(Evento(
                tipo="final_ajustado", titular=f"Final ajustado por {margen}: "
                f"{p.equipo_visitante_abbr} {p.puntos_visitante}-{p.puntos_local} "
                f"{p.equipo_local_abbr}",
                jugador=None, equipo_abbr=ganador, game_id=p.game_id,
                datos={"margen": margen, "ganador": ganador,
                       "pts_local": p.puntos_local, "pts_visit": p.puntos_visitante},
                rareza=52, distractor_apto=True,
            ))
    return eventos


# ===========================================================================
# b. detectores historicos: hitos de acumulados de carrera
# ===========================================================================
#
# metodo determinista y verificado para conocer un acumulado de carrera justo al
# terminar un partido concreto (no ahora):
#
#   carrera_antes_de_temporada = carrera_total_actual - total_de_esta_temporada
#   carrera_tras_partido        = carrera_antes_de_temporada
#                                 + acumulado_en_la_temporada_hasta_ese_partido
#
# lo aplico igual a puntos, triples, asistencias y rebotes. todo son cifras de la
# API; el LLM no calcula nada.

# mapeo mi nombre de stat -> clave en los endpoints de nba_api (career/season/gamelog)
_STATS_CARRERA = {"pts": "PTS", "fg3m": "FG3M", "ast": "AST", "reb": "REB"}

_UMBRALES_CARRERA = {
    "pts": list(range(10000, 42000, 1000)),
    "fg3m": [1000, 1500, 2000, 2500, 3000, 3500],
    "ast": [5000, 7500, 10000, 12500, 15000],
    "reb": [7500, 10000, 12500, 15000],
}

_UNIDAD = {"pts": "puntos", "fg3m": "triples", "ast": "asistencias", "reb": "rebotes"}

# snapshot de referencia de maximos anotadores historicos (temporada regular).
# lo uso para dar contexto verificado ("Nº X de la historia") sin que el LLM lo invente.
# TODO: externalizar a datos/referencias.json y automatizar su actualizacion.
_TOP_ANOTADORES_HISTORICOS = [
    ("LeBron James", 42000), ("Kareem Abdul-Jabbar", 38387),
    ("Karl Malone", 36928), ("Kobe Bryant", 33643),
    ("Michael Jordan", 32292), ("Dirk Nowitzki", 31560),
    ("Kevin Durant", 32000), ("Wilt Chamberlain", 31419),
]


def _rank_anotador(puntos: int) -> Optional[int]:
    return sum(1 for _, p in _TOP_ANOTADORES_HISTORICOS if p > puntos) + 1


def _rareza_carrera(stat: str, umbral: int) -> int:
    if stat == "pts":
        return 98 if umbral >= 30000 else 88 if umbral >= 25000 else \
               78 if umbral >= 20000 else 66 if umbral >= 15000 else 55
    if stat == "fg3m":
        return 96 if umbral >= 3000 else 88 if umbral >= 2500 else \
               80 if umbral >= 2000 else 72 if umbral >= 1500 else 64
    if stat == "ast":
        return 94 if umbral >= 12500 else 86 if umbral >= 10000 else \
               78 if umbral >= 7500 else 70
    if stat == "reb":
        return 94 if umbral >= 15000 else 86 if umbral >= 12500 else \
               78 if umbral >= 10000 else 70
    return 60


def _cache_carrera_path(player_id: int, season: str) -> Path:
    return _DIR_DATOS / f"carrera_{player_id}_{season}.json"


def _obtener_cache_carrera(player_id: int, season: str) -> Optional[dict]:
    """Carga (o descarga y cachea) los totales de inicio de temporada y el gamelog
    completo de un jugador. Devuelve el dict cacheado o None si no se puede.

    Cacheo en datos/carrera_<id>_<season>.json con formato versionado ('v': 2).
    Lo comparten el detector de hitos de carrera y el de rachas.
    """
    from nba_api.stats.endpoints import playercareerstats, playergamelog

    ruta = _cache_carrera_path(player_id, season)
    if ruta.exists():
        try:
            with ruta.open(encoding="utf-8") as fh:
                cache = json.load(fh)
            if cache.get("v") == 2:
                return cache
        except Exception:
            pass  # esquema viejo o corrupto: lo reconstruyo

    try:
        c = playercareerstats.PlayerCareerStats(
            player_id=player_id, timeout=_TIMEOUT).get_normalized_dict()
        car = c["CareerTotalsRegularSeason"][0]
        filas_season = [s for s in c["SeasonTotalsRegularSeason"]
                        if s["SEASON_ID"] == season]
        if not filas_season:
            return None
        sea = filas_season[-1]
        antes_temp = {k: car[api] - sea[api] for k, api in _STATS_CARRERA.items()}
        time.sleep(0.6)
        gl = playergamelog.PlayerGameLog(
            player_id=player_id, season=season,
            timeout=_TIMEOUT).get_normalized_dict()["PlayerGameLog"]
        cache = {
            "v": 2,
            "antes_temp": antes_temp,
            "gamelog": [{"fecha": g["GAME_DATE"],
                         **{k: g[api] for k, api in _STATS_CARRERA.items()}}
                        for g in gl],
        }
        _DIR_DATOS.mkdir(parents=True, exist_ok=True)
        with ruta.open("w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=2)
        time.sleep(0.6)
        return cache
    except Exception as e:  # noqa: BLE001
        print(f"  [deteccion] no se pudo consultar carrera de {player_id}: {e}")
        return None


def _acumulados_carrera_tras_partido(
    player_id: int, fecha: str, season: str
) -> Optional[dict]:
    """Devuelve {stat: {'antes':X,'despues':Y,'noche':Z}} para cada stat de carrera."""
    cache = _obtener_cache_carrera(player_id, season)
    if cache is None:
        return None

    objetivo = datetime.strptime(fecha, "%Y-%m-%d").strftime("%b %d, %Y")
    acc = {k: 0 for k in _STATS_CARRERA}
    noche = None
    for g in sorted(cache["gamelog"],
                    key=lambda x: datetime.strptime(x["fecha"], "%b %d, %Y")):
        for k in _STATS_CARRERA:
            acc[k] += g[k]
        if g["fecha"] == objetivo:
            noche = {k: g[k] for k in _STATS_CARRERA}
            break
    if noche is None:
        return None
    return {
        k: {"antes": cache["antes_temp"][k] + acc[k] - noche[k],
            "despues": cache["antes_temp"][k] + acc[k],
            "noche": noche[k]}
        for k in _STATS_CARRERA
    }


def detectar_hitos_carrera(
    jornada: Jornada, season: str, top_n: int = 25, umbral_pts_noche: int = 12
) -> list[Evento]:
    """Cruces de umbrales redondos de puntos/triples/asistencias/rebotes de carrera.

    Acota llamadas a los `top_n` maximos anotadores de la noche con al menos
    `umbral_pts_noche` puntos (los hitos de carrera los rondan estrellas veteranas;
    filtrar por anotacion es una heuristica barata para no llamar por todos).
    """
    candidatos = sorted(
        [(l, p.game_id) for p in jornada.partidos for l in p.jugadores
         if l.pts >= umbral_pts_noche],
        key=lambda t: t[0].pts, reverse=True,
    )[:top_n]

    eventos: list[Evento] = []
    for l, game_id in candidatos:
        info = _acumulados_carrera_tras_partido(l.player_id, jornada.fecha, season)
        if not info:
            continue
        for stat, umbrales in _UMBRALES_CARRERA.items():
            d = info[stat]
            for umbral in umbrales:
                if d["antes"] < umbral <= d["despues"]:
                    datos = {
                        "stat": stat, "umbral": umbral,
                        "carrera_antes": d["antes"], "carrera_despues": d["despues"],
                        "esta_noche": d["noche"],
                    }
                    if stat == "pts":
                        datos["rank_historico_aprox"] = _rank_anotador(umbral)
                    eventos.append(Evento(
                        tipo=f"hito_{stat}_carrera",
                        titular=f"{l.nombre} ({l.equipo_abbr}) supera los "
                                f"{umbral:,} {_UNIDAD[stat]} de carrera".replace(",", "."),
                        jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=game_id,
                        datos=datos,
                        rareza=_rareza_carrera(stat, umbral),
                        distractor_apto=False,  # un hito unico no es buen distractor
                    ))
    return eventos


# ===========================================================================
# c. rachas multi-jornada (varios partidos seguidos cumpliendo una condicion)
# ===========================================================================
#
# no necesito persistir yo las noches: el gamelog de temporada de nba_api ya trae
# el partido a partido de cada jugador, asi que reutilizo la misma cache que los
# hitos de carrera y cuento la racha que TERMINA esta noche. son cifras de la API;
# el LLM no calcula nada.

# cada tupla: (stat, umbral por partido, longitud minima, etiqueta, rareza base)
_RACHAS = [
    ("pts", 30, 3, "anotando 30+ puntos", 74),
    ("pts", 20, 6, "anotando 20+ puntos", 58),
    ("fg3m", 4, 4, "metiendo 4+ triples", 54),
]


def _racha_hasta(gamelog: list[dict], objetivo: str, stat: str, umbral: int) -> int:
    """Cuenta partidos consecutivos que terminan en `objetivo` con stat >= umbral."""
    juegos = sorted(gamelog, key=lambda g: datetime.strptime(g["fecha"], "%b %d, %Y"))
    hasta: list[dict] = []
    for g in juegos:
        hasta.append(g)
        if g["fecha"] == objetivo:
            break
    else:
        return 0  # el partido objetivo no esta en el gamelog
    racha = 0
    for g in reversed(hasta):
        if g[stat] >= umbral:
            racha += 1
        else:
            break
    return racha


def detectar_rachas(
    jornada: Jornada, season: str, top_n: int = 25, umbral_pts_noche: int = 12
) -> list[Evento]:
    """Rachas individuales que siguen vivas esta noche.

    Reutiliza la cache de carrera (misma que los hitos), asi que si ya se descargo
    para el detector de hitos no hace llamadas nuevas.
    """
    candidatos = sorted(
        [(l, p.game_id) for p in jornada.partidos for l in p.jugadores
         if l.pts >= umbral_pts_noche],
        key=lambda t: t[0].pts, reverse=True,
    )[:top_n]

    objetivo = datetime.strptime(jornada.fecha, "%Y-%m-%d").strftime("%b %d, %Y")
    eventos: list[Evento] = []
    for l, game_id in candidatos:
        cache = _obtener_cache_carrera(l.player_id, season)
        if not cache:
            continue
        # una racha por jugador: la primera (mas exigente) que cumpla la longitud.
        for stat, umbral, minlen, etq, base in _RACHAS:
            racha = _racha_hasta(cache["gamelog"], objetivo, stat, umbral)
            if racha >= minlen:
                eventos.append(Evento(
                    tipo=f"racha_{stat}",
                    titular=f"{l.nombre} ({l.equipo_abbr}) encadena {racha} partidos "
                            f"seguidos {etq}",
                    jugador=l.nombre, equipo_abbr=l.equipo_abbr, game_id=game_id,
                    datos={"stat": stat, "umbral": umbral, "longitud": racha},
                    rareza=min(96, base + (racha - minlen) * 4),
                    distractor_apto=False,
                ))
                break
    return eventos


# ===========================================================================
# orquestador de deteccion
# ===========================================================================

def _season_desde_fecha(fecha: str) -> str:
    """Deriva la temporada NBA ('2025-26') de una fecha. Arranca en octubre."""
    d = datetime.strptime(fecha, "%Y-%m-%d")
    inicio = d.year - 1 if d.month <= 8 else d.year
    return f"{inicio}-{str(inicio + 1)[-2:]}"


def detectar(jornada: Jornada, con_hitos_carrera: bool = True) -> list[Evento]:
    """Corre todos los detectores y devuelve los eventos ordenados por rareza."""
    eventos: list[Evento] = []
    # a - box score
    eventos += detectar_dobles(jornada)
    eventos += detectar_casi_triple_doble(jornada)
    eventos += detectar_anotacion_alta(jornada)
    eventos += detectar_eficiencia_elite(jornada)
    eventos += detectar_festival_triples(jornada)
    eventos += detectar_lideres_jornada(jornada)
    eventos += detectar_duelos(jornada)
    eventos += detectar_margenes(jornada)
    # b - historicos y rachas (comparten la cache de gamelog de temporada)
    if con_hitos_carrera:
        season = _season_desde_fecha(jornada.fecha)
        print(f"[deteccion] Revisando hitos de carrera y rachas (temporada {season})...")
        eventos += detectar_hitos_carrera(jornada, season)
        eventos += detectar_rachas(jornada, season)

    eventos.sort(key=lambda e: e.rareza, reverse=True)
    return eventos


# ---------------------------------------------------------------------------
# prueba manual: python -m agente.herramientas.deteccion 2026-02-26 [--sin-carrera]
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass
    from .ingesta import obtener_jornada

    fecha = next((a for a in sys.argv[1:] if not a.startswith("--")), "2026-02-26")
    con_carrera = "--sin-carrera" not in sys.argv

    jornada = obtener_jornada(fecha)
    eventos = detectar(jornada, con_hitos_carrera=con_carrera)

    print(f"\n=== {len(eventos)} eventos detectados en {fecha} "
          f"(ordenados por rareza) ===\n")
    for e in eventos:
        print(f"  [{e.rareza:3}] {e.tipo:20} | {e.titular}")
        if e.tipo.startswith("hito_") and "carrera_antes" in e.datos:
            extra = ""
            if e.datos.get("rank_historico_aprox"):
                extra = f" (#{e.datos['rank_historico_aprox']} historico aprox.)"
            print(f"        -> antes={e.datos['carrera_antes']:,} "
                  f"despues={e.datos['carrera_despues']:,}{extra}")
