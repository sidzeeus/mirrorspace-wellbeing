/**
 * Renders the PWA icons from src/app/icon.svg into public/icons.
 * Run after changing the icon:  node scripts/make-icons.mjs
 * The PNG files are committed, so this is not part of the build.
 */
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const svg = readFileSync(path.join(root, "src", "app", "icon.svg"), "utf8");
const out = path.join(root, "public", "icons");
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
for (const [name, size, padding] of [
  ["icon-192.png", 192, 0],
  ["icon-512.png", 512, 0],
  // Maskable icons need a safe zone: the artwork sits inside the middle 80%.
  ["icon-maskable-512.png", 512, 0.1],
]) {
  const page = await browser.newPage({ viewport: { width: size, height: size } });
  const inner = Math.round(size * (1 - padding * 2));
  await page.setContent(
    `<body style="margin:0;background:#06070c;display:grid;place-items:center;height:${size}px">
       <div style="width:${inner}px;height:${inner}px">${svg}</div>
     </body>`,
  );
  await page.screenshot({ path: path.join(out, name) });
  await page.close();
}
await browser.close();
console.log(`Wrote icons to ${out}`);
