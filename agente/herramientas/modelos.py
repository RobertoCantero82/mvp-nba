"""
Contrato de datos entre las capas del pipeline.

REGLA DE ORO DEL PROYECTO
-------------------------
Todo lo que vive en este modulo son CIFRAS YA CALCULADAS Y VERIFICADAS por la
capa de datos (Python determinista). El LLM (capas de razonamiento y redaccion)
solo puede LEER estas estructuras: nunca calcula, nunca completa un hueco, nunca
"recuerda" un numero. Si una pieza de contenido necesita un dato que no esta
aqui, el arreglo es anadir ese dato en la capa 1 -- jamas dejar que el LLM lo
invente.

Por eso los modelos son deliberadamente cerrados: si el paquete que consume el
LLM no contiene ningun campo ambiguo o vacio, el LLM no tiene de donde alucinar.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import json


# ---------------------------------------------------------------------------
# capa 1 - datos crudos ya verificados (lo que produce ingesta.py)
# ---------------------------------------------------------------------------

@dataclass
class LineaJugador:
    """Linea de box score de un jugador en un partido concreto.

    Solo estadisticas de ESTA noche. Los acumulados de carrera (para hitos
    historicos) se piden aparte y se guardan en `Evento.datos`, no aqui.
    """

    player_id: int
    nombre: str
    equipo_id: int
    equipo_abbr: str
    titular: bool
    minutos: float          # minutos jugados en decimal (p.ej. 34.5)
    pts: int
    reb: int
    ast: int
    stl: int
    blk: int
    tov: int
    fgm: int
    fga: int
    fg3m: int
    fg3a: int
    ftm: int
    fta: int
    plus_minus: Optional[int] = None

    @property
    def jugo(self) -> bool:
        return self.minutos > 0


@dataclass
class Partido:
    """Un partido de la jornada con su marcador final y sus dos plantillas."""

    game_id: str
    fecha: str                      # AAAA-MM-DD
    equipo_local_id: int
    equipo_local_abbr: str
    equipo_local_nombre: str
    equipo_visitante_id: int
    equipo_visitante_abbr: str
    equipo_visitante_nombre: str
    puntos_local: Optional[int]
    puntos_visitante: Optional[int]
    estado: str                     # "Final", "En juego", etc.
    jugadores: list[LineaJugador] = field(default_factory=list)

    @property
    def finalizado(self) -> bool:
        return self.estado.lower().startswith("final")

    @property
    def ganador_abbr(self) -> Optional[str]:
        if self.puntos_local is None or self.puntos_visitante is None:
            return None
        if self.puntos_local == self.puntos_visitante:
            return None
        return (
            self.equipo_local_abbr
            if self.puntos_local > self.puntos_visitante
            else self.equipo_visitante_abbr
        )


@dataclass
class Jornada:
    """Todos los partidos de una misma noche NBA."""

    fecha: str                      # AAAA-MM-DD
    partidos: list[Partido] = field(default_factory=list)

    @property
    def num_partidos(self) -> int:
        return len(self.partidos)

    def todas_las_lineas(self) -> list[LineaJugador]:
        return [linea for p in self.partidos for linea in p.jugadores]


# ---------------------------------------------------------------------------
# capa 1.5 - eventos detectados (lo que produce deteccion.py)
# ---------------------------------------------------------------------------

@dataclass
class Evento:
    """Un hecho verificado y digno de mencion detectado en la jornada.

    Es la unidad que el LLM prioriza y redacta. Todo su contenido numerico ya
    esta calculado; el LLM solo decide su peso editorial y lo pone en palabras.

    Campos:
        tipo: etiqueta de categoria del detector (p.ej. "doble_doble",
              "hito_historico_puntos", "record_rookie_triples").
        titular: frase corta y factual, ya redactada por Python, sin adornos.
        jugador / equipo_abbr / game_id: a que se refiere el evento.
        datos: diccionario de cifras exactas que sustentan el evento. Es la
               fuente de verdad trazable: cada numero que el LLM escriba debe
               poder señalarse aqui.
        rareza: 0-100, cuan infrecuente es el hecho (lo fija el detector con
                criterio determinista, no el LLM). Ordena la priorizacion.
        distractor_apto: si este evento sirve como opcion falsa "creible" en el
                quiz (dato real de otro partido de la misma noche).
    """

    tipo: str
    titular: str
    jugador: Optional[str]
    equipo_abbr: Optional[str]
    game_id: Optional[str]
    datos: dict[str, Any] = field(default_factory=dict)
    rareza: int = 0
    distractor_apto: bool = False


@dataclass
class PaqueteJornada:
    """Lo que la capa 1 entrega a la capa 2 (razonamiento).

    Contiene los datos verificados y los eventos ya detectados. El LLM recibe
    ESTO y nada mas: no tiene acceso a la API ni a ningun calculo.
    """

    fecha: str
    num_partidos: int
    partidos: list[Partido]
    eventos: list[Evento]

    def a_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)


# ---------------------------------------------------------------------------
# uso estas utilidades para (de)serializar y cachear en datos/ sin tocar la API
# ---------------------------------------------------------------------------

def jornada_a_dict(jornada: Jornada) -> dict:
    return asdict(jornada)


def jornada_desde_dict(d: dict) -> Jornada:
    partidos = []
    for pd in d.get("partidos", []):
        jugadores = [LineaJugador(**lj) for lj in pd.get("jugadores", [])]
        pd = {**pd, "jugadores": jugadores}
        partidos.append(Partido(**pd))
    return Jornada(fecha=d["fecha"], partidos=partidos)
