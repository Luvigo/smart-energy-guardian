import * as THREE from "three";
import {
  cardboardRoofMaterial,
  cardboardWallMaterial,
  grassMaterial,
  laminatedBaseMaterial,
  pathStoneMaterial,
  woodMaterial,
  windowGlassMaterial,
} from "./materials.js";
import { createRoomLayout } from "./rooms.js";

/**
 * Molde modular exterior SMART ENERGY.
 * 1 u = 1 cm. Piso interior Y = 0. Fachada Z−.
 * Vista frontal (cámara en Z−): puerta en +X (izquierda pantalla, sala); ventana en −X (derecha, habitación).
 */
export const W = 35;
export const D = 25;
export const HALF_W = W / 2;
export const HALF_D = D / 2;

export const WALL_H = 13;
export const WALL_T = 0.28;
export const BASE_THICK = 1.2;
export const FLOOR_THICK = 0.35;
export const EAVE = 0.9;
export const ROOF_TH = 0.3;
export const Y_FLOOR_TOP = 0;
export const Y_WALL_BOT = Y_FLOOR_TOP;
export const Y_WALL_TOP = Y_WALL_BOT + WALL_H;
export const Y_RIDGE = 18;

/** Puerta sala (+X, izquierda en pantalla); ventana habitación (−X, derecha en pantalla). */
export const DOOR_CX = 8.2;
export const DOOR_W = 4.9;
export const DOOR_H = 10.6;
export const WIN_CX = -8.2;
export const WIN_W = 6.4;
export const WIN_H = 6.4;

/** Exterior frontal = jardín en Z−; explosión aleja la fachada hacia Z−. */
export const EXPLODED_ROOF_LIFT = 14;
export const EXPLODED_FACADE_Z = -11.8;
export const EXPLODED_FACADE_Y = 0.45;

export const DEBUG_MODULAR_PARTS = false;

const DEBUG_COLORS = {
  fixed: 0x3b82f6,
  facade: 0xfacc15,
  roof: 0xef4444,
  guide: 0x22c55e,
};

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

function tagRole(group, role) {
  group.userData.partRole = role;
  group.traverse((o) => {
    if (o.isMesh) o.userData.partRole = role;
  });
}

/** Ranura rectangular en el piso frontal: abierta hacia el jardín (Z−), borde cartón e interior hondo. */
function buildSlotPocket(group, ox, topY, cz, w, d, rimMat, darkMat) {
  const pitH = 0.46;
  const wallT = 0.1;
  const lipT = 0.075;
  const cy = topY - lipT - (pitH - lipT) / 2;
  const innerW = w - wallT * 2;
  const innerD = d - wallT;
  const pitHInner = pitH - lipT;
  put(group, box(innerW, 0.08, innerD, darkMat), ox, topY - pitH + 0.04, cz - 0.03);
  put(group, box(wallT, pitHInner, d - lipT, rimMat), ox - w / 2 + wallT / 2, cy, cz + lipT * 0.15);
  put(group, box(wallT, pitHInner, d - lipT, rimMat), ox + w / 2 - wallT / 2, cy, cz + lipT * 0.15);
  put(group, box(innerW, pitHInner, wallT, rimMat), ox, cy, cz + d / 2 - wallT / 2);
  put(group, box(innerW + 0.02, pitHInner - 0.08, 0.07, darkMat), ox, cy - 0.02, cz - d / 2 + lipT * 0.55);
  const lipZ = cz - d / 2 + lipT / 2;
  put(group, box(w, lipT, lipT, rimMat), ox, topY - lipT / 2, lipZ);
  put(group, box(lipT, lipT, d, rimMat), ox - w / 2 + lipT / 2, topY - lipT / 2, cz);
  put(group, box(lipT, lipT, d, rimMat), ox + w / 2 - lipT / 2, topY - lipT / 2, cz);
  put(group, box(w - lipT * 1.4, lipT, lipT, rimMat), ox, topY - lipT / 2, cz + d / 2 - lipT / 2);
  const mouth = put(group, box(innerW - 0.04, 0.06, innerD - 0.1, darkMat), ox, topY - lipT - 0.02, cz - 0.03);
  mouth.renderOrder = 3;
}

function buildRoofAssembly(roofMat, wallGable, woodDark, woodMid, strapMat) {
  const roof = new THREE.Group();
  roof.name = "roofAssembly";

  const run = HALF_W + EAVE;
  const rise = Y_RIDGE - Y_WALL_TOP;
  const slopeLen = Math.hypot(run, rise);
  const angle = Math.atan2(rise, run);
  const depth = D + EAVE * 2;
  const zFront = -HALF_D;
  const zBack = HALF_D;

  const makeSlope = (sign, mat) => {
    const g = new THREE.Group();
    g.name = sign > 0 ? "rightRoofSlope" : "leftRoofSlope";
    const panel = new THREE.Mesh(new THREE.BoxGeometry(slopeLen, ROOF_TH, depth), mat);
    panel.castShadow = true;
    panel.receiveShadow = true;
    g.add(panel);
    const underMat = mat.clone();
    underMat.color.multiplyScalar(0.9);
    const liner = new THREE.Mesh(new THREE.BoxGeometry(slopeLen - 0.35, 0.09, depth - 0.22), underMat);
    liner.position.set(0, -ROOF_TH / 2 - 0.045, 0);
    liner.receiveShadow = true;
    g.add(liner);
    const fascia = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.22, depth + 0.04), woodDark.clone());
    fascia.position.set(sign * (slopeLen / 2 - 0.04), -ROOF_TH / 2 - 0.1, 0);
    fascia.castShadow = true;
    g.add(fascia);
    const ribSpan = depth - 3.2;
    const ribMat = woodDark.clone();
    ribMat.color.multiplyScalar(0.72);
    ribMat.roughness = 0.88;
    for (const t of [0.2, 0.4, 0.6, 0.8]) {
      const rib = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.24, ribSpan), ribMat);
      rib.position.set(-slopeLen / 2 + slopeLen * t, -ROOF_TH / 2 - 0.13, 0);
      rib.castShadow = true;
      g.add(rib);
    }
    g.position.set(sign * run * 0.5, Y_WALL_TOP + rise * 0.5, 0);
    g.rotation.z = -sign * angle;
    return g;
  };

  const leftRoofSlope = makeSlope(-1, roofMat.clone());
  const rightRoofSlope = makeSlope(1, roofMat.clone());
  roof.add(leftRoofSlope);
  roof.add(rightRoofSlope);

  const ridge = put(roof, box(0.58, 0.26, depth + 0.04, woodDark.clone()), 0, Y_RIDGE + 0.1, 0);
  ridge.name = "ridge";
  put(roof, box(0.22, 0.12, depth + 0.04, woodMid.clone()), 0, Y_RIDGE + 0.22, 0);

  const intradosMat = roofMat.clone();
  intradosMat.color.multiplyScalar(0.86);
  const gableTriangleShape = (hw) => {
    const shape = new THREE.Shape();
    shape.moveTo(-hw, 0);
    shape.lineTo(hw, 0);
    shape.lineTo(0, rise);
    shape.closePath();
    return shape;
  };

  const addGableEnd = (name, zFace, outwardSign) => {
    const hw = HALF_W + EAVE;
    const skin = new THREE.Mesh(new THREE.ShapeGeometry(gableTriangleShape(hw)), wallGable.clone());
    skin.position.set(0, Y_WALL_TOP, zFace);
    skin.rotation.y = outwardSign < 0 ? Math.PI : 0;
    skin.castShadow = true;
    skin.receiveShadow = true;
    skin.name = `${name}Skin`;
    roof.add(skin);

    const fill = new THREE.Mesh(
      new THREE.ExtrudeGeometry(gableTriangleShape(hw - 0.18), { depth: 0.28, bevelEnabled: false }),
      intradosMat.clone(),
    );
    fill.position.set(0, Y_WALL_TOP, zFace + outwardSign * 0.06);
    fill.rotation.y = outwardSign < 0 ? Math.PI : 0;
    fill.castShadow = false;
    fill.receiveShadow = true;
    fill.name = `${name}Intrados`;
    roof.add(fill);
    return skin;
  };

  const frontGable = addGableEnd("frontGable", zFront - EAVE * 0.62, -1);
  const rearGable = addGableEnd("rearGable", zBack + EAVE * 0.62, 1);

  const eaveTrim = new THREE.Group();
  eaveTrim.name = "eaveTrim";
  const soffit = wallGable.clone();
  put(eaveTrim, box(W + EAVE * 2, 0.12, EAVE * 0.95, soffit), 0, Y_WALL_TOP - 0.04, zFront - EAVE * 0.5);
  put(eaveTrim, box(W + EAVE * 2, 0.12, EAVE * 0.95, soffit.clone()), 0, Y_WALL_TOP - 0.04, zBack + EAVE * 0.5);
  put(eaveTrim, box(EAVE * 0.95, 0.12, depth, soffit.clone()), -HALF_W - EAVE * 0.5, Y_WALL_TOP - 0.04, 0);
  put(eaveTrim, box(EAVE * 0.95, 0.12, depth, soffit.clone()), HALF_W + EAVE * 0.5, Y_WALL_TOP - 0.04, 0);
  roof.add(eaveTrim);

  const internalRibs = new THREE.Group();
  internalRibs.name = "internalRibs";
  roof.add(internalRibs);

  return { roof, leftRoofSlope, rightRoofSlope, ridge, frontGable, rearGable, internalRibs, eaveTrim };
}

/** Muro frontal con vanos reales (puerta y ventana); evita sólido coplanar con el marco. */
function buildFrontFacadeWall(group, mat, facadeZ, doorY, winY) {
  const panelW = W - 0.2;
  const hw = panelW / 2;
  const wall = (cx, cy, w, h) => {
    if (w < 0.08 || h < 0.08) return;
    put(group, box(w, h, WALL_T, mat.clone()), cx, cy, facadeZ);
  };
  const doorL = DOOR_CX - DOOR_W / 2 - 0.14;
  const doorR = DOOR_CX + DOOR_W / 2 + 0.14;
  const doorB = Y_WALL_BOT + 0.32;
  const doorT = doorY + DOOR_H / 2 + 0.14;
  const winL = WIN_CX - WIN_W / 2 - 0.2;
  const winR = WIN_CX + WIN_W / 2 + 0.2;
  const frameClearY = 0.34;
  const winB = winY - WIN_H / 2 - frameClearY;
  const winT = winY + WIN_H / 2 + frameClearY;
  const yTop = Y_WALL_BOT + WALL_H;
  const yBot = Y_WALL_BOT;

  const headerY = Math.max(doorT, winT);
  wall(0, (headerY + yTop) / 2, panelW, yTop - headerY);
  wall(0, (yBot + Math.min(winB, doorB)) / 2, panelW, Math.min(winB, doorB) - yBot);
  wall((-hw + winL) / 2, (yBot + yTop) / 2, winL + hw, WALL_H);
  wall((doorR + hw) / 2, (yBot + yTop) / 2, hw - doorR, WALL_H);
  wall((winR + doorL) / 2, (yBot + yTop) / 2, doorL - winR, WALL_H);
  wall(WIN_CX, (yBot + winB) / 2, winR - winL, winB - yBot);
  wall(WIN_CX, (winT + yTop) / 2, winR - winL, yTop - winT);
  if (doorB > yBot + 0.05) {
    wall(DOOR_CX, (yBot + doorB) / 2, doorR - doorL, doorB - yBot);
  }
  wall(DOOR_CX, (doorT + yTop) / 2, doorR - doorL, yTop - doorT);
}

function buildFrontWindow(group, cx, cy, w, h, facadeFaceZ, woodDark, woodLight, glass) {
  const t = 0.36;
  const frameDepth = 0.42;
  const zExterior = facadeFaceZ;
  const zFrame = zExterior - frameDepth * 0.42;
  const zGlass = zExterior + WALL_T * 0.58;
  const zMullion = zGlass - 0.04;
  const recess = new THREE.MeshStandardMaterial({ color: 0xcbb892, roughness: 0.92, metalness: 0 });
  put(group, box(w - 0.22, h - 0.22, 0.1, recess), cx, cy, zExterior + WALL_T * 0.72);
  put(group, box(w + 0.38, t + 0.08, frameDepth, woodDark.clone()), cx, cy + h / 2, zFrame);
  put(group, box(w + 0.38, t, frameDepth * 0.62, woodLight.clone()), cx, cy - h / 2 + t * 0.2, zFrame + 0.02);
  put(group, box(t, h, frameDepth, woodDark.clone()), cx - w / 2, cy, zFrame);
  put(group, box(t, h, frameDepth, woodDark.clone()), cx + w / 2, cy, zFrame);
  const paneW = w - t * 2.15;
  const paneH = h - t * 2.15;
  const pane = put(group, box(paneW, paneH, 0.06, glass), cx, cy, zGlass);
  put(group, box(0.1, paneH, 0.06, woodDark.clone()), cx, cy, zMullion);
  put(group, box(paneW, 0.1, 0.06, woodDark.clone()), cx, cy, zMullion);
  put(group, box(w + 0.72, 0.18, 0.12, woodDark.clone()), cx, cy - h / 2 - 0.14, zExterior - 0.05);
  return pane;
}

function buildManualDoor(group, cx, cy, w, h, z, wood, woodDark, woodLight) {
  put(group, box(w + 1.1, h + 0.7, 0.26, woodDark.clone()), cx, cy + 0.1, z + 0.16);
  put(group, box(w + 0.52, h + 0.14, 0.2, wood.clone()), cx, cy, z + 0.02);
  const door = put(group, box(w - 0.14, h - 0.2, 0.26, wood.clone()), cx, cy, z - 0.08);
  const panelMat = woodMaterial("dark");
  for (let i = 0; i < 4; i++) {
    put(group, box(0.48, h - 1.35, 0.08, panelMat), cx - 1.3 + i * 0.88, cy - 0.1, z - 0.18);
  }
  put(group, box(0.14, 0.1, 0.12, new THREE.MeshStandardMaterial({ color: 0xc9a227, roughness: 0.45, metalness: 0.55 })), cx + w * 0.3, cy + 0.15, z - 0.24);
  put(group, box(w + 1.3, 0.22, 0.58, woodDark.clone()), cx, cy + h / 2 + 0.26, z - 0.1);
  return door;
}

function buildFenceRun(group, x0, x1, z, picket, rail, grassTopY) {
  const picketH = 0.72;
  const yMid = grassTopY + picketH / 2;
  const step = 1.05;
  for (let x = x0; x <= x1; x += step) {
    put(group, box(0.13, picketH, 0.13, picket), x, yMid, z);
  }
  put(group, box(Math.abs(x1 - x0) + 0.2, 0.08, 0.11, rail), (x0 + x1) / 2, yMid + 0.16, z);
  put(group, box(Math.abs(x1 - x0) + 0.2, 0.08, 0.11, rail), (x0 + x1) / 2, yMid - 0.12, z);
}

let debugState = { applied: false, saved: new Map() };

export function applyDebugModularMaterials(root, enabled) {
  if (enabled && !debugState.applied) {
    root.traverse((o) => {
      if (!o.isMesh) return;
      const role = o.userData.partRole;
      if (!role) return;
      debugState.saved.set(o.uuid, o.material);
      const color =
        role === "fixed-structure"
          ? DEBUG_COLORS.fixed
          : role === "removable-facade"
            ? DEBUG_COLORS.facade
            : role === "removable-roof"
              ? DEBUG_COLORS.roof
              : role === "landscape"
                ? 0x64748b
                : null;
      if (role === "modular-guide" || o.userData.modularGuide) {
        o.material = new THREE.MeshStandardMaterial({ color: DEBUG_COLORS.guide, roughness: 0.7 });
        return;
      }
      if (color) {
        o.material = new THREE.MeshStandardMaterial({ color, roughness: 0.75 });
      }
    });
    debugState.applied = true;
  } else if (!enabled && debugState.applied) {
    root.traverse((o) => {
      if (o.isMesh && debugState.saved.has(o.uuid)) {
        o.material = debugState.saved.get(o.uuid);
      }
    });
    debugState.saved.clear();
    debugState.applied = false;
  }
}

export function createHouse() {
  const root = new THREE.Group();
  root.name = "houseRoot";

  const fixedStructure = new THREE.Group();
  fixedStructure.name = "fixedStructureGroup";
  const removableFacade = new THREE.Group();
  removableFacade.name = "removableFacadeGroup";
  const removableRoof = new THREE.Group();
  removableRoof.name = "removableRoofGroup";
  const landscape = new THREE.Group();
  landscape.name = "landscapeGroup";
  const interiorGroup = new THREE.Group();
  interiorGroup.name = "interiorGroup";
  interiorGroup.visible = false;

  tagRole(fixedStructure, "fixed-structure");
  tagRole(removableFacade, "removable-facade");
  tagRole(removableRoof, "removable-roof");
  tagRole(landscape, "landscape");

  const wallFix = cardboardWallMaterial();
  const wallFacade = cardboardWallMaterial();
  const wallGable = cardboardWallMaterial();
  const roofMat = cardboardRoofMaterial();
  const wood = woodMaterial("mid");
  const woodDark = woodMaterial("dark");
  const woodLight = woodMaterial("light");
  const grass = grassMaterial();
  const glassFacade = windowGlassMaterial();
  const baseLam = laminatedBaseMaterial();
  const strapMat = cardboardWallMaterial();
  const pathStone = pathStoneMaterial();

  const zFront = -HALF_D;
  const zBack = HALF_D;
  const yMid = Y_WALL_BOT + WALL_H / 2;
  const facadeZ = zFront - WALL_T / 2;
  const facadeFaceZ = facadeZ - WALL_T / 2;

  const roomLayout = createRoomLayout({ doorCenterX: DOOR_CX, windowCenterX: WIN_CX });

  const baseAssembly = new THREE.Group();
  baseAssembly.name = "baseAssembly";
  put(baseAssembly, box(W + 2.4, BASE_THICK, D + 2.4, baseLam.clone()), 0, Y_FLOOR_TOP - BASE_THICK / 2 - FLOOR_THICK, 0);

  const TAB_SLOT_X = [-5.5, 5.5];
  const slotTopY = Y_FLOOR_TOP + 0.1;
  const slotCenterZ = zFront - 0.34;
  const slotW = 1.9;
  const slotD = 0.55;
  const slotCenterY = slotTopY - 0.28;

  const facadeBaseSlots = new THREE.Group();
  facadeBaseSlots.name = "facadeBaseSlots";
  facadeBaseSlots.visible = false;
  facadeBaseSlots.renderOrder = 4;
  const slotRim = wallFix.clone();
  const slotDark = new THREE.MeshStandardMaterial({ color: 0x080504, roughness: 1, metalness: 0 });
  for (const ox of TAB_SLOT_X) {
    buildSlotPocket(facadeBaseSlots, ox, slotTopY, slotCenterZ, slotW, slotD, slotRim, slotDark);
  }
  fixedStructure.add(facadeBaseSlots);
  fixedStructure.add(baseAssembly);

  const floorLiving = woodLight.clone();
  floorLiving.color.multiplyScalar(1.02);
  const floorBed = woodLight.clone();
  floorBed.color.multiplyScalar(0.96);
  const livingCenterX = roomLayout.entrySide === "positive-x" ? W / 4 : -W / 4;
  const bedroomCenterX = roomLayout.windowSide === "positive-x" ? W / 4 : -W / 4;
  put(fixedStructure, box(W / 2 - 0.05, FLOOR_THICK, D, floorLiving), livingCenterX, Y_FLOOR_TOP - FLOOR_THICK / 2, 0).name =
    "floorLiving";
  const floor = put(
    fixedStructure,
    box(W / 2 - 0.05, FLOOR_THICK, D, floorBed),
    bedroomCenterX,
    Y_FLOOR_TOP - FLOOR_THICK / 2,
    0,
  );
  floor.name = "floor";

  put(fixedStructure, box(WALL_T, WALL_H, D, wallFix.clone()), -HALF_W + WALL_T / 2, yMid, 0).name = "leftWall";
  put(fixedStructure, box(WALL_T, WALL_H, D, wallFix.clone()), HALF_W - WALL_T / 2, yMid, 0).name = "rightWall";
  put(fixedStructure, box(W, WALL_H, WALL_T, wallFix.clone()), 0, yMid, zBack - WALL_T / 2).name = "rearWall";

  /** Divisor sala/habitación: mitad posterior (Z+ hacia pared trasera); frente Z− libre para electrónica. */
  const dividerDepthFull = D - WALL_T * 2;
  const dividerDepth = dividerDepthFull * 0.5;
  const dividerRearFaceZ = zBack - WALL_T;
  const dividerCenterZ = dividerRearFaceZ - dividerDepth / 2;
  const divider = put(
    fixedStructure,
    box(WALL_T, WALL_H - 0.12, dividerDepth, wallFix.clone()),
    0,
    yMid,
    dividerCenterZ,
  );
  divider.name = "interiorDividerPlaceholder";

  const cornerPosts = new THREE.Group();
  cornerPosts.name = "fixedCornerPosts";
  for (const x of [-HALF_W, HALF_W]) {
    for (const z of [zFront, zBack]) {
      put(cornerPosts, box(0.62, WALL_H + 0.12, 0.62, woodDark.clone()), x, yMid, z);
    }
  }
  fixedStructure.add(cornerPosts);

  const roofGuideBlocks = new THREE.Group();
  roofGuideBlocks.name = "roofGuideBlocks";
  for (const [x, z] of [
    [-HALF_W + 0.35, zFront + 0.5],
    [HALF_W - 0.35, zFront + 0.5],
    [-HALF_W + 0.35, zBack - 0.5],
    [HALF_W - 0.35, zBack - 0.5],
  ]) {
    put(roofGuideBlocks, box(0.52, 0.42, 0.52, woodDark.clone()), x, Y_WALL_TOP + 0.2, z);
  }
  roofGuideBlocks.visible = false;
  fixedStructure.add(roofGuideBlocks);

  const postFasteners = new THREE.Group();
  postFasteners.name = "postUpperFasteners";
  for (const ox of [-HALF_W + 0.62, HALF_W - 0.62]) {
    const m = put(
      postFasteners,
      box(0.2, 0.2, 0.1, new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.65 })),
      ox,
      Y_WALL_TOP - 0.4,
      zFront + 0.15,
    );
  }
  postFasteners.visible = false;
  fixedStructure.add(postFasteners);

  const doorY = Y_WALL_BOT + DOOR_H / 2 + 0.38;
  const winY = Y_WALL_BOT + 7.9;

  const frontWallPanel = new THREE.Group();
  frontWallPanel.name = "frontWallPanel";
  buildFrontFacadeWall(frontWallPanel, wallFacade, facadeZ, doorY, winY);
  removableFacade.add(frontWallPanel);

  const manualDoor = buildManualDoor(removableFacade, DOOR_CX, doorY, DOOR_W, DOOR_H, facadeFaceZ, wood, woodDark, woodLight);
  manualDoor.name = "manualDoor";
  const frontWindow = buildFrontWindow(
    removableFacade,
    WIN_CX,
    winY,
    WIN_W,
    WIN_H,
    facadeFaceZ,
    woodDark,
    woodLight,
    glassFacade,
  );
  frontWindow.name = "frontWindow";

  const exteriorFrames = new THREE.Group();
  exteriorFrames.name = "exteriorFrames";
  put(exteriorFrames, box(W, 0.3, 0.36, woodDark.clone()), 0, Y_WALL_BOT + 0.24, facadeFaceZ - 0.08);
  removableFacade.add(exteriorFrames);

  const rearReinforcementFrame = new THREE.Group();
  rearReinforcementFrame.name = "rearReinforcementFrame";
  const backZ = facadeZ + WALL_T / 2 + 0.1;
  put(rearReinforcementFrame, box(W - 1.4, WALL_H - 1.6, 0.2, strapMat.clone()), 0, yMid, backZ);
  put(rearReinforcementFrame, box(0.2, WALL_H - 1.6, 0.32, strapMat.clone()), -HALF_W + 1.1, yMid, backZ);
  put(rearReinforcementFrame, box(0.2, WALL_H - 1.6, 0.32, strapMat.clone()), HALF_W - 1.1, yMid, backZ);
  for (let i = -1; i <= 1; i++) {
    put(rearReinforcementFrame, box(W - 2.2, 0.16, 0.2, strapMat.clone()), 0, yMid + i * 3.1, backZ);
  }
  removableFacade.add(rearReinforcementFrame);

  const lowerAlignmentTabs = new THREE.Group();
  lowerAlignmentTabs.name = "lowerAlignmentTabs";
  const tabMat = woodDark.clone();
  tabMat.color.multiplyScalar(0.62);
  for (const ox of TAB_SLOT_X) {
    const tab = put(
      lowerAlignmentTabs,
      box(slotW - 0.22, 0.5, slotD - 0.14, tabMat),
      ox,
      slotCenterY,
      slotCenterZ - 0.04,
    );
    tab.userData.modularGuide = true;
    tab.userData.partRole = "modular-guide";
  }
  removableFacade.add(lowerAlignmentTabs);

  const upperFastenerMarkers = new THREE.Group();
  upperFastenerMarkers.name = "upperFastenerMarkers";
  for (const ox of [-HALF_W + 1.1, HALF_W - 1.1]) {
    const marker = put(
      upperFastenerMarkers,
      box(0.2, 0.2, 0.1, new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.55 })),
      ox,
      Y_WALL_TOP - 0.38,
      backZ + 0.04,
    );
    marker.userData.modularGuide = true;
    marker.userData.partRole = "modular-guide";
  }
  removableFacade.add(upperFastenerMarkers);

  const {
    roof: roofAssembly,
    leftRoofSlope,
    rightRoofSlope,
    ridge,
    frontGable,
    rearGable,
    internalRibs,
    eaveTrim,
  } = buildRoofAssembly(roofMat, wallGable, woodDark, wood, strapMat);
  removableRoof.add(roofAssembly);

  const grassW = W + 6.2;
  const grassD = D + 5.4;
  const grassTh = 0.1;
  const grassCy = -0.35;
  const grassTopY = -0.055 + grassTh / 2;
  const grassZFront = grassCy - grassD / 2;
  const grassHalfX = grassW / 2;

  put(landscape, box(grassW, grassTh, grassD, grass.clone()), 0, -0.055, grassCy).name = "grassBase";
  const deckH = BASE_THICK + FLOOR_THICK + 0.1;
  put(landscape, box(W + 8, deckH, D + 8, woodDark.clone()), 0, -deckH / 2 - 0.04, 0);

  const pathTileW = 2.04;
  const pathTileD = 0.52;
  const pathY = grassTopY + 0.06;
  const frontPath = new THREE.Group();
  frontPath.name = "frontPath";
  const pathZNearDoor = zFront - 0.58;
  const pathZFar = grassZFront + pathTileD * 0.55;
  for (let z = pathZNearDoor; z >= pathZFar; z -= 1.02) {
    put(frontPath, box(pathTileW, 0.11, pathTileD, pathStone.clone()), DOOR_CX, pathY, z);
  }
  put(frontPath, box(DOOR_W + 1.2, 0.14, 0.78, woodDark.clone()), DOOR_CX, Y_WALL_BOT + 0.1, zFront - 0.92);
  landscape.add(frontPath);

  const fenceSections = new THREE.Group();
  fenceSections.name = "fenceSections";
  const picket = new THREE.MeshStandardMaterial({ color: 0xf8f6f0, roughness: 0.72, metalness: 0 });
  const rail = new THREE.MeshStandardMaterial({ color: 0xe8e4dc, roughness: 0.75, metalness: 0 });
  const fenceInsetZ = 0.9;
  const fenceInsetX = 1.85;
  const fenceZ = grassZFront + fenceInsetZ;
  const fenceXMax = grassHalfX - fenceInsetX;
  const gap = 2.4;
  buildFenceRun(fenceSections, -fenceXMax, DOOR_CX - gap, fenceZ, picket, rail, grassTopY);
  buildFenceRun(fenceSections, DOOR_CX + gap, fenceXMax, fenceZ, picket, rail, grassTopY);
  landscape.add(fenceSections);

  const smallPlants = new THREE.Group();
  smallPlants.name = "smallPlants";
  const bushMat = new THREE.MeshStandardMaterial({ color: 0x2d7340, roughness: 0.9, metalness: 0 });
  const bushMat2 = new THREE.MeshStandardMaterial({ color: 0x3e8a46, roughness: 0.9, metalness: 0 });
  const leaf = new THREE.MeshStandardMaterial({ color: 0x2f7a3e, roughness: 0.9, metalness: 0 });
  const plantXMax = grassHalfX - 1.15;
  const plantZMin = grassZFront + 0.95;
  const plantZMax = grassCy + grassD / 2 - 1.25;
  const addBush = (cx, cz, radius, material, squashY = 0.72, stretchX = 1) => {
    const x = Math.max(-plantXMax, Math.min(plantXMax, cx));
    const z = Math.max(plantZMin, Math.min(plantZMax, cz));
    const bush = new THREE.Mesh(new THREE.SphereGeometry(radius, 8, 6), material);
    bush.scale.set(stretchX, squashY, 1);
    bush.position.set(x, grassTopY + radius * squashY * 0.82, z);
    bush.castShadow = true;
    smallPlants.add(bush);
    return { x, z, radius };
  };
  addBush(-13.4, zFront - 1.5, 0.5, bushMat, 0.74, 1.02);
  addBush(12.6, zFront - 1.75, 0.44, bushMat2, 0.68, 1.06);
  addBush(WIN_CX - 2.35, zFront - 1.22, 0.34, leaf, 0.42);
  addBush(WIN_CX + 2.15, zFront - 1.38, 0.3, leaf, 0.38);
  addBush(-16.2, plantZMin + 2.1, 0.36, leaf, 0.4);
  addBush(15.8, plantZMin + 2.55, 0.32, leaf, 0.36);
  landscape.add(smallPlants);

  root.add(landscape);
  root.add(fixedStructure);
  root.add(removableFacade);
  root.add(removableRoof);
  root.add(interiorGroup);

  if (DEBUG_MODULAR_PARTS) applyDebugModularMaterials(root, true);

  const baseTransforms = {
    roof: removableRoof.position.clone(),
    facade: removableFacade.position.clone(),
  };

  const parts = {
    door: manualDoor,
    window: frontWindow,
    rooms: roomLayout.rooms,
    entrySide: roomLayout.entrySide,
    windowSide: roomLayout.windowSide,
    groups: {
      fixedStructure,
      removableFacade,
      removableRoof,
      landscape,
    },
    fixedStructure,
    removableFacade,
    removableRoof,
    landscape,
    baseAssembly,
    floor,
    leftWall: fixedStructure.getObjectByName("leftWall"),
    rightWall: fixedStructure.getObjectByName("rightWall"),
    rearWall: fixedStructure.getObjectByName("rearWall"),
    interiorDividerPlaceholder: divider,
    frontWallPanel,
    manualDoor,
    frontWindow,
    leftRoofSlope,
    rightRoofSlope,
    ridge,
    frontGable,
    rearGable,
    componentAnchors: {
      livingEntry: { x: DOOR_CX, z: zFront + 2 },
      bedroomWindow: { x: WIN_CX, z: zFront + 2 },
    },
  };

  return {
    root,
    baseTransforms,
    parts,
    groups: {
      fixedStructure,
      removableFacade,
      removableRoof,
      landscape,
      interiorGroup,
      facadeBaseSlots,
      roofGuideBlocks,
      postFasteners,
      lowerAlignmentTabs,
      roofGroup: removableRoof,
      facadeShellGroup: removableFacade,
      exteriorWallsGroup: fixedStructure,
    },
  };
}

