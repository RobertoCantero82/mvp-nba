// "lo que nadie vio venir": barra visual de lo esperado vs lo real.
export default function Contrafactual({ cf }) {
  if (!cf) return null;
  const [lo, hi] = cf.rango_esperado;
  const media = Math.round(cf.media);
  const max = Math.max(cf.pts_noche, hi) * 1.18;
  const pct = (v) => (v / max) * 100;
  return (
    <section className="section"><div className="wrap">
      <span className="kick">La rareza de la noche</span>
      <h2 className="sec-h2">Lo que nadie vio venir.</h2>
      <div className="panel">
        <div className="cf-top">
          <span className="cf-who">{cf.jugador} · {cf.equipo}</span>
          <span className="cf-tag">el dato más raro de la jornada</span>
        </div>
        <div className="cf-line">
          Se esperaban unos <b>{media}</b> puntos suyos. Hizo <b>{cf.pts_noche}</b>.
        </div>
        <div className="track">
          <div className="axis" />
          <div className="band" style={{ left: pct(lo) + "%", width: (pct(hi) - pct(lo)) + "%" }} />
          <div className="avg" style={{ left: pct(cf.media) + "%" }} />
          <div className="real" style={{ left: pct(cf.pts_noche) + "%" }} />
          <div className="lab real-lab" style={{ left: pct(cf.pts_noche) + "%" }}>{cf.pts_noche} · real</div>
          <div className="lab exp-lab" style={{ left: pct((lo + hi) / 2) + "%", transform: "translateX(-50%)" }}>
            lo normal: {lo}–{hi}
          </div>
        </div>
        {cf.texto && <div className="cf-foot">{cf.texto}</div>}
      </div>
    </div></section>
  );
}
