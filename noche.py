"""
Rutina de una noche, en un solo comando.

Hace todo lo de una jornada de golpe:
  1. genero el contenido con la IA (pipeline nocturno).
  2. publico la web (copio datos, regenero el manifest, construyo).
  3. subo la web a Hugging Face (commit + push).

Uso:
    python noche.py 2026-10-21     # una jornada concreta
    python noche.py                # la jornada de anoche (ayer)

Requisitos: GROQ_API_KEY en .env, y estar autenticado en git para el push.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent


def _paso(titulo: str, cmd, cwd=None, shell=False) -> None:
    print(f"\n=== {titulo} ===")
    subprocess.run(cmd, cwd=cwd or _RAIZ, shell=shell, check=True)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass

    fecha = sys.argv[1] if len(sys.argv) > 1 else (date.today() - timedelta(days=1)).isoformat()
    print(f"### Rutina de la jornada {fecha} ###")

    # 1. genero el contenido de la jornada.
    _paso("1/3 · Genero el contenido con la IA",
          [sys.executable, "-m", "agente.mvp", "--jornada", fecha])

    # 2. publico la web (sincroniza datos + manifest + build en web_estatica/).
    _paso("2/3 · Preparo la web", [sys.executable, "publicar.py"])

    # 3. subo la web a Hugging Face.
    web = _RAIZ / "web_estatica"
    _paso("3/3 · Subo a Hugging Face", "git add -A", cwd=web, shell=True)
    subprocess.run(f'git commit -m "jornada {fecha}"', cwd=web, shell=True)  # puede no haber cambios
    _paso("   push", "git push origin main --force", cwd=web, shell=True)

    print(f"\n✅ Jornada {fecha} publicada. Míralo en tu web (Ctrl+Shift+R).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
