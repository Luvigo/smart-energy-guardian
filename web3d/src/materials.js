import * as THREE from "three";

function canvasTex(draw, w = 256, h = 256) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = 4;
  return tex;
}

function mat(map, roughness, color = 0xffffff) {
  return new THREE.MeshStandardMaterial({
    map,
    color,
    roughness,
    metalness: 0.02,
    transparent: false,
    opacity: 1,
    depthWrite: true,
  });
}

/** Pared de cartón crema: fibras y variación suave, mate. */
export function cardboardWallMaterial() {
  const map = canvasTex((ctx, w, h) => {
    ctx.fillStyle = "#e7d3b4";
    ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 2200; i++) {
      const v = Math.floor(Math.random() * 28) - 12;
      ctx.fillStyle = `rgba(${210 + v}, ${188 + v}, ${150 + v}, 0.22)`;
      ctx.fillRect(Math.random() * w, Math.random() * h, 2 + Math.random() * 5, 1);
    }
    ctx.globalAlpha = 0.07;
    for (let y = 0; y < h; y += 2) {
      ctx.fillStyle = y % 8 === 0 ? "#8a6a45" : "#fff6e8";
      ctx.fillRect(0, y, w, 1);
    }
    ctx.globalAlpha = 1;
  });
  map.repeat.set(2.2, 1.6);
  return mat(map, 0.94);
}

/** Techo de cartón marrón con fibras longitudinales discretas. */
export function cardboardRoofMaterial() {
  const map = canvasTex((ctx, w, h) => {
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, "#8d6240");
    g.addColorStop(0.08, "#a8754e");
    g.addColorStop(0.92, "#a8754e");
    g.addColorStop(1, "#7a5436");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 0.16;
    for (let y = 0; y < h; y += 3) {
      ctx.fillStyle = y % 9 === 0 ? "#5c3b24" : "#c49268";
      ctx.fillRect(0, y, w, 1);
    }
    ctx.globalAlpha = 0.12;
    for (let i = 0; i < 400; i++) {
      ctx.fillStyle = "#6b4428";
      ctx.fillRect(Math.random() * w, Math.random() * h, 8 + Math.random() * 24, 1);
    }
    ctx.globalAlpha = 1;
  }, 256, 128);
  map.repeat.set(1.4, 2);
  return mat(map, 0.9);
}

/** Madera mate con veta suave (marcos, puerta, aleros, escalones). */
export function woodMaterial(tone = "mid") {
  const base = tone === "dark" ? [92, 58, 32] : tone === "light" ? [168, 124, 78] : [122, 78, 42];
  const map = canvasTex((ctx, w, h) => {
    ctx.fillStyle = `rgb(${base[0]}, ${base[1]}, ${base[2]})`;
    ctx.fillRect(0, 0, w, h);
    for (let x = 0; x < w; x += 2) {
      const n = Math.sin(x * 0.17) * 10 + Math.sin(x * 0.05) * 6;
      ctx.fillStyle = `rgba(${base[0] + n}, ${base[1] + n * 0.6}, ${base[2] + n * 0.3}, 0.28)`;
      ctx.fillRect(x, 0, 1, h);
    }
    ctx.globalAlpha = 0.08;
    for (let i = 0; i < 18; i++) {
      const x = (i * 37) % w;
      ctx.fillStyle = "#3a2414";
      ctx.fillRect(x, 0, 2, h);
    }
    ctx.globalAlpha = 1;
  }, 128, 256);
  map.repeat.set(1, 2);
  return mat(map, 0.86);
}

/** Césped con variación verde leve. */
export function grassMaterial() {
  const map = canvasTex((ctx, w, h) => {
    ctx.fillStyle = "#3d7a45";
    ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 3500; i++) {
      const g = 90 + Math.floor(Math.random() * 50);
      ctx.fillStyle = `rgba(${40 + Math.random() * 20}, ${g}, ${48 + Math.random() * 20}, 0.35)`;
      ctx.fillRect(Math.random() * w, Math.random() * h, 2, 3 + Math.random() * 4);
    }
  });
  map.repeat.set(4, 3);
  return mat(map, 0.96);
}

/** Vidrio azul opaco con un reflejo diagonal muy tenue. */
export function glassMaterial() {
  const map = canvasTex((ctx, w, h) => {
    ctx.fillStyle = "#7ea4c4";
    ctx.fillRect(0, 0, w, h);
    const g = ctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, "rgba(255,255,255,0.22)");
    g.addColorStop(0.35, "rgba(255,255,255,0)");
    g.addColorStop(1, "rgba(40,70,100,0.18)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
  }, 128, 128);
  return new THREE.MeshStandardMaterial({
    map,
    color: 0xd7e6f2,
    roughness: 0.28,
    metalness: 0.18,
    transparent: false,
    opacity: 1,
    depthWrite: true,
  });
}
