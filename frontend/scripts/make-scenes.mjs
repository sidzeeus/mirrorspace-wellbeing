/**
 * Writes the still images of the dithered scenes into public/scenes.
 * Run after changing src/components/scene/fields.ts:  node scripts/make-scenes.mjs
 *
 * These stills are what people see with reduced motion, without JavaScript, or
 * before the animated canvas starts. The PNG files are committed, so this is not part
 * of the build. Needs Node 22.18 or newer (it imports the TypeScript file directly).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

import { PALETTE, sample, tone } from "../src/components/scene/fields.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// SCENE_PREVIEW=<folder> writes opaque copies there instead, for looking at while editing.
const preview = process.env.SCENE_PREVIEW;
const out = preview ?? path.join(root, "public", "scenes");
mkdirSync(out, { recursive: true });

const CELL = 3; // pixels per cell
const DOT = 2; // pixels of each cell that are filled

// [scene, suffix, columns, rows]
const SIZES = [
  ["held", "l", 440, 260],
  ["held", "p", 200, 320],
  ["point", "s", 220, 165],
  ["figure", "s", 220, 165],
  ["pair", "s", 220, 165],
  ["terrain", "l", 440, 130],
  ["terrain", "p", 200, 130],
];

const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
function crc(buffer) {
  let c = 0xffffffff;
  for (const byte of buffer) c = crcTable[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const check = Buffer.alloc(4);
  check.writeUInt32BE(crc(body));
  return Buffer.concat([length, body, check]);
}

/** An indexed PNG: palette entry 0 is transparent, 1..n are the tones. */
function png(width, height, pixels, colors) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header.set([8, 3, 0, 0, 0], 8);
  const palette = Buffer.from([0, 0, 0, ...colors.flat()]);
  const rows = Buffer.alloc((width + 1) * height);
  for (let y = 0; y < height; y += 1) {
    pixels.copy(rows, y * (width + 1) + 1, y * width, (y + 1) * width);
  }
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("PLTE", palette),
    ...(preview ? [] : [chunk("tRNS", Buffer.from([0]))]),
    chunk("IDAT", deflateSync(rows, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

let total = 0;
for (const [scene, suffix, columns, rows] of SIZES) {
  const width = columns * CELL;
  const height = rows * CELL;
  const aspect = columns / rows;
  const pixels = Buffer.alloc(width * height);
  for (let j = 0; j < rows; j += 1) {
    for (let i = 0; i < columns; i += 1) {
      const x = (((i + 0.5) / columns) * 2 - 1) * aspect;
      const y = ((j + 0.5) / rows) * 2 - 1;
      const value = sample(scene, x, y, aspect);
      const index = tone(value.still + value.glow, i, j);
      if (index < 0) continue;
      for (let dy = 0; dy < DOT; dy += 1) {
        for (let dx = 0; dx < DOT; dx += 1) {
          pixels[(j * CELL + dy) * width + i * CELL + dx] = index + 1;
        }
      }
    }
  }
  for (const theme of ["night", "daybreak"]) {
    const file = png(width, height, pixels, PALETTE[theme].map((color) => [...color]));
    writeFileSync(path.join(out, `${scene}-${theme}-${suffix}.png`), file);
    total += file.length;
  }
}
console.log(`Wrote ${SIZES.length * 2} scenes to ${out} (${Math.round(total / 1024)} KB in total)`);
