import { useEffect, useState } from "react";

// teaser sin spoilers: describe el TIPO de gesta, sin nombre ni cifra.
const TEASER = {
  hito_pts_carrera: "Un veterano entra en un club de leyenda.",
  hito_fg3m_carrera: "Un tirador alcanza una marca histórica de triples.",
  hito_ast_carrera: "Un base entra en la élite histórica de asistencias.",
  hito_reb_carrera: "Un grande llega a una cifra de rebotes de leyenda.",
  anotacion_alta: "Alguien firma una exhibición anotadora de las gordas.",
  festival_triples: "Un jugador se pone a llover triples sin descanso.",
  racha_pts: "Una racha anotadora que no se apaga.",
  racha_fg3m: "Un francotirador que no falla noche tras noche.",
};

// número que cuenta hacia arriba al montar (respeta reduce-motion).
function useCountUp(target) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!target) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { setVal(target); return; }
    let raf, hecho = false;
    const t0 = performance.now(), dur = 1300, ease = (t) => 1 - Math.pow(1 - t, 3);
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / dur);
      setVal(Math.round(target * ease(p)));
      if (p < 1) raf = requestAnimationFrame(tick);
      else hecho = true;
    };
    raf = requestAnimationFrame(tick);
    // salvavidas: si el rAF está pausado (pestaña oculta), aseguro el valor final.
    const fin = setTimeout(() => { if (!hecho) setVal(target); }, dur + 500);
    return () => { cancelAnimationFrame(raf); clearTimeout(fin); };
  }, [target]);
  return val;
}

function HeroTeaser({ portada }) {
  return (
    <section className="hero"><div className="wrap anim">
      <h1>{TEASER[portada.tipo] || "La gesta de la noche."}</h1>
      <p className="lead">Toca «Resultados» (o supera el reto del final) para descubrir quién, cuánto y contra quién.</p>
    </div></section>
  );
}

function HeroFull({ portada }) {
  const target = parseInt(String(portada.numero).replace(/\D/g, ""), 10) || 0;
  const val = useCountUp(target);
  return (
    <section className="hero"><div className="wrap anim">
      {portada.equipo && <div className="kick"><span className="dot" /> {portada.equipo}</div>}
      {target > 0 && <div className="bignum">{val.toLocaleString("es-ES")}</div>}
      {portada.unidad && <div className="unit">{portada.unidad}{portada.contexto ? ` · ${portada.contexto}` : ""}</div>}
      {portada.jugador && <h1>{portada.jugador}.</h1>}
      {portada.titular && <p className="lead">{portada.titular}.</p>}
    </div></section>
  );
}

export default function Hero({ portada }) {
  if (!portada) return null;
  return portada.safe ? <HeroTeaser portada={portada} /> : <HeroFull portada={portada} />;
}
