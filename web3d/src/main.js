import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createHouse } from "./house.js";
import { setExteriorView as lockExteriorShell } from "./viewShell.js";

const viewport = document.getElementById("viewport");
const btnReset = document.getElementById("btn-reset");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x162033);
scene.fog = new THREE.Fog(0x162033, 80, 150);

const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 200);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
viewport.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.screenSpacePanning = false;
controls.minDistance = 22;
controls.maxDistance = 90;
controls.maxPolarAngle = Math.PI / 2.05;
controls.minPolarAngle = 0.25;

scene.add(new THREE.AmbientLight(0xffe6c8, 0.38));
scene.add(new THREE.HemisphereLight(0xffd7a8, 0x3a2e22, 0.34));

const sun = new THREE.DirectionalLight(0xffc98a, 1.45);
sun.position.set(-20, 18, -26);
sun.shadow.bias = -0.00035;
sun.castShadow = true;
sun.shadow.mapSize.set(1536, 1536);
sun.shadow.camera.near = 5;
sun.shadow.camera.far = 95;
sun.shadow.camera.left = -32;
sun.shadow.camera.right = 32;
sun.shadow.camera.top = 32;
sun.shadow.camera.bottom = -32;
scene.add(sun);

const facadeLight = new THREE.DirectionalLight(0xfff1dc, 0.55);
facadeLight.position.set(8, 12, -32);
scene.add(facadeLight);

const fill = new THREE.DirectionalLight(0xc9b49a, 0.22);
fill.position.set(16, 10, 18);
scene.add(fill);

const backFill = new THREE.DirectionalLight(0xffe4c4, 0.42);
backFill.position.set(-6, 16, 36);
scene.add(backFill);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(120, 120),
  new THREE.MeshStandardMaterial({ color: 0x0a101c, roughness: 1 }),
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const { root: house, parts: houseParts, groups } = createHouse();
scene.add(house);
window.houseParts = houseParts;

const exteriorCam = {
  position: new THREE.Vector3(-28, 12.2, -62),
  target: new THREE.Vector3(0, 6.2, -1),
};

let viewMode = "exterior";
let targetBlend = 0;
let viewBlend = 0;

function setExteriorView() {
  viewMode = "exterior";
  targetBlend = 0;
  viewBlend = 0;
  lockExteriorShell(groups);
}

function restoreExteriorCamera() {
  camera.position.copy(exteriorCam.position);
  controls.target.copy(exteriorCam.target);
  controls.update();
}

setExteriorView();
restoreExteriorCamera();

btnReset.addEventListener("click", () => {
  setExteriorView();
  restoreExteriorCamera();
});

window.setExteriorView = setExteriorView;
window.restoreExteriorCamera = restoreExteriorCamera;
window.__viewer = { camera, controls, setExteriorView, restoreExteriorCamera };

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
  controls.update();
  renderer.render(scene, camera);
}
animate();
