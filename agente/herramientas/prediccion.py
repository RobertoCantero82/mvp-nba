"""
Capa 1 - Modelo de Machine Learning para predecir partidos.

Es un modelo DETERMINISTA (Python + scikit-learn): entreno con partidos reales del
histórico y, dado un cruce futuro, estimo la probabilidad de victoria del local y
el margen esperado. El LLM luego SOLO narra ese resultado; la cifra sale del modelo,
nunca del LLM (misma regla que el resto del proyecto).

Enfoque analítico, NO de apuestas: probabilidad y margen como lectura del modelo,
sin cuotas ni consejos de apuesta.

Pipeline:
  1. `entrenar()` baja el histórico (varias temporadas) vía nba_api, construye para
     cada partido features PRE-partido (sin data leakage) y entrena:
       - una regresión logística -> probabilidad de que gane el local.
       - una regresión Ridge -> margen esperado (local - visitante).
     Guarda ambos en datos/modelo_prediccion.joblib y reporta el acierto.
  2. `predecir(local, visitante, season)` calcula las features actuales de cada
     equipo y devuelve favorito, probabilidad y margen.

Uso:
    python -m agente.herramientas.prediccion --entrenar
    python -m agente.herramientas.prediccion --predecir LAL PHX
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

_DIR_DATOS = Path(__file__).resolve().parents[2] / "datos"
_RUTA_MODELO = _DIR_DATOS / "modelo_prediccion.joblib"
_TIMEOUT = 60
_MIN_PARTIDOS = 5      # mínimo de partidos previos por equipo para usar el ejemplo
_FEATS = ["d_net", "d_net10", "d_wpct", "d_rest"]


# ---------------------------------------------------------------------------
# datos
# ---------------------------------------------------------------------------

def _filas_temporada(season: str) -> list[dict]:
    """Todas las filas equipo-partido de una temporada (regular + playoffs)."""
    from nba_api.stats.endpoints import leaguegamefinder

    d = leaguegamefinder.LeagueGameFinder(
        season_nullable=season, league_id_nullable="00", timeout=_TIMEOUT
    ).get_normalized_dict()
    return d.get("LeagueGameFinderResults", [])


def _construir_ejemplos(seasons: list[str]):
    """Construye el DataFrame de ejemplos con features PRE-partido y etiquetas."""
    import pandas as pd

    filas: list[dict] = []
    for s in seasons:
        print(f"  [prediccion] descargando temporada {s}...")
        filas += _filas_temporada(s)
        time.sleep(0.6)

    df = pd.DataFrame(filas)
    df = df[["GAME_ID", "TEAM_ID", "TEAM_ABBREVIATION", "GAME_DATE",
             "MATCHUP", "WL", "PTS", "PLUS_MINUS"]].dropna()
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df["es_local"] = df["MATCHUP"].str.contains("vs.", regex=False)

    hist: dict[int, list[tuple]] = defaultdict(list)   # team_id -> [(pm, win), ...]
    ult_fecha: dict[int, object] = {}
    ejemplos: list[dict] = []

    def _rasgos(tid, fecha):
        h = hist[tid]
        pms = [x[0] for x in h]
        wins = [x[1] for x in h]
        net = sum(pms) / len(pms) if pms else 0.0
        net10 = sum(pms[-10:]) / len(pms[-10:]) if pms else 0.0
        wpct = sum(wins) / len(wins) if wins else 0.5
        ld = ult_fecha.get(tid)
        rest = min((fecha - ld).days, 5) if ld is not None else 3
        return net, net10, wpct, rest, len(h)

    # recorro los partidos en orden cronológico
    for gid, g in sorted(df.groupby("GAME_ID"),
                         key=lambda kv: (kv[1]["GAME_DATE"].iloc[0], kv[0])):
        loc = g[g["es_local"]]
        vis = g[~g["es_local"]]
        if len(loc) != 1 or len(vis) != 1:
            continue
        loc = loc.iloc[0]
        vis = vis.iloc[0]
        fecha = loc["GAME_DATE"]

        hn, hn10, hw, hr, hgames = _rasgos(loc["TEAM_ID"], fecha)
        an, an10, aw, ar, agames = _rasgos(vis["TEAM_ID"], fecha)
        if hgames >= _MIN_PARTIDOS and agames >= _MIN_PARTIDOS:
            ejemplos.append({
                "d_net": hn - an, "d_net10": hn10 - an10,
                "d_wpct": hw - aw, "d_rest": hr - ar,
                "home_win": 1 if loc["WL"] == "W" else 0,
                "margin": int(loc["PTS"] - vis["PTS"]),
                "date": fecha,
            })
        # actualizo el histórico DESPUÉS de generar el ejemplo (sin leakage)
        for r in (loc, vis):
            hist[r["TEAM_ID"]].append((float(r["PLUS_MINUS"]), 1 if r["WL"] == "W" else 0))
            ult_fecha[r["TEAM_ID"]] = fecha

    return pd.DataFrame(ejemplos)


# ---------------------------------------------------------------------------
# entrenamiento
# ---------------------------------------------------------------------------

def entrenar(seasons: Optional[list[str]] = None) -> dict:
    """Entrena y guarda el modelo. Devuelve métricas de validación temporal."""
    import numpy as np
    import joblib
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression, Ridge

    seasons = seasons or ["2023-24", "2024-25", "2025-26"]
    print(f"[prediccion] construyendo dataset de {seasons}...")
    data = _construir_ejemplos(seasons).sort_values("date").reset_index(drop=True)
    if len(data) < 200:
        raise RuntimeError(f"muy pocos ejemplos ({len(data)}) para entrenar")

    X = data[_FEATS].values
    y = data["home_win"].values
    ym = data["margin"].values

    # validación TEMPORAL: entreno con el pasado, pruebo con el 20% más reciente.
    k = int(len(data) * 0.8)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X[:k], y[:k])
    reg = make_pipeline(StandardScaler(), Ridge()).fit(X[:k], ym[:k])
    acc = clf.score(X[k:], y[k:])
    base = float(max(y[k:].mean(), 1 - y[k:].mean()))   # acierto de "siempre gana el local"
    mae = float(np.mean(np.abs(reg.predict(X[k:]) - ym[k:])))

    # modelo de producción: reentreno con TODO el histórico.
    clf_full = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X, y)
    reg_full = make_pipeline(StandardScaler(), Ridge()).fit(X, ym)
    _DIR_DATOS.mkdir(parents=True, exist_ok=True)
    joblib.dump({"clf": clf_full, "reg": reg_full, "feats": _FEATS,
                 "seasons": seasons, "n": len(data)}, _RUTA_MODELO)

    return {"n": len(data), "acierto": acc, "base_local": base, "mae_margen": mae}


# ---------------------------------------------------------------------------
# predicción
# ---------------------------------------------------------------------------

def _stats_actuales(season: str) -> dict:
    """Rasgos actuales de cada equipo (abbr -> dict) con TODOS sus partidos."""
    import pandas as pd

    df = pd.DataFrame(_filas_temporada(season))
    df = df[["TEAM_ID", "TEAM_ABBREVIATION", "GAME_DATE", "WL", "PLUS_MINUS"]].dropna()
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values("GAME_DATE")
    out: dict[str, dict] = {}
    for abbr, g in df.groupby("TEAM_ABBREVIATION"):
        pms = g["PLUS_MINUS"].astype(float).tolist()
        wins = (g["WL"] == "W").astype(int).tolist()
        out[abbr] = {
            "net": sum(pms) / len(pms) if pms else 0.0,
            "net10": sum(pms[-10:]) / len(pms[-10:]) if pms else 0.0,
            "wpct": sum(wins) / len(wins) if wins else 0.5,
            "ult_fecha": g["GAME_DATE"].iloc[-1],
        }
    return out


def predecir(local: str, visitante: str, season: str = "2025-26",
             stats: Optional[dict] = None) -> Optional[dict]:
    """Predice un cruce: favorito, probabilidad del local y margen esperado."""
    import joblib

    if not _RUTA_MODELO.exists():
        raise RuntimeError("no hay modelo entrenado; corre entrenar() primero")
    modelo = joblib.load(_RUTA_MODELO)
    stats = stats or _stats_actuales(season)
    h, a = stats.get(local), stats.get(visitante)
    if not h or not a:
        return None

    x = [[h["net"] - a["net"], h["net10"] - a["net10"],
          h["wpct"] - a["wpct"], 0]]   # descanso neutro para un cruce hipotético
    prob_local = float(modelo["clf"].predict_proba(x)[0][1])
    margen = float(modelo["reg"].predict(x)[0])
    favorito = local if prob_local >= 0.5 else visitante
    return {
        "local": local, "visitante": visitante,
        "favorito": favorito,
        "prob_favorito": round(max(prob_local, 1 - prob_local) * 100),
        "prob_local": round(prob_local * 100),
        "margen_esperado": round(abs(margen)),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # fuerzo utf-8 en consolas Windows (cp1252)
    except Exception:
        pass

    if "--entrenar" in sys.argv:
        m = entrenar()
        print(f"\n[prediccion] Entrenado con {m['n']} partidos.")
        print(f"  Acierto del modelo (test temporal): {m['acierto']:.1%}")
        print(f"  Base 'siempre gana el local':        {m['base_local']:.1%}")
        print(f"  Error medio del margen (MAE):        {m['mae_margen']:.1f} puntos")
    elif "--predecir" in sys.argv:
        i = sys.argv.index("--predecir")
        loc, vis = sys.argv[i + 1], sys.argv[i + 2]
        p = predecir(loc, vis)
        print(p)
    else:
        print("uso: --entrenar  |  --predecir LOCAL VISITANTE")
