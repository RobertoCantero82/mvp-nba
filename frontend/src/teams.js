// color principal de cada franquicia, para dar aire de retransmision a la web.
export const COLOR_EQUIPO = {
  ATL: "#E03A3E", BOS: "#1FA67A", BKN: "#B0B4BC", CHA: "#00A9E0", CHI: "#CE1141",
  CLE: "#C8102E", DAL: "#0053BC", DEN: "#FEC524", DET: "#EF3B50", GSW: "#1D69C4",
  HOU: "#CE1141", IND: "#FDBB30", LAC: "#EF3B50", LAL: "#B98CE8", MEM: "#5D9CEC",
  MIA: "#F9155E", MIL: "#2ECC8B", MIN: "#4FA3E0", NOP: "#C8102E", NYK: "#F58426",
  OKC: "#00A2E8", ORL: "#0B77C0", PHI: "#3C7DD6", PHX: "#E56020", POR: "#EF3B50",
  SAC: "#8E6CC0", SAS: "#C4CED4", TOR: "#E03A46", UTA: "#F9A01B", WAS: "#3C6DF0",
};

export const colorEquipo = (abbr) => COLOR_EQUIPO[abbr] || "var(--flame)";
