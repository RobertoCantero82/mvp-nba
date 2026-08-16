import { colorEquipo } from "../teams";

// etiqueta corta (eyebrow) segun el tipo de hito de portada.
const LABEL = {
  hito_pts_carrera: "Hito histórico",
  hito_fg3m_carrera: "Hito histórico",
  hito_ast_carrera: "Hito histórico",
  hito_reb_carrera: "Hito histórico",
  anotacion_alta: "Exhibición anotadora",
  festival_triples: "Lluvia de triples",
  racha_pts: "Racha viva",
  racha_fg3m: "Racha viva",
};

// titular sin spoilers: describe el TIPO de gesta, sin desvelar quién ni cuánto.
const TEASER = {
  hito_pts_carrera: "Un veterano entró en un club que muy pocos han pisado",
  hito_fg3m_carrera: "Un tirador alcanzó una marca histórica de triples",
  hito_ast_carrera: "Un base se metió en la élite histórica de asistencias",
  hito_reb_carrera: "Un grande llegó a una cifra de rebotes de leyenda",
  anotacion_alta: "Alguien firmó una exhibición anotadora de las gordas",
  festival_triples: "Un jugador se puso a llover triples sin descanso",
  racha_pts: "Una racha anotadora que no se apaga",
  racha_fg3m: "Un francotirador encadena noche tras noche",
};

export default function Hero({ portada, fecha }) {
  if (!portada) return null;
  const label = LABEL[portada.tipo] || "La noche";

  // version sin spoilers: nada de nombre, equipo ni cifra.
  if (portada.safe) {
    return (
      <section className="hero" style={{ "--team": "var(--flame)" }}>
        <div className="hero-in">
          <span className="eyebrow">{label} · {fecha}</span>
          <h1 className="hero-titular">{TEASER[portada.tipo] || "La gesta de la noche"}</h1>
          <p className="hero-sub">
            Activa <b>«Con resultados»</b> para descubrir quién, cuánto y contra quién.
          </p>
        </div>
      </section>
    );
  }

  const color = colorEquipo(portada.equipo);
  return (
    <section className="hero" style={{ "--team": color }}>
      <div className="hero-in">
        <div className="hero-kicker">
          <span className="eyebrow">{label} · {fecha}</span>
          {portada.equipo && <span className="team-chip">{portada.equipo}</span>}
        </div>
        {portada.numero && <div className="bignum">{portada.numero}</div>}
        {portada.jugador && <h1 className="hero-name">{portada.jugador}</h1>}
        {portada.unidad && <div className="hero-unit">{portada.unidad}</div>}
        {portada.contexto && <span className="rank">{portada.contexto}</span>}
        <p className="hero-sub">{portada.titular}</p>
      </div>
    </section>
  );
}
