import { useState, useEffect } from "react";
import { getRespuestas } from "../api";

// quiz jugable. las opciones llegan sin la respuesta correcta; solo al enviar
// pido /respuestas al backend para puntuar y revelar (revelado opt-in: en
// modo sin-spoilers, cargar la jornada nunca desvela resultados).
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

  const idxCorrecta = (i) =>
    respuestas?.respuestas?.[i]?.correcta_idx ?? null;

  const aciertos = enviado
    ? quiz.preguntas.reduce(
        (n, _, i) => n + (seleccion[i] === idxCorrecta(i) ? 1 : 0),
        0
      )
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
    if (!enviado) return seleccion[i] === j ? "opcion elegida" : "opcion";
    if (j === idxCorrecta(i)) return "opcion correcta";
    if (seleccion[i] === j) return "opcion fallada";
    return "opcion";
  }

  return (
    <section className="tarjeta quiz">
      <h2>🏀 Quiz de la jornada</h2>
      {quiz.intro && <p className="intro">{quiz.intro}</p>}

      {quiz.preguntas.map((p, i) => (
        <div className="pregunta" key={i}>
          <h3>
            {i + 1}. {p.pregunta}
          </h3>
          <div className="opciones">
            {p.opciones.map((op, j) => (
              <button
                key={j}
                className={claseOpcion(i, j)}
                disabled={enviado}
                onClick={() => setSeleccion({ ...seleccion, [i]: j })}
              >
                <span className="letra">{String.fromCharCode(65 + j)}</span>
                {op}
              </button>
            ))}
          </div>
          {enviado && respuestas.respuestas[i]?.explicacion && (
            <p className="explicacion">💡 {respuestas.respuestas[i].explicacion}</p>
          )}
        </div>
      ))}

      {!enviado ? (
        <button
          className="boton-principal"
          disabled={contestadas < total || cargando}
          onClick={comprobar}
        >
          {contestadas < total
            ? `Responde las ${total} (${contestadas}/${total})`
            : cargando
            ? "Comprobando…"
            : "Comprobar respuestas"}
        </button>
      ) : (
        <div className="resultado">
          Has acertado <strong>{aciertos}</strong> de <strong>{total}</strong>.{" "}
          {aciertos === total
            ? "Perfecto. ¿Seguro que no jugaste tú la jornada?"
            : aciertos === 0
            ? "Cero. Al menos la constancia es admirable."
            : "Ni tan mal. La NBA no se lee solo en el marcador."}
        </div>
      )}
    </section>
  );
}
