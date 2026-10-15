import * as THREE from "three";
import {
  createArduinoUno,
  createBreadboard,
  createBuzzer,
  createDupontCable,
  createFan,
  createIna219,
  createLed,
  createLm2596,
  createLcd,
  createServo,
  createUltrasonicSensor,
} from "./components.js";

/**
 * Coordenadas (cm), origen en el centro del suelo:
 *  +X derecha, +Y arriba, +Z fondo. Fachada en Z = -HALF_D.
 *  Puerta en X negativo (izquierda al mirar desde +Z).
 */
export const W = 35;
export const D = 25;
export const HALF_W = W / 2;
export const HALF_D = D / 2;
const WALL_H = 18;
const WALL_T = 0.7;
const BASE_H = 1.5;
const PLATE_H = 0.35;
const EAVE = 1.05;
const ROOF_TH = 0.42;
export const Y_WALL_BOT = BASE_H + PLATE_H;
export const Y_WALL_TOP = Y_WALL_BOT + WALL_H;
export const Y_RIDGE = Y_WALL_TOP + 3.35;

const ENTRY_X1 = -8.5;
const SALA_X1 = 4.5;
const TECH_X0 = 12.5;
const INNER_Z = -4.5;

function matCardboard(color, opts = {}) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.9,
    metalness: 0.03,
    transparent: false,
    opacity: 1,
    depthWrite: true,
    ...opts,
  });
}

function meshBox(w, h, d, material) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function wallBox(group, x, y, z, w, h, d, material) {
  const m = meshBox(w, h, d, material);
  m.position.set(x, y, z);
  group.add(m);
  return m;
}

function roofHalf(sign, material, darkMaterial) {
  const run = HALF_W + EAVE;
  const rise = Y_RIDGE - Y_WALL_TOP;
  const slopeLen = Math.hypot(run, rise);
  const angle = Math.atan2(rise, run);
  const depth = D + EAVE * 2;
  const geom = new THREE.BoxGeometry(slopeLen, ROOF_TH, depth);
  const panel = new THREE.Mesh(geom, sign > 0 ? material : darkMaterial);
  panel.castShadow = true;
  panel.receiveShadow = true;
  const cx = sign * run * 0.5;
  const cy = Y_WALL_TOP + rise * 0.5;
  panel.position.set(cx, cy, 0);
  panel.rotation.z = -sign * angle;
  return panel;
}

function gableEnd(z, material) {
  const geom = new THREE.BufferGeometry();
  const verts = new Float32Array([
    -HALF_W - EAVE, Y_WALL_TOP, z,
    HALF_W + EAVE, Y_WALL_TOP, z,
    0, Y_RIDGE, z,
  ]);
  geom.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  geom.computeVertexNormals();
  const m = new THREE.Mesh(geom, material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function glassMat() {
  return matCardboard(0x3d6a8c, {
    roughness: 0.25,
    metalness: 0.05,
    transparent: true,
    opacity: 0.68,
    depthWrite: true,
  });
}

function addWindowFrame(group, cx, cy, w, h, depth, z, woodMat, glass, innerTrim = null) {
  const t = 0.38;
  const trim = innerTrim || woodMat;
  wallBox(group, cx, cy + h / 2 - t / 2, z, w, t, depth, woodMat);
  wallBox(group, cx, cy - h / 2 + t / 2, z, w, t, depth, woodMat);
  wallBox(group, cx - w / 2 + t / 2, cy, z, t, h, depth, woodMat);
  wallBox(group, cx + w / 2 - t / 2, cy, z, t, h, depth, woodMat);
  const iw = w - t * 2.4;
  const ih = h - t * 2.4;
  wallBox(group, cx, cy, z + depth * 0.08, iw, ih, depth * 0.12, trim);
  const pane = meshBox(iw - 0.15, ih - 0.15, depth * 0.22, glass);
  pane.position.set(cx, cy, z + depth * 0.2);
  group.add(pane);
  return pane;
}

function addPlant(group, x, z, scale = 1) {
  const pot = meshBox(1.4 * scale, 1.1 * scale, 1.4 * scale, matCardboard(0x6b4f2a));
  pot.position.set(x, Y_WALL_BOT - 0.55 * scale, z);
  group.add(pot);
  const soil = meshBox(1.2 * scale, 0.15 * scale, 1.2 * scale, matCardboard(0x3d2e1f));
  soil.position.set(x, Y_WALL_BOT + 0.05 * scale, z);
  group.add(soil);
  const bush = new THREE.Mesh(
    new THREE.SphereGeometry(0.9 * scale, 8, 6),
    matCardboard(0x2d6a3a),
  );
  bush.position.set(x, Y_WALL_BOT + 1.1 * scale, z);
  bush.castShadow = true;
  group.add(bush);
}

export function createHouse() {
  const root = new THREE.Group();
  const sceneryGroup = new THREE.Group();
  sceneryGroup.name = "sceneryGroup";
  const roofGroup = new THREE.Group();
  roofGroup.name = "roofGroup";
  const exteriorWallsGroup = new THREE.Group();
  exteriorWallsGroup.name = "exteriorWallsGroup";
  const facadeShellGroup = new THREE.Group();
  facadeShellGroup.name = "facadeShell";
  const facadeDetailGroup = new THREE.Group();
  facadeDetailGroup.name = "facadeDetail";
  const interiorGroup = new THREE.Group();
  interiorGroup.name = "interiorGroup";
  interiorGroup.visible = false;

  const parts = {
    leds: {},
    lcd: {},
    ultrasonic: {},
    door: null,
    window: null,
    fan: null,
    arduino: null,
    breadboards: [],
    buzzer: null,
    servos: {},
    ina219: null,
    lm2596: null,
    cables: [],
  };

  const woodTrim = matCardboard(0x5c3d1e);
  const wood = matCardboard(0x8b6914);
  const woodDark = matCardboard(0x6b4f2a);
  const roofA = matCardboard(0xa67c52);
  const roofB = matCardboard(0x8f6a45);
  const glass = glassMat();

  const zFront = -HALF_D;
  const zBack = HALF_D;
  const yMid = Y_WALL_BOT + WALL_H / 2;
  const zFace = zFront - WALL_T / 2;
  const xRightFace = HALF_W - WALL_T / 2;

  const doorX0 = -12.8;
  const doorX1 = -7.8;
  const doorH = 12;
  const doorCx = (doorX0 + doorX1) / 2;
  const winW = 7.5;
  const winH = 7.5;
  const winX0 = 7.5;
  const winX1 = winX0 + winW;
  const winY0 = Y_WALL_BOT + 5.4;
  const winY1 = winY0 + winH;
  const winCx = (winX0 + winX1) / 2;
  const winCy = (winY0 + winY1) / 2;

  // --- Base doble y jardín (referencia SMART ENERGY) ---
  wallBox(sceneryGroup, 0, BASE_H / 2, 0, W + 7, BASE_H, D + 7, matCardboard(0x3a3228));
  wallBox(sceneryGroup, 0, BASE_H + PLATE_H / 2, 0, W + 1.8, PLATE_H, D + 1.8, matCardboard(0xb8956a));
  const grass = matCardboard(0x2f6b42);
  const gy = BASE_H + PLATE_H + 0.07;
  wallBox(sceneryGroup, 0, gy, zFront - 4.2, W + 8, 0.16, 3.6, grass);
  wallBox(sceneryGroup, -(HALF_W + 1.8), gy, zFront - 1.5, 1.6, 0.16, 4.5, grass);
  wallBox(sceneryGroup, HALF_W + 1.8, gy, zFront - 1.5, 1.6, 0.16, 4.5, grass);

  const plankMat = matCardboard(0x8b7355);
  const pathW = 2.8;
  for (let i = 0; i < 5; i++) {
    const pz = zFront - 1.8 - i * 1.05;
    wallBox(sceneryGroup, doorCx, gy + 0.05, pz, pathW, 0.1, 0.85, plankMat);
    wallBox(sceneryGroup, doorCx - 0.55, gy + 0.04, pz - 0.05, 0.35, 0.08, 0.75, matCardboard(0x6b5340));
    wallBox(sceneryGroup, doorCx + 0.55, gy + 0.04, pz - 0.05, 0.35, 0.08, 0.75, matCardboard(0x6b5340));
  }

  const picketMat = matCardboard(0xf2ede6);
  const fenceZ = zFront - 5.4;
  const gapHalf = pathW * 0.65;
  for (let px = -HALF_W - 2; px < doorCx - gapHalf; px += 1.05) {
    wallBox(sceneryGroup, px, gy + 0.42, fenceZ, 0.18, 0.85, 0.18, picketMat);
  }
  for (let px = doorCx + gapHalf; px < HALF_W + 2; px += 1.05) {
    wallBox(sceneryGroup, px, gy + 0.42, fenceZ, 0.18, 0.85, 0.18, picketMat);
  }
  wallBox(sceneryGroup, doorCx - gapHalf - 2.2, gy + 0.28, fenceZ, 4.4, 0.1, 0.16, picketMat);
  wallBox(sceneryGroup, doorCx + gapHalf + 2.2, gy + 0.28, fenceZ, 4.4, 0.1, 0.16, picketMat);

  addPlant(sceneryGroup, -15.5, zFront - 3.8, 0.75);
  addPlant(sceneryGroup, 15, zFront - 3.5, 0.7);
  addPlant(sceneryGroup, -13, zFront - 5.1, 0.65);
  const planter = meshBox(2.4, 0.55, 1.1, matCardboard(0x6b4f2a));
  planter.position.set(winCx, Y_WALL_BOT - 0.15, zFront - 0.55);
  sceneryGroup.add(planter);
  const succ = new THREE.Mesh(new THREE.SphereGeometry(0.45, 7, 5), matCardboard(0x3d8b4a));
  succ.position.set(winCx, Y_WALL_BOT + 0.35, zFront - 0.55);
  succ.castShadow = true;
  sceneryGroup.add(succ);

  // --- Interior (conservado, no visible en fase exterior) ---
  const intWall = matCardboard(0xa08050);
  const intWall2 = matCardboard(0xc4a574);
  const floorEntry = matCardboard(0x2a2612);
  const floorSala = matCardboard(0x1a140f);
  const floorBed = matCardboard(0x1a140f);
  const floorElec = matCardboard(0x16120e);
  wallBox(interiorGroup, (-HALF_W + ENTRY_X1) / 2, Y_WALL_BOT + 0.05, 0, HALF_W + ENTRY_X1, 0.1, D, floorEntry);
  wallBox(interiorGroup, (ENTRY_X1 + SALA_X1) / 2, Y_WALL_BOT + 0.05, (INNER_Z + zBack) / 2, SALA_X1 - ENTRY_X1, 0.1, zBack - INNER_Z, floorSala);
  wallBox(interiorGroup, (SALA_X1 + TECH_X0) / 2, Y_WALL_BOT + 0.05, (INNER_Z + zBack) / 2, TECH_X0 - SALA_X1, 0.1, zBack - INNER_Z, floorBed);
  wallBox(interiorGroup, (ENTRY_X1 + TECH_X0) / 2, Y_WALL_BOT + 0.05, (zFront + INNER_Z) / 2, TECH_X0 - ENTRY_X1, 0.1, INNER_Z - zFront, floorElec);

  wallBox(exteriorWallsGroup, 0, yMid, zBack + WALL_T / 2, W, WALL_H, WALL_T, matCardboard(0xa08050));

  // Muro izquierdo (material propio)
  wallBox(exteriorWallsGroup, -HALF_W + WALL_T / 2, yMid, 0, WALL_T, WALL_H, D, matCardboard(0xc4a574));

  // Muro derecho con ventana lateral
  const sideWinZ0 = -2;
  const sideWinZ1 = 6;
  const sideWinY0 = Y_WALL_BOT + 5;
  const sideWinY1 = Y_WALL_BOT + 13;
  const sideWinW = sideWinZ1 - sideWinZ0;
  const sideWinH = sideWinY1 - sideWinY0;
  const sideWinCy = (sideWinY0 + sideWinY1) / 2;
  const sideWinCz = (sideWinZ0 + sideWinZ1) / 2;
  wallBox(
    exteriorWallsGroup,
    xRightFace,
    yMid,
    (zFront + sideWinZ0) / 2,
    WALL_T,
    WALL_H,
    sideWinZ0 - zFront,
    matCardboard(0xc9b08a),
  );
  wallBox(
    exteriorWallsGroup,
    xRightFace,
    yMid,
    (sideWinZ1 + zBack) / 2,
    WALL_T,
    WALL_H,
    zBack - sideWinZ1,
    matCardboard(0xc9b08a),
  );
  wallBox(
    exteriorWallsGroup,
    xRightFace,
    (Y_WALL_TOP + sideWinY1) / 2,
    sideWinCz,
    WALL_T,
    Y_WALL_TOP - sideWinY1,
    sideWinW,
    matCardboard(0xc9b08a),
  );
  wallBox(
    exteriorWallsGroup,
    xRightFace,
    (Y_WALL_BOT + sideWinY0) / 2,
    sideWinCz,
    WALL_T,
    sideWinY0 - Y_WALL_BOT,
    sideWinW,
    matCardboard(0xc9b08a),
  );
  wallBox(
    exteriorWallsGroup,
    xRightFace,
    (sideWinY0 + sideWinY1) / 2,
    (zFront + sideWinZ0) / 2,
    WALL_T,
    sideWinH,
    sideWinZ0 - zFront,
    matCardboard(0xc9b08a),
  );

  const sideTrim = matCardboard(0x5c3d1e);
  const sx = xRightFace + 0.32;
  const sw = sideWinW - 0.55;
  const sh = sideWinH - 0.5;
  const st = 0.42;
  wallBox(facadeDetailGroup, sx, sideWinY1 - st / 2, sideWinCz, 0.38, st, sw, sideTrim);
  wallBox(facadeDetailGroup, sx, sideWinY0 + st / 2, sideWinCz, 0.38, st, sw, sideTrim);
  wallBox(facadeDetailGroup, sx, sideWinCy, sideWinZ0 + st / 2, 0.38, sh, st, sideTrim);
  wallBox(facadeDetailGroup, sx, sideWinCy, sideWinZ1 - st / 2, 0.38, sh, st, sideTrim);
  const sidePane = meshBox(0.22, sh - st * 2, sw - st * 2, glass.clone());
  sidePane.position.set(sx + 0.12, sideWinCy, sideWinCz);
  facadeDetailGroup.add(sidePane);
  const servoSide = createServo({ scale: 0.3 });
  servoSide.position.set(xRightFace + 0.5, sideWinY0 + 0.8, sideWinZ1 - 0.4);
  servoSide.rotation.y = -Math.PI / 2;
  facadeDetailGroup.add(servoSide);
  parts.servos.sideWindow = servoSide;

  // Fachada shell (paneles crema opacos)
  const fMat = () => matCardboard(0xe5d4bc);
  wallBox(facadeShellGroup, (-HALF_W + doorX0) / 2, yMid, zFace, HALF_W + doorX0, WALL_H, WALL_T, fMat());
  wallBox(facadeShellGroup, (winX1 + HALF_W) / 2, yMid, zFace, HALF_W - winX1, WALL_H, WALL_T, fMat());
  wallBox(facadeShellGroup, (doorX1 + winX0) / 2, yMid, zFace, winX0 - doorX1, WALL_H, WALL_T, fMat());
  wallBox(
    facadeShellGroup,
    (doorX0 + doorX1) / 2,
    doorH + Y_WALL_BOT + (Y_WALL_TOP - doorH - Y_WALL_BOT) / 2,
    zFace,
    doorX1 - doorX0,
    Y_WALL_TOP - doorH,
    WALL_T,
    fMat(),
  );
  wallBox(
    facadeShellGroup,
    (winX0 + winX1) / 2,
    winY1 + (Y_WALL_TOP - winY1) / 2,
    zFace,
    winX1 - winX0,
    Y_WALL_TOP - winY1,
    WALL_T,
    fMat(),
  );
  wallBox(
    facadeShellGroup,
    (winX0 + winX1) / 2,
    Y_WALL_BOT + (winY0 - Y_WALL_BOT) / 2,
    zFace,
    winX1 - winX0,
    winY0 - Y_WALL_BOT,
    WALL_T,
    fMat(),
  );
  wallBox(
    facadeShellGroup,
    (doorX1 + winX0) / 2,
    (winY0 + winY1) / 2,
    zFace,
    winX0 - doorX1,
    winY1 - winY0,
    WALL_T,
    fMat(),
  );

  // Vigas esquina fachada
  for (const x of [-HALF_W + 0.35, HALF_W - 0.35]) {
    wallBox(facadeDetailGroup, x, yMid, zFront + 0.2, 0.55, WALL_H, 0.55, woodTrim);
  }
  wallBox(facadeDetailGroup, 0, Y_WALL_TOP - 0.35, zFront + 0.2, W + 0.5, 0.45, 0.45, woodTrim);
  wallBox(facadeDetailGroup, 0, Y_WALL_BOT - 0.08, zFront + 0.18, W + 0.35, 0.32, 0.38, woodDark);

  const doorW = doorX1 - doorX0 - 0.55;
  const creamTrim = matCardboard(0xd4c4a8);
  wallBox(facadeDetailGroup, doorCx, Y_WALL_BOT + doorH / 2, zFront + 0.12, doorW + 0.75, doorH + 0.3, 0.32, woodTrim);
  const door = meshBox(doorW, doorH - 0.35, 0.48, matCardboard(0x5c3a22));
  door.position.set(doorCx, Y_WALL_BOT + doorH / 2, zFront + 0.4);
  facadeDetailGroup.add(door);
  parts.door = door;
  const handle = meshBox(0.2, 0.45, 0.16, matCardboard(0xc0a060, { metalness: 0.25, roughness: 0.5 }));
  handle.position.set(doorX1 - 0.85, Y_WALL_BOT + doorH * 0.42, zFront + 0.68);
  facadeDetailGroup.add(handle);

  const step = meshBox(2.6, 0.26, 1.05, woodDark);
  step.position.set(doorCx, Y_WALL_BOT - 0.14, zFront - 0.95);
  facadeDetailGroup.add(step);

  const lcdExt = createLcd({ scale: 0.5, line2: "Sin lectura" });
  lcdExt.position.set(doorCx, Y_WALL_BOT + 15.2, zFront + 0.78);
  facadeDetailGroup.add(lcdExt);
  parts.lcd.exterior = lcdExt;

  const usExt = createUltrasonicSensor({ scale: 0.38 });
  usExt.position.set(doorCx, Y_WALL_BOT + 12.6, zFront + 0.74);
  facadeDetailGroup.add(usExt);
  parts.ultrasonic.exterior = usExt;

  const zWin = zFront + 0.34;
  addWindowFrame(facadeDetailGroup, winCx, winCy, winW, winH, 0.42, zWin, woodTrim, glass.clone(), creamTrim);
  const paneW = winW - 1.1;
  const paneH = winH - 1.1;
  const frontPane = meshBox(paneW, paneH, 0.14, glass.clone());
  frontPane.position.set(winCx, winCy, zFront + 0.52);
  facadeDetailGroup.add(frontPane);
  const mullionMat = matCardboard(0x5c3d1e);
  wallBox(facadeDetailGroup, winCx, winCy, zFront + 0.58, 0.1, paneH, 0.08, mullionMat);
  wallBox(facadeDetailGroup, winCx, winCy, zFront + 0.58, paneW, 0.1, 0.08, mullionMat);
  parts.window = frontPane;

  const servoDoor = createServo({ scale: 0.28 });
  servoDoor.position.set(doorX0 + 0.75, Y_WALL_BOT + 1.6, zFront + 0.55);
  facadeDetailGroup.add(servoDoor);
  parts.servos.door = servoDoor;

  const servoWin = createServo({ scale: 0.26 });
  servoWin.position.set(winX0 + 0.65, winY0 + 0.75, zFront + 0.52);
  facadeDetailGroup.add(servoWin);
  parts.servos.window = servoWin;

  // Muros interiores
  const innerH = WALL_H * 0.72;
  const innerY = Y_WALL_BOT + innerH / 2;
  wallBox(interiorGroup, ENTRY_X1, innerY, 0, WALL_T * 0.8, innerH, D, intWall);
  wallBox(interiorGroup, SALA_X1, innerY, (INNER_Z + zBack) / 2, WALL_T * 0.8, innerH, zBack - INNER_Z, intWall2);
  wallBox(interiorGroup, TECH_X0, innerY, 0, WALL_T * 0.8, innerH, D, intWall);
  wallBox(interiorGroup, (ENTRY_X1 + TECH_X0) / 2, innerY, INNER_Z, TECH_X0 - ENTRY_X1, innerH, WALL_T * 0.8, intWall2);

  const arduino = createArduinoUno({ scale: 0.42 });
  arduino.position.set(-4, Y_WALL_BOT + 0.35, -9);
  arduino.rotation.y = Math.PI / 2;
  interiorGroup.add(arduino);
  parts.arduino = arduino;

  const bb1 = createBreadboard({ scale: 0.38 });
  bb1.position.set(1.5, Y_WALL_BOT + 0.28, -9.5);
  interiorGroup.add(bb1);
  parts.breadboards.push(bb1);
  const bb2 = createBreadboard({ scale: 0.38 });
  bb2.position.set(5.5, Y_WALL_BOT + 0.28, -9.5);
  interiorGroup.add(bb2);
  parts.breadboards.push(bb2);

  parts.ina219 = createIna219({ scale: 0.35 });
  parts.ina219.position.set(8, Y_WALL_BOT + 0.3, -8.2);
  interiorGroup.add(parts.ina219);

  parts.lm2596 = createLm2596({ scale: 0.38 });
  parts.lm2596.position.set(9.5, Y_WALL_BOT + 0.32, -10.5);
  interiorGroup.add(parts.lm2596);

  const cableColors = [0xef4444, 0x111827, 0xfacc15, 0x22c55e, 0x3b82f6];
  for (let i = 0; i < 12; i++) {
    const c = createDupontCable(cableColors[i % cableColors.length], 1.8 + (i % 3) * 0.4, 0.35);
    c.position.set(-2 + (i % 4) * 1.2, Y_WALL_BOT + 0.5 + (i % 2) * 0.15, -8.5 + Math.floor(i / 4) * 0.6);
    c.rotation.y = (i * 0.4) % (Math.PI / 2);
    interiorGroup.add(c);
    parts.cables.push(c);
  }

  parts.leds.entry = createLed(0xfacc15, { scale: 0.45 });
  parts.leds.entry.position.set(-12, Y_WALL_BOT + 9, -2);
  interiorGroup.add(parts.leds.entry);
  parts.leds.living = createLed(0xf87171, { scale: 0.45 });
  parts.leds.living.position.set(-1, Y_WALL_BOT + 9, 3);
  interiorGroup.add(parts.leds.living);
  parts.leds.bedroom = createLed(0x4ade80, { scale: 0.45 });
  parts.leds.bedroom.position.set(8, Y_WALL_BOT + 9, 3);
  interiorGroup.add(parts.leds.bedroom);

  parts.buzzer = createBuzzer({ scale: 0.4 });
  parts.buzzer.position.set(-14, Y_WALL_BOT + 2.2, -6);
  interiorGroup.add(parts.buzzer);

  const usIn = createUltrasonicSensor({ scale: 0.38 });
  usIn.position.set(-11, Y_WALL_BOT + 3.5, zFront + 2.5);
  usIn.rotation.y = Math.PI;
  interiorGroup.add(usIn);
  parts.ultrasonic.interior = usIn;

  const lcdIn = createLcd({ scale: 0.42 });
  lcdIn.position.set(-10, Y_WALL_BOT + 6, zFront + 2.2);
  lcdIn.rotation.y = Math.PI;
  interiorGroup.add(lcdIn);
  parts.lcd.interior = lcdIn;

  // Techo opaco
  const r1 = roofHalf(1, roofA, roofB);
  const r2 = roofHalf(-1, matCardboard(0xa67c52), matCardboard(0x8f6a45));
  roofGroup.add(r1);
  roofGroup.add(r2);
  const zGableF = zFront - EAVE - ROOF_TH / 2;
  const zGableB = zBack + EAVE + ROOF_TH / 2;
  roofGroup.add(gableEnd(zGableF, matCardboard(0xe5d4bc)));
  roofGroup.add(gableEnd(zGableB, matCardboard(0xc9b08a)));
  const ridgeBeam = meshBox(0.55, 0.45, D + EAVE * 2, woodDark);
  ridgeBeam.position.set(0, Y_RIDGE + 0.12, 0);
  roofGroup.add(ridgeBeam);
  wallBox(roofGroup, -HALF_W - EAVE + 0.2, Y_WALL_TOP + 0.15, 0, 0.35, 0.35, D + EAVE * 2, woodTrim);
  wallBox(roofGroup, HALF_W + EAVE - 0.2, Y_WALL_TOP + 0.15, 0, 0.35, 0.35, D + EAVE * 2, woodTrim);

  const run = HALF_W + EAVE;
  const rise = Y_RIDGE - Y_WALL_TOP;
  const slopeAngle = Math.atan2(rise, run);
  const fanX = 8.5;
  const fanZ = -1.5;
  const fanY = Y_WALL_TOP + (fanX / run) * rise + 0.08;
  const fanFrame = meshBox(2.5, 0.28, 2.5, woodTrim);
  fanFrame.position.set(fanX, fanY + 0.04, fanZ);
  fanFrame.rotation.z = -slopeAngle;
  roofGroup.add(fanFrame);
  const fanRecess = meshBox(2.1, 0.38, 2.1, matCardboard(0x141414));
  fanRecess.position.set(fanX, fanY - 0.02, fanZ);
  fanRecess.rotation.z = -slopeAngle;
  roofGroup.add(fanRecess);

  const fan = createFan({ scale: 0.34 });
  fan.position.set(fanX, fanY + 0.08, fanZ);
  fan.rotation.z = -slopeAngle;
  roofGroup.add(fan);
  parts.fan = fan;

  root.add(sceneryGroup);
  root.add(interiorGroup);
  root.add(exteriorWallsGroup);
  root.add(facadeShellGroup);
  root.add(facadeDetailGroup);
  root.add(roofGroup);

  return {
    root,
    parts,
    groups: {
      roofGroup,
      facadeShellGroup,
      exteriorWallsGroup,
      facadeDetailGroup,
      interiorGroup,
      sceneryGroup,
    },
  };
}
