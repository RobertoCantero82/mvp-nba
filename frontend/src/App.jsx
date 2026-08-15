import { useState, useEffect } from "react";
import { getJornadas, getJornada } from "./api";
import Quiz from "./components/Quiz";

// convierto '2026-02-26' en '26 feb 2026' para mostrarlo mas humano.
const _MESES = ["ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic"];
function fechaBonita(iso) {
  const p = String(iso).split("-");
  if (p.length !== 3) return iso;
  return `${Number(p[2])} ${_MESES[Number(p[1]) - 1]} ${p[0]}`;
}

// renderizo un bloque de texto (con saltos dobles) como parrafos.
function Parrafos({ texto }) {
  if (!texto) return null;
  return texto
    .split(/\n{2,}|\n/)
    .filter((p) => p.trim())
    .map((p, i) => <p key={i}>{p.trim()}</p>);
}

// color principal de cada franquicia, para dar aire de retransmision al marcador.
const COLOR_EQUIPO = {
  ATL: "#E03A3E", BOS: "#1FA67A", BKN: "#B0B4BC", CHA: "#00788C", CHI: "#CE1141",
  CLE: "#C8102E", DAL: "#0053BC", DEN: "#FEC524", DET: "#EF3B50", GSW: "#1D69C4",
  HOU: "#CE1141", IND: "#FDBB30", LAC: "#EF3B50", LAL: "#B98CE8", MEM: "#5D76A9",
  MIA: "#F9155E", MIL: "#2ECC8B", MIN: "#4FA3E0", NOP: "#C8A96A", NYK: "#F58426",
  OKC: "#00A2E8", ORL: "#0B77C0", PHI: "#3C7DD6", PHX: "#E56020", POR: "#EF3B50",
  SAC: "#8E6CC0", SAS: "#C4CED4", TOR: "#E03A46", UTA: "#F9A01B", WAS: "#3C6DF0",
};

function Resultados({ partidos }) {
  if (!partidos?.length) return null;
  return (
    <section className="tarjeta resultados">
      <h2>🏆 Resultados de la jornada</h2>
      <div className="marcadores">
        {partidos.map((p) => {
          const ganaVis = p.ganador === p.visitante;
          const ganaLoc = p.ganador === p.local;
          const colorGanador = COLOR_EQUIPO[p.ganador] || "var(--acento)";
          return (
            <div
              className="marcador"
              key={p.game_id}
              style={{ borderLeftColor: colorGanador }}
            >
              <div className={`equipo ${ganaVis ? "gana" : ""}`}>
                <span className="abbr">{p.visitante}</span>
                <span
                  className="pts"
                  style={ganaVis ? { color: colorGanador, textShadow: `0 0 14px ${colorGanador}88` } : undefined}
                >
                  {p.pts_visitante}
                </span>
              </div>
              <div className={`equipo ${ganaLoc ? "gana" : ""}`}>
                <span className="abbr">{p.local}</span>
                <span
                  className="pts"
                  style={ganaLoc ? { color: colorGanador, textShadow: `0 0 14px ${colorGanador}88` } : undefined}
                >
                  {p.pts_local}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Contrafactual({ cf }) {
  if (!cf) return null;
  const [lo, hi] = cf.rango_esperado;
  return (
    <section className="tarjeta contrafactual">
      <h2>🔮 Qué hubiera pasado</h2>
      <div className="cf-datos">
        <div>
          <span className="cf-num">{cf.pts_noche}</span>
          <span className="cf-lab">puntos esta noche</span>
        </div>
        <div>
          <span className="cf-num">
            {lo}–{hi}
          </span>
          <span className="cf-lab">rango esperado</span>
        </div>
        <div>
          <span className="cf-num">{cf.z}σ</span>
          <span className="cf-lab">de desviación</span>
        </div>
      </div>
      <Parrafos texto={cf.texto} />
    </section>
  );
}

export default function App() {
  const [jornadas, setJornadas] = useState([]);
  const [fecha, setFecha] = useState(null);
  const [spoilers, setSpoilers] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    getJornadas()
      .then((js) => {
        // ordeno por fecha descendente: la mas reciente es siempre la portada.
        const orden = [...js].sort((a, b) => b.localeCompare(a));
        setJornadas(orden);
        if (orden.length) setFecha(orden[0]);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!fecha) return;
    setCargando(true);
    setError(null);
    getJornada(fecha, spoilers)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [fecha, spoilers]);

  return (
    <div className="app">
      <header className="cabecera">
        <div className="marca">
          <span className="logo">M.V.P.</span>
          <span className="claim">Analista NBA · métricas, verificación, publicación</span>
        </div>
        <div className="controles">
          {jornadas.length > 1 && (
            <select value={fecha ?? ""} onChange={(e) => setFecha(e.target.value)}>
              {jornadas.map((j) => (
                <option key={j} value={j}>
                  {fechaBonita(j)}
                </option>
              ))}
            </select>
          )}
          <div className="toggle" role="group" aria-label="Modo de spoilers">
            <button
              className={!spoilers ? "activo" : ""}
              onClick={() => setSpoilers(false)}
            >
              🙈 Sin spoilers
            </button>
            <button
              className={spoilers ? "activo" : ""}
              onClick={() => setSpoilers(true)}
            >
              👁 Con resultados
            </button>
          </div>
        </div>
      </header>

      <main className="contenido">
        {error && <div className="aviso error">⚠️ {error} · ¿Está el backend en marcha?</div>}
        {cargando && <div className="aviso">Cargando la jornada…</div>}

        {data && !cargando && (
          <>
            <div className="titulo-jornada">
              <h1>Jornada del {fechaBonita(data.fecha)}</h1>
              <span className={`chip ${spoilers ? "chip-spoil" : "chip-safe"}`}>
                {spoilers ? "Con resultados" : "Sin spoilers"}
              </span>
            </div>

            <Quiz fecha={data.fecha} quiz={data.quiz} />

            {spoilers && <Resultados partidos={data.resultados} />}

            <section className="tarjeta analisis">
              <h2>📰 Análisis de la jornada</h2>
              <Parrafos texto={data.analisis} />
            </section>

            {spoilers ? (
              <Contrafactual cf={data.contrafactual} />
            ) : (
              <p className="nota-omitido">
                🔒 La pieza «qué hubiera pasado» se desbloquea con los resultados: un
                contrafactual no puede existir sin desvelar antes lo que pasó de verdad.
              </p>
            )}
          </>
        )}
      </main>

      <footer className="pie">
        Datos vía nba_api · redacción asistida por IA con cifras verificadas ·
        cero apuestas, cero cifras inventadas.
      </footer>
    </div>
  );
}
