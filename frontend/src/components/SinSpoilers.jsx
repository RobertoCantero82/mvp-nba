import { useState } from "react";

// candado: acertar la trivia desbloquea; fallar deja reintentar o ver igualmente.
function Gate({ gate, onUnlock }) {
  const [wrong, setWrong] = useState(null);
  const [done, setDone] = useState(false);
  if (!gate) return null;
  const tried = wrong !== null;
  const click = (j) => {
    if (done) return;
    if (j === gate.correcta_idx) {
      setDone(true);
      setTimeout(onUnlock, 480);
    } else {
      setWrong(j);
    }
  };
  const clase = (j) => {
    if (done && j === gate.correcta_idx) return "opt ok";
    if (j === wrong) return "opt no";
    return "opt";
  };
  return (
    <div className="gate">
      <div className="gate-lock">🔒</div>
      <div className="gate-t">¿Te ganas los resultados?</div>
      <div className="gate-sub">
        Acierta esta y te desbloqueo marcadores, la crónica partido a partido y «lo que nadie vio venir».
      </div>
      <div className="gate-q">{gate.pregunta}</div>
      <div className="opts">
        {gate.opciones.map((op, j) => (
          <button key={j} className={clase(j)} disabled={done} onClick={() => click(j)}>
            <span className="l">{String.fromCharCode(65 + j)}</span> {op}
          </button>
        ))}
      </div>
      {tried && !done && (
        <>
          <p className="msg">¡Casi! {gate.explicacion} Puedes reintentar…</p>
          <button className="gate-skip" onClick={onUnlock}>…o ver los resultados igualmente →</button>
        </>
      )}
    </div>
  );
}

export default function SinSpoilers({ highlights, recomendacion, gate, onUnlock }) {
  return (
    <section className="section"><div className="wrap">
      <span className="kick">Lo más destacado</span>
      <h2 className="sec-h2">Lo más destacado de la noche.</h2>
      <div className="hl">
        {(highlights || []).map((h, i) => <div className="hl-item" key={i}>{h}</div>)}
      </div>
      {recomendacion && (
        <div className="reco">
          <div className="rl">▶ No te pierdas</div>
          <div className="rt">{recomendacion.partido}</div>
          <div className="rd">{recomendacion.texto}</div>
        </div>
      )}
      <Gate gate={gate} onUnlock={onUnlock} />
    </div></section>
  );
}
