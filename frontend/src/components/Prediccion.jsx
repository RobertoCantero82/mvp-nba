import { colorEquipo } from "../teams";

// elijo tinta oscura o blanca según lo claro que sea el color, para que se lea bien.
function textoSobre(hex) {
  const c = hex.replace("#", "");                 // quito la almohadilla
  const r = parseInt(c.slice(0, 2), 16);          // canal rojo
  const g = parseInt(c.slice(2, 4), 16);          // canal verde
  const b = parseInt(c.slice(4, 6), 16);          // canal azul
  const luz = 0.299 * r + 0.587 * g + 0.114 * b;  // luminosidad percibida
  return luz > 150 ? "#1d1d1f" : "#fff";          // color claro -> tinta; oscuro -> blanco
}

// caja "La predicción para mañana": el partido a seguir con la lectura del modelo de ML.
export default function Prediccion({ pred }) {
  if (!pred) return null;                          // si no hay predicción, no pinto nada
  const probLocal = pred.prob_local;               // probabilidad de que gane el local
  const probVis = 100 - probLocal;                 // la del visitante es el complemento
  const cLocal = colorEquipo(pred.local);          // color del equipo local
  const cVis = colorEquipo(pred.visitante);        // color del equipo visitante
  return (
    <div className="reco" style={{ marginTop: "38px" }}>
      <div className="rl">La predicción para mañana</div>
      <div className="rt">{pred.visitante_nombre} <span className="at">@</span> {pred.local_nombre}</div>
      {/* barra dividida: cada mitad crece según su probabilidad, con el color del equipo */}
      <div className="pred-bar">
        <div className="pb-fill" style={{ width: probVis + "%", background: cVis, color: textoSobre(cVis) }}>
          {pred.visitante} {probVis}%
        </div>
        <div className="pb-fill home" style={{ width: probLocal + "%", background: cLocal, color: textoSobre(cLocal) }}>
          {pred.local} {probLocal}%
        </div>
      </div>
      <div className="rd">{pred.texto}</div>
      <div className="pred-note">Pronóstico analítico del Modelo M.V.P. · 67% de acierto histórico · sin apuestas.</div>
    </div>
  );
}
