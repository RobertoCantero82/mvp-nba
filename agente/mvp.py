"""
Orquestador del pipeline nocturno de M.V.P.

Encadena las capas en orden:
    ingesta (datos)  ->  deteccion (hitos)  ->  [priorizacion + redaccion: LLM]

Uso:
    python -m agente.mvp --jornada 2026-02-26
    python -m agente.mvp --jornada 2026-02-26 --refrescar     # ignora cache
    python -m agente.mvp --jornada 2026-02-26 --sin-carrera   # sin hitos historicos
    python -m agente.mvp --jornada 2026-02-26 --solo-datos    # para hasta deteccion

Estado actual: pasos 1-3 (datos + deteccion) funcionan de punta a punta y
persisten un PaqueteJornada en datos/paquete_<fecha>.json. Priorizacion y
redaccion con Groq son los pasos 4-5 (pendientes); mientras tanto se usa el
orden determinista por rareza.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .herramientas.ingesta import obtener_jornada
from .herramientas.deteccion import detectar
from .herramientas.modelos import PaqueteJornada
from .herramientas.priorizacion import priorizar
from .herramientas.redaccion import redactar

_DIR_DATOS = Path(__file__).resolve().parents[1] / "datos"


def construir_paquete(fecha: str, refrescar: bool, con_carrera: bool) -> PaqueteJornada:
    """Corre ingesta + deteccion y arma el PaqueteJornada (frontera capa1 -> capa2)."""
    jornada = obtener_jornada(fecha, refrescar=refrescar)
    eventos = detectar(jornada, con_hitos_carrera=con_carrera)
    return PaqueteJornada(
        fecha=jornada.fecha,
        num_partidos=jornada.num_partidos,
        partidos=jornada.partidos,
        eventos=eventos,
    )


def guardar_paquete(paquete: PaqueteJornada) -> Path:
    _DIR_DATOS.mkdir(parents=True, exist_ok=True)
    ruta = _DIR_DATOS / f"paquete_{paquete.fecha}.json"
    with ruta.open("w", encoding="utf-8") as fh:
        json.dump(asdict(paquete), fh, ensure_ascii=False, indent=2)
    return ruta


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Pipeline nocturno M.V.P. (Analista NBA)")
    parser.add_argument("--jornada", required=True, help="Fecha de la jornada, AAAA-MM-DD")
    parser.add_argument("--refrescar", action="store_true", help="Ignora la cache de ingesta")
    parser.add_argument("--sin-carrera", action="store_true",
                        help="Salta los hitos historicos (sin llamadas extra a la API)")
    parser.add_argument("--solo-datos", action="store_true",
                        help="Para tras la deteccion (no llama al LLM)")
    args = parser.parse_args(argv)

    print(f"=== M.V.P. pipeline | jornada {args.jornada} ===\n")

    paquete = construir_paquete(
        args.jornada, refrescar=args.refrescar, con_carrera=not args.sin_carrera
    )
    ruta = guardar_paquete(paquete)

    print(f"\n[mvp] Paquete de datos+eventos guardado en {ruta}")
    print(f"[mvp] {paquete.num_partidos} partidos, {len(paquete.eventos)} eventos.")

    if args.solo_datos:
        historias = priorizar(paquete, usar_llm=False)
        top = historias[0] if historias else None
        if top:
            print(f"[mvp] Historia de portada (orden determinista): "
                  f"[{top.rareza}] {top.titular}")
        print("\n[mvp] --solo-datos: fin del pipeline en la capa de deteccion.")
        return 0

    # paso 4: priorizo editorialmente con el LLM.
    print("\n[mvp] Priorizando historias con el LLM...")
    historias = priorizar(paquete)
    if historias:
        print(f"[mvp] Portada: [{historias[0].rareza}] {historias[0].titular}")

    # paso 5: redacto las piezas (quiz, analisis, contrafactual), en doble version.
    print("[mvp] Redactando piezas de contenido (Groq)...\n")
    contenido = redactar(historias, paquete)

    ruta_cont = _DIR_DATOS / f"contenido_{paquete.fecha}.json"
    with ruta_cont.open("w", encoding="utf-8") as fh:
        json.dump(contenido, fh, ensure_ascii=False, indent=2)
    print(f"\n[mvp] Contenido redactado guardado en {ruta_cont}")

    # persisto tambien en SQLite (lineas + contenido); es la BD que lee el backend.
    from .herramientas import persistencia
    conn = persistencia.conectar()
    n = persistencia.guardar_jornada(paquete, conn)
    persistencia.guardar_contenido(paquete.fecha, contenido, conn)
    conn.close()
    print(f"[mvp] Persistido en SQLite: {n} lineas de jugador + el contenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
