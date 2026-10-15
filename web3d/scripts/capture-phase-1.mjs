/**
 * Regenera las evidencias finales de FASE 1 en docs/phase-1/final/.
 * Requiere: npm run build && npm run preview (o PREVIEW_URL).
 * Dependencia opcional: npx playwright install chromium
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const finalDir = path.join(__dirname, "..", "docs", "phase-1", "final");
const baseUrl = process.env.PREVIEW_URL || "http://127.0.0.1:4173";

const ROOF_Y = 14;
const FACADE_Y = 0.45;
const FACADE_Z = -11.8;

const shots = [
  { file: "exterior-cerrado-frontal.png", preset: "exteriorFront", exploded: false },
  { file: "exterior-cerrado-tres-cuartos.png", preset: "exteriorThreeQuarter", exploded: false },
  { file: "exterior-cerrado-lateral.png", preset: "exteriorRight", exploded: false },
  { file: "exterior-desmontado-frontal.png", preset: "explodedFront", exploded: true },
  { file: "exterior-desmontado-tres-cuartos.png", preset: "explodedThreeQuarter", exploded: true },
];

await mkdir(finalDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto(baseUrl, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__viewer?.camera && window.houseParts);

for (const shot of shots) {
  await page.evaluate(
    ({ preset, exploded, roofY, facadeY, facadeZ }) => {
      window.__viewer.resetAll();
      if (exploded) {
        window.__viewer.setExteriorExploded();
        const g = window.houseParts.groups;
        g.removableRoof.position.set(0, roofY, 0);
        g.removableFacade.position.set(0, facadeY, facadeZ);
        const slots = window.__viewer.house.getObjectByName("facadeBaseSlots");
        if (slots) slots.visible = true;
      }
      window.__viewer.applyCameraPreset(preset);
    },
    { ...shot, roofY: ROOF_Y, facadeY: FACADE_Y, facadeZ: FACADE_Z },
  );
  await page.waitForTimeout(shot.exploded ? 450 : 550);
  await page.screenshot({ path: path.join(finalDir, shot.file) });
  console.log("Wrote", shot.file);
}

await page.click("#btn-reset");
await page.waitForTimeout(400);
await page.click("#btn-exploded");
await page.waitForFunction(
  () => {
    const r = window.houseParts.groups.removableRoof.position.y;
    const f = window.houseParts.groups.removableFacade.position.z;
    return r > 13.6 && f < -11.2;
  },
  { timeout: 20000 },
);
await page.waitForTimeout(400);
await page.evaluate(() => window.__viewer.applyCameraPreset("explodedThreeQuarter"));
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(finalDir, "interior-divisor-franja-libre.png") });
console.log("Wrote interior-divisor-franja-libre.png");

await browser.close();
