import { useState, useEffect } from "react";
import { getRespuestas } from "../api";

// quiz jugable. las opciones llegan sin la respuesta correcta; solo al enviar
// pido /respuestas para puntuar y revelar (revelado opt-in: en sin-spoilers,
// cargar la jornada nunca desvela resultados).
export default function Quiz({ fecha, quiz }) {
  const [seleccion, setSeleccion] = useState({});
  const [respuestas, setRespuestas] = useState(null);
  const [cargando, setCargando] = useState(false);

  // reinicio el quiz al cambiar de jornada.
  useEffect(() => {
    setSeleccion({});
    setRespuestas(null);
  }, [fecha]);

  if (!quiz || !quiz.preguntas?.length) return null;

  const enviado = respuestas !== null;
  const total = quiz.preguntas.length;
  const contestadas = Object.keys(seleccion).length;
  const idxCorrecta = (i) => respuestas?.respuestas?.[i]?.correcta_idx ?? null;
  const aciertos = enviado
    ? quiz.preguntas.reduce((n, _, i) => n + (seleccion[i] === idxCorrecta(i) ? 1 : 0), 0)
    : 0;

  async function comprobar() {
    setCargando(true);
    try {
      setRespuestas(await getRespuestas(fecha));
    } finally {
      setCargando(false);
    }
  }

  function claseOpcion(i, j) {
    if (!enviado) return seleccion[i] === j ? "opt sel" : "opt";
    if (j === idxCorrecta(i)) return "opt ok";
    if (seleccion[i] === j) return "opt no";
    return "opt";
  }

  return (
    <>
      <span className="eyebrow">Pon a prueba tu memoria</span>
      <h2 className="sec-h2">Quiz de la jornada</h2>
      {quiz.intro && <p className="quiz-intro">{quiz.intro}</p>}

      {quiz.preguntas.map((p, i) => (
        <div className={`q ${enviado ? "done" : ""}`} key={i}>
          <h3>{i + 1}. {p.pregunta}</h3>
          <div className="opts">
            {p.opciones.map((op, j) => (
              <button
                key={j}
                className={claseOpcion(i, j)}
                disabled={enviado}
                onClick={() => setSeleccion((prev) => ({ ...prev, [i]: j }))}
              >
                <span className="l">{String.fromCharCode(65 + j)}</span>
                {op}
              </button>
            ))}
          </div>
          {enviado && respuestas.respuestas[i]?.explicacion && (
            <p className="reveal">💡 {respuestas.respuestas[i].explicacion}</p>
          )}
        </div>
      ))}

      {!enviado ? (
        <button className="quiz-btn" disabled={contestadas < total || cargando} onClick={comprobar}>
          {contestadas < total
            ? `Responde las ${total} (${contestadas}/${total})`
            : cargando ? "Comprobando…" : "Comprobar respuestas"}
        </button>
      ) : (
        <div className="quiz-result">
          Has acertado <strong>{aciertos}</strong> de <strong>{total}</strong>.{" "}
          {aciertos === total
            ? "Perfecto. ¿Seguro que no jugaste tú la jornada?"
            : aciertos === 0
            ? "Cero. Al menos la constancia es admirable."
            : "Ni tan mal. La NBA no se lee solo en el marcador."}
        </div>
      )}
    </>
  );
}
