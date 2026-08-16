import { useState } from "react";

// quiz de UNA pregunta curiosa (solo en modo con-resultados).
export default function Quiz({ quiz }) {
  const [sel, setSel] = useState(null);
  if (!quiz) return null;
  const done = sel !== null;
  const clase = (j) => {
    if (!done) return "opt";
    if (j === quiz.correcta_idx) return "opt ok";
    if (j === sel) return "opt no";
    return "opt";
  };
  return (
    <section className="section"><div className="wrap">
      <span className="kick">Curiosidad</span>
      <h2 className="sec-h2">La pregunta de la noche</h2>
      <div className="q">
        <h3>{quiz.pregunta}</h3>
        <div className="opts">
          {quiz.opciones.map((op, j) => (
            <button key={j} className={clase(j)} disabled={done} onClick={() => setSel(j)}>
              <span className="l">{String.fromCharCode(65 + j)}</span> {op}
            </button>
          ))}
        </div>
        {/* al contestar, revelo la explicación (sin iconos) */}
        {done && quiz.explicacion && <p className="reveal">{quiz.explicacion}</p>}
      </div>
    </div></section>
  );
}
