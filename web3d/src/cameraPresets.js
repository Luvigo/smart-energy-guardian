import * as THREE from "three";

/** Presets deterministas (cm, origen en piso interior). */
export const cameraPresets = {
  exteriorFront: {
    position: new THREE.Vector3(0, 10.2, -76),
    target: new THREE.Vector3(0, 7.4, -12.5),
    fov: 32,
  },
  exteriorThreeQuarter: {
    position: new THREE.Vector3(-33, 13.2, -57),
    target: new THREE.Vector3(0, 7.3, -2.5),
    fov: 34,
  },
  exteriorRight: {
    position: new THREE.Vector3(58, 11.5, -4),
    target: new THREE.Vector3(0, 7, 0),
    fov: 34,
  },
  exteriorRear: {
    position: new THREE.Vector3(0, 10.5, 66),
    target: new THREE.Vector3(0, 7, 12),
    fov: 34,
  },
  explodedFront: {
    position: new THREE.Vector3(0, 12.8, -88),
    target: new THREE.Vector3(0, 7.2, -11.5),
    fov: 38,
  },
  explodedThreeQuarter: {
    position: new THREE.Vector3(-42, 17.5, -78),
    target: new THREE.Vector3(0, 7, -4),
    fov: 38,
  },
};

export function applyCameraPreset(camera, controls, preset) {
  camera.position.copy(preset.position);
  controls.target.copy(preset.target);
  if (preset.fov) {
    camera.fov = preset.fov;
    camera.updateProjectionMatrix();
  }
  controls.update();
}
