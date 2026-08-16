import { colorEquipo } from "../teams";

// crónica partido a partido: marcador (ganador en su color) + línea de análisis.
export default function Cronica({ partidos }) {
  if (!partidos?.length) return null;
  return (
    <section className="section"><div className="wrap">
      <span className="kick">Resultados + análisis</span>
      <h2 className="sec-h2">La jornada, partido a partido.</h2>
      <div className="games">
        {partidos.map((p) => {
          const gc = colorEquipo(p.ganador);
          const ganaVis = p.ganador === p.visitante;
          const ganaLoc = p.ganador === p.local;
          return (
            <div className="grow" key={p.game_id}>
              <div className="gr-sc">
                <span style={ganaVis ? { color: gc, fontWeight: 800 } : undefined}>
                  {p.visitante} {p.pts_visitante}
                </span>
                {" · "}
                <span style={ganaLoc ? { color: gc, fontWeight: 800 } : undefined}>
                  {p.local} {p.pts_local}
                </span>
              </div>
              <div className="gr-note">{p.analisis}</div>
            </div>
          );
        })}
      </div>
    </div></section>
  );
}
