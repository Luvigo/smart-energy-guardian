import * as THREE from "three";

function mat(color, roughness = 0.88, metalness = 0.04) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}

function box(w, h, d, material) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

export function createLcdTexture(line2 = "Sin lectura") {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 128;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#061a28";
  ctx.fillRect(0, 0, 256, 128);
  ctx.strokeStyle = "#1e3a2f";
  ctx.lineWidth = 6;
  ctx.strokeRect(4, 4, 248, 120);
  ctx.fillStyle = "#7dd3fc";
  ctx.font = "bold 20px Helvetica, Arial, sans-serif";
  ctx.fillText("SMART ENERGY", 16, 44);
  ctx.fillStyle = "#22c55e";
  ctx.font = "18px Helvetica, Arial, sans-serif";
  ctx.fillText(line2, 16, 78);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export function createLcd({ scale = 1, line2 = "Sin lectura" } = {}) {
  const g = new THREE.Group();
  g.name = "lcd";
  const pcb = mat(0x14532d);
  const frame = box(2.8 * scale, 1.6 * scale, 0.12 * scale, mat(0x111827));
  g.add(frame);
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(2.5 * scale, 1.25 * scale),
    new THREE.MeshStandardMaterial({
      map: createLcdTexture(line2),
      roughness: 0.55,
      emissive: 0x0a2030,
      emissiveIntensity: 0.3,
    }),
  );
  screen.position.z = 0.08 * scale;
  g.add(screen);
  for (let i = 0; i < 4; i++) {
    const pin = box(0.08 * scale, 0.08 * scale, 0.25 * scale, mat(0x94a3b8, 0.5, 0.35));
    pin.position.set(-0.35 * scale + i * 0.22 * scale, -0.95 * scale, -0.1 * scale);
    g.add(pin);
  }
  g.userData.tooltip = "LCD I2C (pantalla de proximidad/distancia)";
  return g;
}

export function createUltrasonicSensor({ scale = 1 } = {}) {
  const g = new THREE.Group();
  g.name = "hcsr04";
  const board = box(2.6 * scale, 1.1 * scale, 0.35 * scale, mat(0x1e3a5f));
  g.add(board);
  const cyl = new THREE.Mesh(
    new THREE.CylinderGeometry(0.42 * scale, 0.42 * scale, 0.35 * scale, 12),
    mat(0xb8c4d0, 0.45, 0.45),
  );
  cyl.rotation.x = Math.PI / 2;
  cyl.position.set(-0.55 * scale, 0.15 * scale, 0.32 * scale);
  g.add(cyl);
  const cyl2 = cyl.clone();
  cyl2.position.x = 0.55 * scale;
  g.add(cyl2);
  g.userData.tooltip = "HC-SR04 (sensor ultrasónico)";
  return g;
}

export function createArduinoUno({ scale = 1 } = {}) {
  const g = new THREE.Group();
  g.name = "arduino-uno";
  const pcb = box(3.4 * scale, 0.18 * scale, 2.6 * scale, mat(0x1d4ed8));
  g.add(pcb);
  const chip = box(0.7 * scale, 0.22 * scale, 0.55 * scale, mat(0x111827));
  chip.position.set(0, 0.12 * scale, 0.1 * scale);
  g.add(chip);
  const usb = box(0.45 * scale, 0.25 * scale, 0.55 * scale, mat(0xc0c0c0, 0.4, 0.5));
  usb.position.set(-1.55 * scale, 0.1 * scale, 0);
  g.add(usb);
  const jack = box(0.35 * scale, 0.35 * scale, 0.35 * scale, mat(0x111827));
  jack.position.set(1.45 * scale, 0.1 * scale, 0.8 * scale);
  g.add(jack);
  for (const side of [-1, 1]) {
    for (let i = 0; i < 7; i++) {
      const pin = box(0.06 * scale, 0.14 * scale, 0.06 * scale, mat(0xd4d4d8, 0.5, 0.4));
      pin.position.set(-1.1 * scale + i * 0.32 * scale, 0.12 * scale, side * 1.35 * scale);
      g.add(pin);
    }
  }
  const led1 = box(0.08 * scale, 0.06 * scale, 0.08 * scale, mat(0x22c55e, 0.3, 0.1));
  led1.position.set(0.9 * scale, 0.12 * scale, -0.55 * scale);
  g.add(led1);
  g.userData.tooltip = "Arduino UNO";
  return g;
}

export function createBreadboard({ scale = 1 } = {}) {
  const g = new THREE.Group();
  g.name = "breadboard";
  const body = box(3.8 * scale, 0.14 * scale, 2.6 * scale, mat(0xf5f5f4));
  g.add(body);
  const red = box(3.6 * scale, 0.03 * scale, 0.12 * scale, mat(0xdc2626));
  red.position.set(0, 0.1 * scale, 1.05 * scale);
  g.add(red);
  const blue = box(3.6 * scale, 0.03 * scale, 0.12 * scale, mat(0x2563eb));
  blue.position.set(0, 0.1 * scale, -1.05 * scale);
  g.add(blue);
  const holeMat = mat(0xd6d3d1, 0.95, 0);
  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 9; c++) {
      const h = box(0.06 * scale, 0.02 * scale, 0.06 * scale, holeMat);
      h.position.set(-1.4 * scale + c * 0.35 * scale, 0.1 * scale, -0.5 * scale + r * 0.25 * scale);
      g.add(h);
    }
  }
  g.userData.tooltip = "Protoboard";
  return g;
}

export function createDupontCable(color, length = 2.5, scale = 1) {
  const g = new THREE.Group();
  const wire = new THREE.Mesh(
    new THREE.CylinderGeometry(0.04 * scale, 0.04 * scale, length * scale, 6),
    mat(color, 0.7, 0.05),
  );
  wire.rotation.z = Math.PI / 2;
  g.add(wire);
  const cap = box(0.12 * scale, 0.12 * scale, 0.12 * scale, mat(0x111827));
  cap.position.x = (length / 2) * scale;
  g.add(cap);
  const cap2 = cap.clone();
  cap2.position.x = (-length / 2) * scale;
  g.add(cap2);
  return g;
}

export function createLed(colorHex, { scale = 1 } = {}) {
  const g = new THREE.Group();
  g.name = "led";
  const body = new THREE.Mesh(
    new THREE.SphereGeometry(0.35 * scale, 10, 8),
    new THREE.MeshStandardMaterial({
      color: colorHex,
      emissive: 0x000000,
      emissiveIntensity: 0,
      roughness: 0.55,
    }),
  );
  g.add(body);
  const base = box(0.5 * scale, 0.15 * scale, 0.5 * scale, mat(0x292524));
  base.position.y = -0.35 * scale;
  g.add(base);
  g.userData.ledMaterial = body.material;
  g.userData.tooltip = "LED de zona";
  return g;
}

export function createBuzzer({ scale = 1 } = {}) {
  const g = new THREE.Group();
  const disc = new THREE.Mesh(
    new THREE.CylinderGeometry(0.55 * scale, 0.55 * scale, 0.35 * scale, 14),
    mat(0x111827),
  );
  g.add(disc);
  g.userData.tooltip = "Buzzer";
  return g;
}

export function createServo({ scale = 1 } = {}) {
  const g = new THREE.Group();
  const body = box(1.1 * scale, 0.55 * scale, 0.9 * scale, mat(0x1e293b));
  g.add(body);
  const horn = box(0.15 * scale, 0.12 * scale, 0.65 * scale, mat(0xe7e5e4));
  horn.position.set(0, 0.35 * scale, 0.35 * scale);
  g.add(horn);
  const cable = createDupontCable(0xef4444, 1.2, scale * 0.5);
  cable.rotation.y = Math.PI / 2;
  cable.position.set(-0.7 * scale, 0, 0);
  g.add(cable);
  g.userData.tooltip = "Servo SG90";
  return g;
}

export function createIna219({ scale = 1 } = {}) {
  const g = new THREE.Group();
  g.add(box(1.4 * scale, 0.12 * scale, 1.1 * scale, mat(0x1d4ed8)));
  const terminal = box(0.5 * scale, 0.2 * scale, 0.35 * scale, mat(0x166534));
  terminal.position.set(0.45 * scale, 0.08 * scale, 0);
  g.add(terminal);
  g.userData.tooltip = "INA219 (medidor de energía)";
  return g;
}

export function createLm2596({ scale = 1 } = {}) {
  const g = new THREE.Group();
  g.add(box(1.6 * scale, 0.14 * scale, 1.2 * scale, mat(0x1e40af)));
  const pot = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18 * scale, 0.18 * scale, 0.12 * scale, 10),
    mat(0xf5f5f4),
  );
  pot.position.set(-0.35 * scale, 0.12 * scale, 0);
  g.add(pot);
  const screw = box(0.45 * scale, 0.18 * scale, 0.3 * scale, mat(0x15803d));
  screw.position.set(0.45 * scale, 0.08 * scale, 0);
  g.add(screw);
  g.userData.tooltip = "LM2596 (alimentación 5 V — pendiente)";
  return g;
}

export function createFan({ scale = 1 } = {}) {
  const g = new THREE.Group();
  g.name = "fan";
  const housing = box(3.2 * scale, 0.55 * scale, 3.2 * scale, mat(0x3f3f46));
  g.add(housing);
  const grille = box(2.6 * scale, 0.08 * scale, 2.6 * scale, mat(0x27272a));
  grille.position.y = 0.32 * scale;
  g.add(grille);
  for (let i = 0; i < 4; i++) {
    const blade = box(1.1 * scale, 0.05 * scale, 0.22 * scale, mat(0x52525b));
    const p = new THREE.Group();
    p.rotation.y = (i * Math.PI) / 2;
    blade.position.set(0.55 * scale, 0.15 * scale, 0);
    p.add(blade);
    g.add(p);
  }
  g.userData.tooltip = "Ventilador (pendiente de alimentación)";
  return g;
}
