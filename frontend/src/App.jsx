import { useState, useEffect } from "react";
import { getJornadas, getJornada } from "./api";
import Hero from "./components/Hero";
import Ticker from "./components/Ticker";
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

function Contrafactual({ cf }) {
  if (!cf) return null;
  const [lo, hi] = cf.rango_esperado;
  return (
    <section className="sec cf-sec anim" style={{ animationDelay: "0.24s" }}>
      <span className="eyebrow">¿Qué hubiera pasado?</span>
      <h2 className="sec-h2">El terremoto de la noche</h2>
      <div className="cf">
        <div className="cf-z">{cf.z}σ</div>
        <div className="cf-txt">
          <div className="cf-who">{cf.jugador} · {cf.equipo}</div>
          <Parrafos texto={cf.texto} />
          <span className="cf-range">
            media {cf.media} · esperado {lo}–{hi} · real {cf.pts_noche}
          </span>
        </div>
      </div>
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
      <header className="top">
        <div className="brand">
          <span className="logo">M.V.P<b>.</b></span>
          <span className="claim">Analista NBA</span>
        </div>
        <div className="controls">
          {jornadas.length > 1 && (
            <select value={fecha ?? ""} onChange={(e) => setFecha(e.target.value)}>
              {jornadas.map((j) => (
                <option key={j} value={j}>{fechaBonita(j)}</option>
              ))}
            </select>
          )}
          <div className="toggle" role="group" aria-label="Modo de spoilers">
            <button className={!spoilers ? "on" : ""} onClick={() => setSpoilers(false)}>
              🙈 Sin spoilers
            </button>
            <button className={spoilers ? "on" : ""} onClick={() => setSpoilers(true)}>
              👁 Con resultados
            </button>
          </div>
        </div>
      </header>

      {error && <div className="aviso error">⚠️ {error} · ¿está el backend / los datos en su sitio?</div>}
      {cargando && <div className="aviso">Cargando la jornada…</div>}

      {data && !cargando && (
        <main key={`${data.fecha}-${data.modo}`}>
          <Hero portada={data.portada} fecha={fechaBonita(data.fecha)} />

          {spoilers && data.resultados && (
            <div className="anim" style={{ animationDelay: "0.06s" }}>
              <Ticker partidos={data.resultados} />
            </div>
          )}

          <section className="cronica anim" style={{ animationDelay: "0.12s" }}>
            <div className="cronica-in">
              <span className="eyebrow">Crónica de la jornada</span>
              <h2 className="cronica-h2">La crónica de la noche</h2>
              <div className="rule" />
              <Parrafos texto={data.analisis} />
            </div>
          </section>

          <section className="sec anim" style={{ animationDelay: "0.18s" }}>
            <Quiz fecha={data.fecha} quiz={data.quiz} />
          </section>

          {spoilers ? (
            <Contrafactual cf={data.contrafactual} />
          ) : (
            <p className="nota-omitido">
              🔒 La pieza «qué hubiera pasado» se desbloquea con los resultados: un
              contrafactual no puede existir sin desvelar antes lo que pasó de verdad.
            </p>
          )}
        </main>
      )}

      <footer className="pie">
        Datos vía nba_api · redacción asistida por IA con cifras verificadas ·
        cero apuestas, cero cifras inventadas
      </footer>
    </div>
  );
}
