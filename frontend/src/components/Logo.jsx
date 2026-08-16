// logo de la marca: emblema (balón con gradiente de IA + costuras blancas + chispa
// negra) junto al wordmark "AGENTE M.V.P.". Es SVG, así que se ve nítido a cualquier
// tamaño y pesa nada. Fusiona baloncesto (el balón) con agente de IA (gradiente + chispa).
export default function Logo() {
  return (
    <svg
      className="logo"
      width="168"
      height="40"
      viewBox="0 0 235 58"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Agente M.V.P."
    >
      {/* gradiente naranja -> magenta, estética de producto de IA */}
      <defs>
        <linearGradient id="mvpGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffab4a" />
          <stop offset="0.5" stopColor="#ff5a2c" />
          <stop offset="1" stopColor="#e83f9c" />
        </linearGradient>
      </defs>
      {/* el emblema: balón macizo con costuras blancas y la chispa de IA en negro */}
      <g transform="translate(29,29)">
        <circle r="19" fill="url(#mvpGrad)" />
        <g fill="none" stroke="#fff" strokeWidth="1.8" strokeLinecap="round">
          <path d="M0 -19V19" />
          <path d="M-17 -6Q0 -1 17 -6" />
          <path d="M-17 6Q0 1 17 6" />
        </g>
        {/* chispa de IA (estrella de 4 puntas) en negro, arriba a la derecha */}
        <path
          transform="translate(12,-13) scale(0.32)"
          d="M0 -12C1.3 -5 5 -1.3 12 0C5 1.3 1.3 5 0 12C-1.3 5 -5 1.3 -12 0C-5 -1.3 -1.3 -5 0 -12Z"
          fill="#1d1d1f"
        />
      </g>
      {/* wordmark: "AGENTE" pequeño encima, "M.V.P." grande debajo */}
      <text x="57" y="24" fontFamily="-apple-system, system-ui, sans-serif" fontSize="10" fontWeight="600" letterSpacing="2" fill="#8a8f98">AGENTE</text>
      <text x="57" y="41" fontFamily="-apple-system, system-ui, sans-serif" fontSize="21" fontWeight="800" letterSpacing="-0.5" fill="#1d1d1f">M.V.P.</text>
    </svg>
  );
}
