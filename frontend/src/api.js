// cliente ESTATICO: leo el contenido ya generado desde archivos JSON incluidos en
// la propia web (carpeta data/), sin backend. la lógica de spoilers corre en el
// navegador, así la web es 100% estática y se despliega gratis.
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

// moldeo el contenido según el modo: con-resultados / sin-spoilers.
function _moldear(c, spoilers) {
  const p = c.portada;
  return {
    fecha: c.fecha,
    modo: spoilers ? "con_resultados" : "sin_spoilers",
    // portada: completa con resultados; sin spoilers solo el tipo (teaser, sin cifra).
    portada: p ? (spoilers ? p : { tipo: p.tipo, unidad: p.unidad, safe: true }) : null,
    // solo con resultados:
    resultados: spoilers ? (c.resultados ?? null) : null,
    quiz: spoilers ? (c.quiz ?? null) : null,
    contrafactual: spoilers ? (c.contrafactual ?? null) : null,
    // solo sin spoilers:
    highlights: spoilers ? null : (c.highlights ?? []),
    recomendacion: spoilers ? null : (c.recomendacion ?? null),
    gate: spoilers ? null : (c.gate ?? null),
  };
}

export async function getJornada(fecha, spoilers) {
  return _moldear(await _cargarContenido(fecha), spoilers);
}
