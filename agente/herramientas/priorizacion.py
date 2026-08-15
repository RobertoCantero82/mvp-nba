"""
Capa 2 - Razonamiento (LLM: prioriza historias).

Recibe un `PaqueteJornada` (datos + eventos YA calculados) y devuelve las
historias ordenadas por peso editorial, SIN redactarlas todavia. El LLM decide
que importa y en que orden; NO toca ninguna cifra.

Blindaje anti-alucinacion: al LLM solo se le pasan indices + titulares ya
redactados por Python. Devuelve una lista de indices; nosotros mapeamos esos
indices de vuelta a los objetos Evento originales. Si el LLM inventa un indice
inexistente, se ignora; los eventos que omita se anexan al final por rareza, de
modo que nunca se pierde ni se inventa informacion.
"""

from __future__ import annotations

from .modelos import PaqueteJornada, Evento
from ..sistema import VOZ_EDITORIAL
from . import llm


def priorizar_determinista(paquete: PaqueteJornada) -> list[Evento]:
    """Orden puramente por rareza (fallback sin LLM)."""
    return sorted(paquete.eventos, key=lambda e: e.rareza, reverse=True)


def _resumen_eventos(eventos: list[Evento]) -> str:
    """Serializa los eventos como lineas indexadas y compactas para el prompt."""
    lineas = []
    for i, e in enumerate(eventos):
        lineas.append(f"{i}. [{e.tipo}, rareza {e.rareza}] {e.titular}")
    return "\n".join(lineas)


def priorizar(paquete: PaqueteJornada, usar_llm: bool = True,
              top_n: int = 20) -> list[Evento]:
    """Devuelve los eventos reordenados por peso editorial.

    Solo se envian al LLM los `top_n` eventos de mayor rareza (para no agotar el
    limite de tokens/minuto de la capa gratuita de Groq); el resto se anexa
    despues por rareza. Ordenar la cola de doble-dobles rutinarios no aporta.

    Args:
        usar_llm: si False, usa solo el orden determinista por rareza.
        top_n: cuantos eventos (por rareza) se someten al criterio del LLM.
    """
    if not usar_llm or not paquete.eventos:
        return priorizar_determinista(paquete)

    ordenados = sorted(paquete.eventos, key=lambda e: e.rareza, reverse=True)
    cabeza = ordenados[:top_n]
    cola = ordenados[top_n:]

    system = VOZ_EDITORIAL + (
        "\n\nAhora actuas como EDITOR JEFE: no escribes todavia, solo decides el "
        "orden. Te doy los hechos ya verificados de una jornada NBA, cada uno con "
        "un indice. Ordenalos por peso editorial para un articulo de la jornada:\n"
        "- Primero el hito de mayor calado (normalmente un record o marca "
        "historica), aunque su 'rareza' numerica no sea la mas alta.\n"
        "- Luego encadena el resto formando un hilo narrativo coherente.\n"
        "- Agrupa mentalmente lo redundante (no repitas 5 veces al mismo jugador)."
    )
    user = (
        f"Jornada del {paquete.fecha}, {paquete.num_partidos} partidos.\n\n"
        f"HECHOS VERIFICADOS MAS DESTACADOS (indice. [tipo, rareza] titular):\n"
        f"{_resumen_eventos(cabeza)}\n\n"
        'Devuelve JSON: {"orden": [lista de indices, del mas importante al menos], '
        '"portada": indice_del_titular_principal}. '
        "Incluye SOLO indices que existan en la lista."
    )

    try:
        resp = llm.completar_json(system, user, temperature=0.2, max_tokens=5000)
    except Exception as e:  # noqa: BLE001
        print(f"[priorizacion] LLM fallo ({e}); uso orden determinista.")
        return priorizar_determinista(paquete)

    n = len(cabeza)
    orden = [i for i in resp.get("orden", []) if isinstance(i, int) and 0 <= i < n]
    portada = resp.get("portada")
    if isinstance(portada, int) and 0 <= portada < n:
        orden = [portada] + [i for i in orden if i != portada]
    # quito duplicados preservando el orden.
    vistos: set[int] = set()
    orden = [i for i in orden if not (i in vistos or vistos.add(i))]
    # anexo los eventos de la cabeza que el LLM omitiera, por rareza, tras los ordenados.
    faltan = sorted((i for i in range(n) if i not in vistos),
                    key=lambda i: cabeza[i].rareza, reverse=True)
    orden += faltan

    # devuelvo la cabeza reordenada por el LLM + la cola (baja rareza) sin tocar.
    return [cabeza[i] for i in orden] + cola
