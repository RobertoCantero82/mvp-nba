// color principal de cada franquicia, para el puntito del ganador en los marcadores.
export const COLOR_EQUIPO = {
  ATL: "#E03A3E", BOS: "#1FA67A", BKN: "#B0B4BC", CHA: "#00A2C7", CHI: "#CE1141",
  CLE: "#C8102E", DAL: "#0053BC", DEN: "#FEC524", DET: "#EF3B50", GSW: "#1D69C4",
  HOU: "#CE1141", IND: "#FDBB30", LAC: "#5A6C82", LAL: "#8E6CC0", MEM: "#5D9CEC",
  MIA: "#C0417A", MIL: "#2ECC8B", MIN: "#236192", NOP: "#C8102E", NYK: "#F58426",
  OKC: "#00A2E8", ORL: "#0B77C0", PHI: "#006BB6", PHX: "#E56020", POR: "#D4453D",
  SAC: "#5A2D81", SAS: "#6B7078", TOR: "#E03A46", UTA: "#F9A01B", WAS: "#3C6DF0",
};

export const colorEquipo = (abbr) => COLOR_EQUIPO[abbr] || "var(--accent)";
