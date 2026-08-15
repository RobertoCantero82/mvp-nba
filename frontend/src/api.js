// cliente de la API de solo lectura de M.V.P.
// en desarrollo, Vite proxya /api -> http://localhost:8000 (ver vite.config.js).
// en produccion lo puedo sobreescribir con VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL || "/api";

async function _get(ruta) {
  const resp = await fetch(`${BASE}${ruta}`);
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al pedir ${ruta}`);
  }
  return resp.json();
}

export const getJornadas = () => _get("/jornadas");

export const getJornada = (fecha, spoilers) =>
  _get(`/jornada/${fecha}?spoilers=${spoilers ? "true" : "false"}`);

export const getRespuestas = (fecha) => _get(`/jornada/${fecha}/respuestas`);
