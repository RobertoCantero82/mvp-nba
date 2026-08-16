import { colorEquipo } from "../teams";

// tira de marcadores estilo retransmision: cada partido con el color del ganador.
export default function Ticker({ partidos }) {
  if (!partidos?.length) return null;
  return (
    <div className="ticker">
      <div className="ticker-row">
        {partidos.map((p) => {
          const gc = colorEquipo(p.ganador);
          const ganaVis = p.ganador === p.visitante;
          const ganaLoc = p.ganador === p.local;
          return (
            <div className="game" key={p.game_id} style={{ "--gc": gc }}>
              <div className={`gline ${ganaVis ? "w" : ""}`}>
                <span className="ab">{p.visitante}</span>
                <span className="pt">{p.pts_visitante}</span>
              </div>
              <div className={`gline ${ganaLoc ? "w" : ""}`}>
                <span className="ab">{p.local}</span>
                <span className="pt">{p.pts_local}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
