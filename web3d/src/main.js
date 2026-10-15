import * as THREE from "three";

window.THREE = THREE;
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  applyDebugModularMaterials,
  createHouse,
  DEBUG_MODULAR_PARTS,
  EXPLODED_FACADE_Y,
  EXPLODED_FACADE_Z,
  EXPLODED_ROOF_LIFT,
} from "./house.js";
import { applyCameraPreset, cameraPresets } from "./cameraPresets.js";
import { setExteriorView as lockExteriorShell } from "./viewShell.js";

const viewport = document.getElementById("viewport");
const btnExterior = document.getElementById("btn-exterior");
const btnExploded = document.getElementById("btn-exploded");
const btnReset = document.getElementById("btn-reset");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a2844);
scene.fog = new THREE.Fog(0x1a2844, 110, 180);

const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 200);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.28;
viewport.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.screenSpacePanning = true;
controls.minDistance = 22;
controls.maxDistance = 90;
controls.maxPolarAngle = Math.PI / 2.05;
controls.minPolarAngle = 0.2;

scene.add(new THREE.AmbientLight(0xfff0dc, 0.55));
scene.add(new THREE.HemisphereLight(0xfff4e6, 0x4a3828, 0.42));

const sun = new THREE.DirectionalLight(0xffe0b0, 1.65);
sun.position.set(-14, 22, -22);
sun.shadow.bias = -0.00028;
sun.castShadow = true;
sun.shadow.mapSize.set(1536, 1536);
sun.shadow.camera.near = 5;
sun.shadow.camera.far = 95;
sun.shadow.camera.left = -32;
sun.shadow.camera.right = 32;
sun.shadow.camera.top = 32;
sun.shadow.camera.bottom = -32;
scene.add(sun);

const facadeLight = new THREE.DirectionalLight(0xfff8ee, 0.72);
facadeLight.position.set(6, 14, -30);
scene.add(facadeLight);

const fill = new THREE.DirectionalLight(0xd8c8b0, 0.38);
fill.position.set(22, 12, 16);
scene.add(fill);

const backFill = new THREE.DirectionalLight(0xffecd8, 0.28);
backFill.position.set(-8, 10, 28);
scene.add(backFill);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(120, 120),
  new THREE.MeshStandardMaterial({ color: 0x121c30, roughness: 1 }),
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -2.4;
ground.receiveShadow = true;
scene.add(ground);

const { root: house, parts: houseParts, groups, baseTransforms } = createHouse();
scene.add(house);
window.houseParts = houseParts;
window.cameraPresets = cameraPresets;

const LERP = 0.09;
let exteriorMode = "EXTERIOR_CLOSED";
let targetRoofOffset = new THREE.Vector3(0, 0, 0);
let targetFacadeOffset = new THREE.Vector3(0, 0, 0);
let currentRoofOffset = new THREE.Vector3(0, 0, 0);
let currentFacadeOffset = new THREE.Vector3(0, 0, 0);

const roofBase = baseTransforms.roof.clone();
const facadeBase = baseTransforms.facade.clone();

function applyShellOffsets() {
  groups.removableRoof.position.copy(roofBase).add(currentRoofOffset);
  groups.removableFacade.position.copy(facadeBase).add(currentFacadeOffset);
}

function setModularHintsVisible(visible) {
  if (groups.facadeBaseSlots) groups.facadeBaseSlots.visible = visible;
  if (groups.roofGuideBlocks) groups.roofGuideBlocks.visible = visible;
  if (groups.postFasteners) groups.postFasteners.visible = visible;
}

function setExteriorClosed() {
  exteriorMode = "EXTERIOR_CLOSED";
  targetRoofOffset.set(0, 0, 0);
  targetFacadeOffset.set(0, 0, 0);
  setModularHintsVisible(false);
  lockExteriorShell(groups);
}

function setExteriorExploded() {
  exteriorMode = "EXTERIOR_EXPLODED";
  targetRoofOffset.set(0, EXPLODED_ROOF_LIFT, 0);
  targetFacadeOffset.set(0, EXPLODED_FACADE_Y, EXPLODED_FACADE_Z);
  setModularHintsVisible(true);
  lockExteriorShell(groups);
}

function setExteriorView() {
  setExteriorClosed();
}

function restoreExteriorCamera() {
  applyCameraPreset(camera, controls, cameraPresets.exteriorThreeQuarter);
}

function resetAll() {
  setExteriorClosed();
  currentRoofOffset.set(0, 0, 0);
  currentFacadeOffset.set(0, 0, 0);
  applyShellOffsets();
  restoreExteriorCamera();
}

setExteriorView();
applyShellOffsets();
restoreExteriorCamera();

btnExterior.addEventListener("click", () => {
  setExteriorClosed();
});

btnExploded.addEventListener("click", () => {
  if (exteriorMode === "EXTERIOR_EXPLODED") setExteriorClosed();
  else setExteriorExploded();
});

btnReset.addEventListener("click", resetAll);

window.setExteriorView = setExteriorView;
window.restoreExteriorCamera = restoreExteriorCamera;
window.setExteriorExploded = setExteriorExploded;
window.setExteriorClosed = setExteriorClosed;
window.applyDebugModularMaterials = (on) => applyDebugModularMaterials(house, on);
window.__viewer = {
  camera,
  controls,
  renderer,
  scene,
  house,
  exteriorMode: () => exteriorMode,
  setExteriorView,
  setExteriorExploded,
  setExteriorClosed,
  restoreExteriorCamera,
  resetAll,
  applyCameraPreset: (name) => applyCameraPreset(camera, controls, cameraPresets[name]),
  cameraPresets,
  DEBUG_MODULAR_PARTS,
};

function resize() {
  const w = viewport.clientWidth;
  const h = viewport.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
}
window.addEventListener("resize", resize);
resize();

function animate() {
  requestAnimationFrame(animate);
  currentRoofOffset.lerp(targetRoofOffset, LERP);
  currentFacadeOffset.lerp(targetFacadeOffset, LERP);
  applyShellOffsets();
  controls.update();
  renderer.render(scene, camera);
}
animate();
