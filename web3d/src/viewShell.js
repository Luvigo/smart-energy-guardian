/** Fuerza opacidad total en todos los meshes de un grupo (fase exterior). */
function forceMeshOpaque(obj) {
  if (!obj.isMesh) return;
  const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
  mats.forEach((m) => {
    m.transparent = false;
    m.opacity = 1;
    m.depthWrite = true;
    m.needsUpdate = true;
  });
  obj.visible = true;
}

function opaqueGroup(group) {
  if (!group) return;
  group.visible = true;
  group.traverse(forceMeshOpaque);
}

/**
 * Modo exterior determinista: oculta interior y deja shell exterior opaco.
 * (La lógica de blend por zoom queda desactivada en main.js.)
 */
export function setExteriorView(groups) {
  if (groups.interiorGroup) groups.interiorGroup.visible = false;
  opaqueGroup(groups.roofGroup);
  opaqueGroup(groups.facadeShellGroup);
  opaqueGroup(groups.exteriorWallsGroup);
}
