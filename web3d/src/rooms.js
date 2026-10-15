/** Lado físico de sala/habitación respecto al eje X (fachada en Z−, jardín mirando hacia +Z). */
export const ROOM_SIDE = {
  NEGATIVE_X: "negative-x",
  POSITIVE_X: "positive-x",
};

/**
 * La puerta y la ventana definen el lado de cada estancia.
 * En la vista frontal del visor, +X proyecta a la izquierda de pantalla (puerta/sala).
 */
export function createRoomLayout({ doorCenterX, windowCenterX }) {
  const entrySide = doorCenterX < 0 ? ROOM_SIDE.NEGATIVE_X : ROOM_SIDE.POSITIVE_X;
  const windowSide = windowCenterX < 0 ? ROOM_SIDE.NEGATIVE_X : ROOM_SIDE.POSITIVE_X;

  const livingRange =
    entrySide === ROOM_SIDE.NEGATIVE_X ? [-Infinity, 0] : [0, Infinity];
  const bedroomRange =
    windowSide === ROOM_SIDE.NEGATIVE_X ? [-Infinity, 0] : [0, Infinity];

  const rooms = {
    living: {
      name: "SALA",
      side: entrySide,
      xRange: livingRange,
    },
    bedroom: {
      name: "HABITACIÓN",
      side: windowSide,
      xRange: bedroomRange,
    },
  };

  const layout = {
    rooms,
    entrySide,
    windowSide,
    doorCenterX,
    windowCenterX,
  };

  validateRoomLayout(layout);
  return layout;
}

export function validateRoomLayout(layout) {
  const ok =
    layout.entrySide === layout.rooms.living.side &&
    layout.windowSide === layout.rooms.bedroom.side &&
    layout.entrySide !== layout.windowSide;

  if (!ok) {
    console.error("[SMART ENERGY] Validación sala/puerta fallida:", layout);
  }
  return ok;
}
