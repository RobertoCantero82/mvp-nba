"""
Publicador de la web estatica de M.V.P.

Prepara la web con las jornadas ya generadas y la deja lista para subir a Hugging
Face. Hace, en orden:
  1. copio todos los datos/contenido_*.json a frontend/public/data/
  2. regenero el manifest.json (fechas ordenadas de la mas nueva a la mas vieja)
  3. construyo el frontend (npm run build)
  4. copio el resultado a web_estatica/ (la carpeta que se sube al Space)

Despues solo queda enviarlo:
    cd web_estatica
    git add -A && git commit -m "nueva jornada" && git push origin main --force

Uso:
    python publicar.py            # publico TODAS las jornadas que haya generadas
    python publicar.py 2026-10-21 # me aseguro de incluir esa jornada (debe existir
                                  # ya su datos/contenido_2026-10-21.json)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
_DATOS = _RAIZ / "datos"
_PUBLIC_DATA = _RAIZ / "frontend" / "public" / "data"
_DIST = _RAIZ / "frontend" / "dist"
_WEB = _RAIZ / "web_estatica"


def _sincronizar_datos() -> list[str]:
    """Copio los contenido_*.json a public/data y devuelvo las fechas disponibles."""
    _PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    fechas = []
    for origen in sorted(_DATOS.glob("contenido_*.json")):
        shutil.copy2(origen, _PUBLIC_DATA / origen.name)
        fechas.append(origen.stem.replace("contenido_", ""))
    return fechas


def _escribir_manifest(fechas: list[str]) -> None:
    """Escribo el manifest con las fechas ordenadas de la mas nueva a la mas vieja."""
    fechas_ordenadas = sorted(set(fechas), reverse=True)
    with (_PUBLIC_DATA / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(fechas_ordenadas, fh, ensure_ascii=False)


def _construir_frontend() -> None:
    """Lanzo el build de Vite (npm run build) dentro de frontend/."""
    print("[publicar] construyendo el frontend (npm run build)...")
    subprocess.run("npm run build", cwd=_RAIZ / "frontend", shell=True, check=True)


def _copiar_a_web() -> None:
    """Refresco web_estatica/ con el build nuevo, conservando el repo git (.git)."""
    _WEB.mkdir(exist_ok=True)
    # borro lo anterior menos .git (asi no rompo el repo del Space).
    for hijo in _WEB.iterdir():
        if hijo.name == ".git":
            continue
        shutil.rmtree(hijo) if hijo.is_dir() else hijo.unlink()
    # copio el build recien hecho.
    for hijo in _DIST.iterdir():
        destino = _WEB / hijo.name
        shutil.copytree(hijo, destino) if hijo.is_dir() else shutil.copy2(hijo, destino)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass

    fechas = _sincronizar_datos()
    if not fechas:
        print("[publicar] no encuentro ninguna jornada en datos/contenido_*.json.")
        print("[publicar] genera una antes con: python -m agente.mvp --jornada AAAA-MM-DD")
        return 1

    _escribir_manifest(fechas)
    print(f"[publicar] {len(fechas)} jornada(s) en la web: {', '.join(sorted(fechas, reverse=True))}")
    _construir_frontend()
    _copiar_a_web()

    print("\n[publicar] Web lista en web_estatica/. Ahora subela:")
    print('    cd web_estatica')
    print('    git add -A && git commit -m "nueva jornada" && git push origin main --force')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
