import { useState, useEffect } from "react";
import { getJornadas, getJornada } from "./api";
import Hero from "./components/Hero";
import Quiz from "./components/Quiz";
import Cronica from "./components/Cronica";
import SinSpoilers from "./components/SinSpoilers";
import Contrafactual from "./components/Contrafactual";

const _MESES = ["ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic"];
function fechaBonita(iso) {
  const p = String(iso).split("-");
  if (p.length !== 3) return iso;
  return `${Number(p[2])} ${_MESES[Number(p[1]) - 1]} ${p[0]}`;
}

export default function App() {
  const [jornadas, setJornadas] = useState([]);
  const [fecha, setFecha] = useState(null);
  const [spoilers, setSpoilers] = useState(false);   // por defecto: sin spoilers
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
      <div className="orb a" /><div className="orb b" /><div className="orb c" />

      <header className="nav"><div className="wrap">
        <div className="brand">Agente M.V.P.{fecha ? <span>{fechaBonita(fecha)}</span> : null}</div>
        <div className="controls">
          {jornadas.length > 1 && (
            <select value={fecha ?? ""} onChange={(e) => setFecha(e.target.value)}>
              {jornadas.map((j) => <option key={j} value={j}>{fechaBonita(j)}</option>)}
            </select>
          )}
          <div className={`seg ${spoilers ? "results" : ""}`} role="group" aria-label="Modo">
            <div className="seg-ind" />
            <button onClick={() => setSpoilers(false)}>Sin spoilers</button>
            <button onClick={() => setSpoilers(true)}>Resultados</button>
          </div>
        </div>
      </div></header>

      {error && <div className="aviso error">⚠️ {error}</div>}
      {cargando && <div className="aviso">Cargando la jornada…</div>}

      {data && !cargando && (
        <main key={data.modo}>
          <Hero portada={data.portada} />
          {spoilers ? (
            <>
              <Quiz quiz={data.quiz} />
              <Cronica partidos={data.resultados} />
              <Contrafactual cf={data.contrafactual} />
            </>
          ) : (
            <SinSpoilers
              highlights={data.highlights}
              recomendacion={data.recomendacion}
              gate={data.gate}
              onUnlock={() => setSpoilers(true)}
            />
          )}
        </main>
      )}

      <footer>
        Agente M.V.P. — Modelo · Veredicto · Predicción&nbsp;&nbsp;|&nbsp;&nbsp;
        redacción asistida a través de LLM y datos verificados&nbsp;&nbsp;|&nbsp;&nbsp;
        Roberto Cantero
      </footer>
    </div>
  );
}
