// cliente ESTATICO: leo el contenido ya generado desde archivos JSON incluidos en
// la propia web (carpeta data/), sin backend. la logica de spoilers y del quiz
// corre en el navegador, asi la web es 100% estatica y se despliega gratis.
// (el backend FastAPI sigue existiendo para uso local; aqui no hace falta.)
const BASE = import.meta.env.BASE_URL || "/";

async function _cargarContenido(fecha) {
  const resp = await fetch(`${BASE}data/contenido_${fecha}.json`);
  if (!resp.ok) throw new Error(`no encuentro el contenido de la jornada ${fecha}`);
  return resp.json();
}

// listado de jornadas disponibles (lo genero al construir la web).
export async function getJornadas() {
  const resp = await fetch(`${BASE}data/manifest.json`);
  if (!resp.ok) throw new Error("no encuentro el listado de jornadas");
  return resp.json();
}

// replico el moldeado que hacia el backend: version con-resultados / sin-spoilers.
function _moldear(c, spoilers) {
  const p = c.portada;
  return {
    fecha: c.fecha,
    modo: spoilers ? "con_resultados" : "sin_spoilers",
    // portada: completa con resultados; sin spoilers solo el tipo (sin nombre ni cifra).
    portada: p ? (spoilers ? p : { tipo: p.tipo, unidad: p.unidad, safe: true }) : null,
    quiz: {
      intro: c.quiz?.intro ?? "",
      // no expongo la respuesta correcta en las opciones (se pide aparte al comprobar).
      preguntas: (c.quiz?.preguntas ?? []).map((q) => ({
        pregunta: q.pregunta,
        opciones: q.opciones,
      })),
    },
    // los marcadores son spoilers: solo en la version con-resultados.
    resultados: spoilers ? c.resultados ?? null : null,
    analisis: spoilers
      ? c.analisis?.con_resultados ?? ""
      : c.analisis?.sin_spoilers ?? "",
    contrafactual: spoilers ? c.contrafactual ?? null : null,
  };
}

export async function getJornada(fecha, spoilers) {
  return _moldear(await _cargarContenido(fecha), spoilers);
}

// respuestas del quiz (revelado opt-in: solo las leo al comprobar).
export async function getRespuestas(fecha) {
  const c = await _cargarContenido(fecha);
  return {
    fecha,
    respuestas: (c.quiz?.preguntas ?? []).map((p) => ({
      pregunta: p.pregunta,
      correcta: p.correcta,
      correcta_idx: p.correcta_idx,
      explicacion: p.explicacion,
    })),
  };
}
