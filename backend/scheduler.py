"""
Scheduler nocturno con APScheduler.

Dispara el pipeline una vez cada noche para dejar el contenido de la jornada
listo antes de que nadie lo pida. Corre DENTRO del propio contenedor, sin
infraestructura externa (encaja con el despliegue en Hugging Face Spaces).

Uso:
    python -m backend.scheduler                 # arranca el planificador (bloquea)
    python -m backend.scheduler --ahora         # ejecuta ya la jornada de anoche
    python -m backend.scheduler --ahora 2026-02-26   # ejecuta ya una fecha dada
    python -m backend.scheduler --ahora --solo-datos # sin llamar al LLM (prueba)

Config por entorno:
    SCHEDULER_HORA    hora local del disparo diario (0-23, por defecto 9)
    SCHEDULER_MINUTO  minuto (0-59, por defecto 0)
    SCHEDULER_TZ      zona horaria (por defecto Europe/Madrid)
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from datetime import date, datetime, timedelta


def _fecha_de_anoche() -> str:
    """La jornada NBA 'de anoche' en EE.UU. se cierra de madrugada; usamos ayer."""
    return (date.today() - timedelta(days=1)).isoformat()


def ejecutar_pipeline(fecha: str | None = None, solo_datos: bool = False) -> bool:
    """Ejecuta el pipeline para una fecha (o la de anoche). Devuelve True si fue bien.

    No propaga excepciones: un fallo de una noche no debe tumbar el scheduler.
    """
    fecha = fecha or _fecha_de_anoche()
    inicio = datetime.now()
    print(f"[scheduler] {inicio:%Y-%m-%d %H:%M:%S} -> pipeline de la jornada {fecha}"
          + (" (solo datos)" if solo_datos else ""))
    try:
        from agente.mvp import construir_paquete, guardar_paquete

        paquete = construir_paquete(fecha, refrescar=True, con_carrera=True)
        guardar_paquete(paquete)
        print(f"[scheduler]   {paquete.num_partidos} partidos, "
              f"{len(paquete.eventos)} eventos detectados.")

        if not solo_datos:
            from agente.herramientas.priorizacion import priorizar
            from agente.herramientas.redaccion import redactar
            from agente.mvp import _DIR_DATOS
            import json

            historias = priorizar(paquete)
            contenido = redactar(historias, paquete)
            ruta = _DIR_DATOS / f"contenido_{fecha}.json"
            with ruta.open("w", encoding="utf-8") as fh:
                json.dump(contenido, fh, ensure_ascii=False, indent=2)
            print(f"[scheduler]   contenido redactado en {ruta.name}")

        dur = (datetime.now() - inicio).total_seconds()
        print(f"[scheduler] OK en {dur:.0f}s.")
        return True
    except Exception:  # noqa: BLE001 - un fallo no debe tumbar el planificador
        print(f"[scheduler] ERROR en la jornada {fecha}:")
        traceback.print_exc()
        return False


def _config() -> tuple[int, int, str]:
    return (
        int(os.environ.get("SCHEDULER_HORA", "9")),
        int(os.environ.get("SCHEDULER_MINUTO", "0")),
        os.environ.get("SCHEDULER_TZ", "Europe/Madrid"),
    )


def crear_scheduler_background():
    """Crea y arranca un BackgroundScheduler con el disparo diario. Devuelve la
    instancia (para poder pararla). Pensado para embeberlo en el proceso del
    servidor FastAPI dentro del contenedor."""
    from apscheduler.schedulers.background import BackgroundScheduler

    hora, minuto, tz = _config()
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        ejecutar_pipeline, "cron", hour=hora, minute=minuto,
        id="pipeline_nocturno", misfire_grace_time=3600, coalesce=True,
    )
    scheduler.start()
    print(f"[scheduler] (embebido) pipeline diario a las {hora:02d}:{minuto:02d} {tz}.")
    return scheduler


def iniciar_scheduler() -> None:
    """Arranca APScheduler con un disparo diario (bloqueante, proceso dedicado)."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    hora, minuto, tz = _config()
    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        ejecutar_pipeline, "cron", hour=hora, minute=minuto,
        id="pipeline_nocturno", misfire_grace_time=3600, coalesce=True,
    )
    print(f"[scheduler] Programado el pipeline diario a las "
          f"{hora:02d}:{minuto:02d} {tz}. Ctrl+C para salir.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[scheduler] Detenido.")


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Scheduler nocturno de M.V.P.")
    parser.add_argument("--ahora", nargs="?", const="", metavar="FECHA",
                        help="Ejecuta el pipeline ya (opcional: fecha AAAA-MM-DD); "
                             "sin fecha usa la jornada de anoche.")
    parser.add_argument("--solo-datos", action="store_true",
                        help="Con --ahora: para tras la deteccion (sin LLM).")
    args = parser.parse_args(argv)

    if args.ahora is not None:
        fecha = args.ahora or None
        ok = ejecutar_pipeline(fecha, solo_datos=args.solo_datos)
        return 0 if ok else 1

    iniciar_scheduler()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
