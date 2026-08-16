import { useState } from "react";
import Prediccion from "./Prediccion";

// el reto (candado): si aciertas la trivia desbloqueo los resultados; si fallas,
// puedes reintentar o verlos igualmente (nunca dejo al usuario atrapado).
function Gate({ gate, onUnlock }) {
  const [wrong, setWrong] = useState(null);   // índice de la opción fallada (o null)
  const [done, setDone] = useState(false);    // true cuando ya ha acertado
  if (!gate) return null;
  const tried = wrong !== null;               // ¿ha fallado al menos una vez?
  const click = (j) => {                       // al pulsar una opción...
    if (done) return;                          // si ya acertó, ignoro
    if (j === gate.correcta_idx) {             // acierto:
      setDone(true);                           // lo marco como resuelto
      setTimeout(onUnlock, 480);               // y desbloqueo tras un instante
    } else {
      setWrong(j);                             // fallo: recuerdo cuál falló
    }
  };
  const clase = (j) => {                        // clase css de cada opción según el estado
    if (done && j === gate.correcta_idx) return "opt ok";
    if (j === wrong) return "opt no";
    return "opt";
  };
  return (
    <div className="gate" style={{ marginTop: "38px" }}>
      <div className="rl">El reto</div>
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
      {tried && !done && (   // solo tras fallar: mensaje + salida "ver igualmente"
        <>
          <p className="msg">¡Casi! {gate.explicacion} Puedes reintentar…</p>
          <button className="gate-skip" onClick={onUnlock}>…o ver los resultados igualmente</button>
        </>
      )}
    </div>
  );
}

// vista sin spoilers: destacados + recomendación + predicción de mañana + el reto.
export default function SinSpoilers({ highlights, recomendacion, prediccion, gate, onUnlock }) {
  return (
    <section className="section"><div className="wrap">
      <span className="kick">Lo más destacado</span>
      <h2 className="sec-h2">Lo más destacado de la noche.</h2>
      {/* lista de gestas en clave sin-spoiler (sin nombres ni marcadores) */}
      <div className="hl">
        {(highlights || []).map((h, i) => <div className="hl-item" key={i}>{h}</div>)}
      </div>
      {/* recomendación de un partido de esta noche para ver en diferido, sin destripar */}
      {recomendacion && (
        <div className="reco">
          <div className="rl">No te pierdas</div>
          <div className="rt">{recomendacion.partido}</div>
          <div className="rd">{recomendacion.texto}</div>
        </div>
      )}
      {/* predicción de ML del partido a seguir de mañana */}
      <Prediccion pred={prediccion} />
      {/* el reto para desbloquear los resultados */}
      <Gate gate={gate} onUnlock={onUnlock} />
    </div></section>
  );
}
