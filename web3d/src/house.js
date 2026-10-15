import * as THREE from "three";
import {
  cardboardRoofMaterial,
  cardboardWallMaterial,
  glassMaterial,
  grassMaterial,
  woodMaterial,
} from "./materials.js";

/**
 * Maqueta exterior. Origen en el centro del suelo.
 * +X derecha de la maqueta, +Y arriba, +Z fondo.
 * Fachada en Z negativo. La cámara inicial mira desde Z negativo:
 * en esa vista, +X queda a la izquierda de la pantalla, así que la
 * puerta vive en X positivo y la ventana frontal en X negativo.
 * El ensamblado interior anterior se conserva en interiorLegacy.js
 * y no se añade a la escena.
 */
export const W = 35;
export const D = 25;
export const HALF_W = W / 2;
export const HALF_D = D / 2;
const WALL_H = 16.5;
const WALL_T = 0.85;
const BASE_H = 1.35;
const PLATE_H = 0.42;
const EAVE = 1.15;
const ROOF_TH = 0.55;
const Y_WALL_BOT = BASE_H + PLATE_H;
const Y_WALL_TOP = Y_WALL_BOT + WALL_H;
const Y_RIDGE = Y_WALL_TOP + 3.15;

const DOOR_CX = 8.6;
const DOOR_W = 4.6;
const DOOR_H = 11.4;
const WIN_CX = -7.4;
const WIN_W = 6.6;
const WIN_H = 6.4;

function box(w, h, d, material) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function put(group, mesh, x, y, z) {
  mesh.position.set(x, y, z);
  group.add(mesh);
  return mesh;
}

function roofPanel(sign, material, seamMat) {
  const run = HALF_W + EAVE;
  const rise = Y_RIDGE - Y_WALL_TOP;
  const slopeLen = Math.hypot(run, rise);
  const angle = Math.atan2(rise, run);
  const depth = D + EAVE * 2;
  const g = new THREE.Group();
  const panel = new THREE.Mesh(new THREE.BoxGeometry(slopeLen, ROOF_TH, depth), material);
  panel.castShadow = true;
  panel.receiveShadow = true;
  g.add(panel);
  const fascia = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.48, depth + 0.15), seamMat);
  fascia.position.set(sign * (slopeLen / 2 - 0.08), -0.16, 0);
  fascia.castShadow = true;
  fascia.receiveShadow = true;
  g.add(fascia);
  for (let i = 1; i <= 3; i++) {
    const seam = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.045, depth * 0.9), seamMat);
    seam.position.set(-slopeLen / 2 + (slopeLen * i) / 4, ROOF_TH / 2 + 0.02, 0);
    seam.castShadow = true;
    g.add(seam);
  }
  g.position.set(sign * run * 0.5, Y_WALL_TOP + rise * 0.5, 0);
  g.rotation.z = -sign * angle;
  return g;
}

function gable(z, material, outward) {
  const hw = HALF_W + EAVE;
  const rise = Y_RIDGE - Y_WALL_TOP;
  const shape = new THREE.Shape();
  shape.moveTo(-hw, 0);
  shape.lineTo(hw, 0);
  shape.lineTo(0, rise);
  shape.closePath();
  const geom = new THREE.ExtrudeGeometry(shape, { depth: 0.5, bevelEnabled: false });
  geom.computeVertexNormals();
  const mesh = new THREE.Mesh(geom, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.position.set(0, Y_WALL_TOP, z + outward * 0.02);
  return mesh;
}

function windowOnFace(group, cx, cy, w, h, z, face, wood, woodLight, glass) {
  const t = 0.38;
  const depth = 0.62;
  const outward = face === "front" ? -1 : face === "back" ? 1 : face === "posX" ? 1 : -1;
  const recess = new THREE.MeshStandardMaterial({ color: 0xcbb892, roughness: 0.92, metalness: 0 });
  if (face === "front" || face === "back") {
    put(group, box(w - 0.3, h - 0.3, 0.2, recess), cx, cy, z + outward * 0.22);
    put(group, box(w + 0.35, t + 0.08, depth, wood), cx, cy + h / 2, z);
    put(group, box(w + 0.35, t, depth * 0.72, woodLight), cx, cy - h / 2 + t * 0.2, z + outward * 0.08);
    put(group, box(t, h, depth, wood), cx - w / 2, cy, z);
    put(group, box(t, h, depth, wood), cx + w / 2, cy, z);
    put(group, box(w - t * 1.2, 0.16, 0.22, woodLight), cx, cy + h / 2 - t * 0.9, z + outward * 0.28);
    put(group, box(w - t * 1.2, 0.16, 0.22, woodLight), cx, cy - h / 2 + t * 0.9, z + outward * 0.28);
    put(group, box(0.16, h - t * 1.4, 0.22, woodLight), cx - w / 2 + t * 0.95, cy, z + outward * 0.28);
    put(group, box(0.16, h - t * 1.4, 0.22, woodLight), cx + w / 2 - t * 0.95, cy, z + outward * 0.28);
    const pane = put(group, box(w - t * 2.4, h - t * 2.4, 0.1, glass), cx, cy, z + outward * 0.34);
    put(group, box(0.08, h - t * 2.8, 0.06, wood), cx, cy, z + outward * 0.4);
    put(group, box(w - t * 2.8, 0.08, 0.06, wood), cx, cy, z + outward * 0.4);
    put(group, box(w + 0.7, 0.16, 0.55, wood), cx, cy - h / 2 - 0.12, z + outward * 0.22);
    return pane;
  }
  put(group, box(0.18, h - 0.25, w - 0.25, recess), cx + outward * -0.05, cy, z);
  put(group, box(depth, t + 0.06, w + 0.3, wood), cx, cy + h / 2, z);
  put(group, box(depth * 0.7, t, w + 0.3, woodLight), cx + outward * 0.08, cy - h / 2 + t * 0.15, z);
  put(group, box(depth, h, t, wood), cx, cy, z - w / 2);
  put(group, box(depth, h, t, wood), cx, cy, z + w / 2);
  const pane = put(group, box(0.1, h - t * 2.2, w - t * 2.2, glass), cx + outward * 0.28, cy, z);
  put(group, box(0.55, 0.14, w + 0.55, wood), cx + outward * 0.22, cy - h / 2 - 0.1, z);
  return pane;
}

function woodVent(group, x, y, z, wood) {
  put(group, box(0.18, 1.35, 1.7, wood), x, y, z);
  for (let i = 0; i < 4; i++) {
    put(group, box(0.1, 0.08, 1.35, wood), x + 0.12, y - 0.45 + i * 0.3, z);
  }
}

export function createHouse() {
  const root = new THREE.Group();
  const exteriorGroup = new THREE.Group();
  exteriorGroup.name = "exteriorGroup";
  const sceneryGroup = new THREE.Group();
  sceneryGroup.name = "sceneryGroup";
  const interiorGroup = new THREE.Group();
  interiorGroup.name = "interiorGroup";
  interiorGroup.visible = false;

  const wallMat = cardboardWallMaterial();
  const roofMatL = cardboardRoofMaterial();
  const roofMatR = cardboardRoofMaterial();
  const gableMat = cardboardWallMaterial();
  const wood = woodMaterial("mid");
  const woodDark = woodMaterial("dark");
  const woodLight = woodMaterial("light");
  const grass = grassMaterial();
  const glass = glassMaterial();
  const leaf = new THREE.MeshStandardMaterial({ color: 0x2f7a3e, roughness: 0.9, metalness: 0 });

  const zFront = -HALF_D;
  const zBack = HALF_D;
  const yMid = Y_WALL_BOT + WALL_H / 2;

  put(exteriorGroup, box(W, WALL_H, WALL_T, wallMat), 0, yMid, zFront);
  put(exteriorGroup, box(W, WALL_H, WALL_T, cardboardWallMaterial()), 0, yMid, zBack);
  put(exteriorGroup, box(WALL_T, WALL_H, D, cardboardWallMaterial()), -HALF_W, yMid, 0);
  put(exteriorGroup, box(WALL_T, WALL_H, D, cardboardWallMaterial()), HALF_W, yMid, 0);

  for (const x of [-HALF_W, HALF_W]) {
    for (const z of [zFront, zBack]) {
      put(exteriorGroup, box(0.72, WALL_H + 0.2, 0.72, woodDark), x, yMid, z);
    }
  }
  put(exteriorGroup, box(W + 0.5, 0.55, 0.48, woodDark), 0, Y_WALL_BOT + 0.12, zFront - 0.22);
  put(exteriorGroup, box(W + 0.5, 0.55, 0.48, woodDark), 0, Y_WALL_BOT + 0.12, zBack + 0.22);
  put(exteriorGroup, box(0.48, 0.55, D, woodDark), -HALF_W - 0.16, Y_WALL_BOT + 0.12, 0);
  put(exteriorGroup, box(0.48, 0.55, D, woodDark), HALF_W + 0.16, Y_WALL_BOT + 0.12, 0);
  put(exteriorGroup, box(W + 0.35, 0.32, 0.42, wood), 0, Y_WALL_TOP - 0.08, zFront - 0.2);
  put(exteriorGroup, box(W + 0.35, 0.32, 0.42, wood), 0, Y_WALL_TOP - 0.08, zBack + 0.2);

  const doorZ = zFront - 0.72;
  const doorY = Y_WALL_BOT + DOOR_H / 2;
  put(exteriorGroup, box(DOOR_W + 1.15, DOOR_H + 0.7, 0.28, woodDark), DOOR_CX, doorY + 0.1, doorZ + 0.22);
  put(exteriorGroup, box(DOOR_W + 0.55, DOOR_H + 0.15, 0.22, wood), DOOR_CX, doorY, doorZ + 0.02);
  const door = put(exteriorGroup, box(DOOR_W - 0.15, DOOR_H - 0.2, 0.28, wood), DOOR_CX, doorY, doorZ - 0.08);
  const panelMat = woodMaterial("dark");
  for (let i = 0; i < 4; i++) {
    const px = DOOR_CX - 1.35 + i * 0.9;
    put(exteriorGroup, box(0.55, DOOR_H - 1.5, 0.08, panelMat), px, doorY - 0.1, doorZ - 0.2);
  }
  put(exteriorGroup, box(0.14, 0.48, 0.1, woodLight), DOOR_CX - DOOR_W * 0.28, Y_WALL_BOT + DOOR_H * 0.46, doorZ - 0.28);
  put(exteriorGroup, box(DOOR_W + 1.4, 0.22, 0.7, woodDark), DOOR_CX, doorY + DOOR_H / 2 + 0.28, doorZ - 0.15);
  put(exteriorGroup, box(DOOR_W + 1.6, 0.22, 0.95, woodDark), DOOR_CX, Y_WALL_BOT + 0.28, zFront - 0.85);
  put(exteriorGroup, box(DOOR_W + 2.3, 0.2, 1.15, wood), DOOR_CX, Y_WALL_BOT - 0.02, zFront - 1.7);

  const winY = Y_WALL_BOT + 8.1;
  const frontWin = windowOnFace(
    exteriorGroup,
    WIN_CX,
    winY,
    WIN_W,
    WIN_H,
    zFront - 0.62,
    "front",
    woodDark,
    woodLight,
    glass,
  );
  windowOnFace(exteriorGroup, -HALF_W - 0.42, Y_WALL_BOT + 8.8, 2.15, 7.2, -3.6, "negX", woodDark, woodLight, glassMaterial());
  woodVent(exteriorGroup, HALF_W + 0.42, Y_WALL_BOT + 12.2, -5.5, woodDark);
  woodVent(exteriorGroup, HALF_W + 0.42, Y_WALL_BOT + 12.2, 4.2, woodDark);
  windowOnFace(exteriorGroup, 4.2, Y_WALL_BOT + 9.4, 3.3, 3.6, zBack + 0.62, "back", woodDark, woodLight, glassMaterial());

  const planter = put(exteriorGroup, box(WIN_W * 0.78, 0.62, 1.05, wood), WIN_CX, Y_WALL_BOT + 0.22, zFront - 1.05);
  const leafDark = new THREE.MeshStandardMaterial({ color: 0x246b38, roughness: 0.9, metalness: 0 });
  const leafLite = new THREE.MeshStandardMaterial({ color: 0x6a9a48, roughness: 0.88, metalness: 0 });
  for (const [dx, kind] of [[-1.5, "cone"], [0, "ball"], [1.45, "low"]]) {
    if (kind === "cone") {
      const p = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.7, 6), leaf);
      p.position.set(WIN_CX + dx, Y_WALL_BOT + 0.85, zFront - 1.05);
      p.castShadow = true;
      exteriorGroup.add(p);
    } else if (kind === "ball") {
      const p = new THREE.Mesh(new THREE.SphereGeometry(0.32, 8, 6), leafDark);
      p.position.set(WIN_CX + dx, Y_WALL_BOT + 0.78, zFront - 1.05);
      p.castShadow = true;
      exteriorGroup.add(p);
    } else {
      const p = new THREE.Mesh(new THREE.SphereGeometry(0.22, 7, 5), leafLite);
      p.scale.y = 0.45;
      p.position.set(WIN_CX + dx, Y_WALL_BOT + 0.62, zFront - 1.05);
      p.castShadow = true;
      exteriorGroup.add(p);
    }
  }

  exteriorGroup.add(roofPanel(1, roofMatL, woodDark));
  exteriorGroup.add(roofPanel(-1, roofMatR, woodDark));
  exteriorGroup.add(gable(-(HALF_D + EAVE) - 0.2, gableMat, -1));
  exteriorGroup.add(gable(HALF_D + EAVE + 0.2, cardboardWallMaterial(), 1));
  put(exteriorGroup, box(0.7, 0.28, D + EAVE * 2, woodDark), 0, Y_RIDGE + 0.16, 0);
  put(exteriorGroup, box(0.28, 0.18, D + EAVE * 2, wood), 0, Y_RIDGE + 0.32, 0);
  put(exteriorGroup, box(0.22, 0.22, D + EAVE * 2.1, woodDark), -(HALF_W + EAVE) + 0.15, Y_WALL_TOP + 0.08, 0);
  put(exteriorGroup, box(0.22, 0.22, D + EAVE * 2.1, woodDark), HALF_W + EAVE - 0.15, Y_WALL_TOP + 0.08, 0);
  const soffit = cardboardWallMaterial();
  put(exteriorGroup, box(W + EAVE * 2, 0.16, EAVE, soffit), 0, Y_WALL_TOP - 0.02, -(HALF_D + EAVE * 0.45));
  put(exteriorGroup, box(W + EAVE * 2, 0.16, EAVE, soffit), 0, Y_WALL_TOP - 0.02, HALF_D + EAVE * 0.45);

  const deck = woodMaterial("dark");
  put(sceneryGroup, box(W + 8, BASE_H, D + 8, deck), 0, BASE_H / 2, 0);
  put(sceneryGroup, box(W + 2.4, PLATE_H, D + 2.4, woodMaterial("light")), 0, BASE_H + PLATE_H / 2, 0);
  const gy = BASE_H + PLATE_H + 0.08;
  const grassW = W + 6.2;
  const grassD = D + 5.2;
  put(sceneryGroup, box(grassW, 0.1, grassD, grass), 0, gy, -0.6);
  const edge = woodMaterial("dark");
  put(sceneryGroup, box(grassW + 0.3, 0.16, 0.18, edge), 0, gy + 0.04, -0.6 - grassD / 2);
  put(sceneryGroup, box(grassW + 0.3, 0.16, 0.18, edge), 0, gy + 0.04, -0.6 + grassD / 2);
  put(sceneryGroup, box(0.18, 0.16, grassD, edge), -grassW / 2, gy + 0.04, -0.6);
  put(sceneryGroup, box(0.18, 0.16, grassD, edge), grassW / 2, gy + 0.04, -0.6);

  const slab = woodMaterial("light");
  const slabDark = woodMaterial("mid");
  for (let i = 0; i < 4; i++) {
    const rise = i === 3 ? 0.08 : 0;
    put(
      sceneryGroup,
      box(2.15, 0.1, 0.62, i % 2 ? slabDark : slab),
      DOOR_CX,
      gy + 0.08 + rise,
      zFront - 2.15 - i * 1.15,
    );
  }

  const fenceZ = zFront - 6.35;
  const picket = new THREE.MeshStandardMaterial({ color: 0xf4f0e8, roughness: 0.78, metalness: 0 });
  const addRun = (x0, x1, z, alongX) => {
    const step = 1.15;
    if (alongX) {
      for (let x = x0; x <= x1; x += step) put(sceneryGroup, box(0.12, 0.7, 0.12, picket), x, gy + 0.4, z);
      put(sceneryGroup, box(Math.abs(x1 - x0), 0.07, 0.1, picket), (x0 + x1) / 2, gy + 0.28, z);
    } else {
      for (let zz = x0; zz <= x1; zz += step) put(sceneryGroup, box(0.12, 0.62, 0.12, picket), z, gy + 0.36, zz);
    }
  };
  addRun(-8, 5.6, fenceZ, true);
  addRun(11.6, 16.5, fenceZ, true);
  addRun(zFront - 5.2, zFront - 2.4, -16.2, false);
  addRun(zFront - 5.2, zFront - 2.4, 16.2, false);

  const bushMat = new THREE.MeshStandardMaterial({ color: 0x2d7340, roughness: 0.9, metalness: 0 });
  const bushMat2 = new THREE.MeshStandardMaterial({ color: 0x3e8a46, roughness: 0.9, metalness: 0 });
  const b1 = new THREE.Mesh(new THREE.SphereGeometry(0.62, 8, 6), bushMat);
  b1.position.set(-13.2, gy + 0.7, zFront - 3.4);
  b1.castShadow = true;
  sceneryGroup.add(b1);
  const b2 = new THREE.Mesh(new THREE.SphereGeometry(0.48, 8, 6), bushMat2);
  b2.scale.set(1.15, 0.75, 1);
  b2.position.set(14.6, gy + 0.5, zFront - 2.8);
  b2.castShadow = true;
  sceneryGroup.add(b2);
  for (const [x, z] of [[-4.2, zFront - 4.4], [12.2, zFront - 4.8]]) {
    const low = new THREE.Mesh(new THREE.SphereGeometry(0.36, 7, 5), leaf);
    low.scale.y = 0.35;
    low.position.set(x, gy + 0.22, z);
    low.castShadow = true;
    sceneryGroup.add(low);
  }
  put(sceneryGroup, box(2.4, 0.45, 0.85, wood), -1.2, gy + 0.28, zFront - 3.1);
  const bed = new THREE.Mesh(new THREE.SphereGeometry(0.28, 6, 5), leaf);
  bed.scale.set(1.6, 0.4, 0.7);
  bed.position.set(-1.2, gy + 0.58, zFront - 3.1);
  bed.castShadow = true;
  sceneryGroup.add(bed);

  root.add(sceneryGroup);
  root.add(exteriorGroup);
  root.add(interiorGroup);

  return {
    root,
    parts: { door, window: frontWin },
    groups: {
      exteriorGroup,
      sceneryGroup,
      interiorGroup,
      roofGroup: exteriorGroup,
      facadeShellGroup: exteriorGroup,
      exteriorWallsGroup: exteriorGroup,
    },
  };
}
