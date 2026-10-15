/** Oculta solo el interior reservado; no altera materiales del exterior en esta fase. */
export function setExteriorView(groups) {
  if (groups.interiorGroup) groups.interiorGroup.visible = false;
}
