// Normalize icons: trim content, add uniform padding, output same square size
const sharp = require('sharp');
const path = require('path');

const files = ['runner', 'swimmer', 'biker', 'settings'];
const srcDir = 'C:/Users/simon/resilio-plus/frontend/public/icons';
const outSize = 400; // final square size px
const paddingPct = 0.12; // 12% padding on each side

async function normalize(name) {
  const input = path.join(srcDir, name + '.png');

  // Trim transparent pixels, then resize with padding into a square
  const trimmed = await sharp(input)
    .trim({ threshold: 10 }) // remove near-transparent edges
    .toBuffer();

  const meta = await sharp(trimmed).metadata();
  const w = meta.width, h = meta.height;

  // Fit the trimmed image inside a square with padding
  const padding = Math.round(outSize * paddingPct);
  const fitSize = outSize - padding * 2;

  // Scale to fit within fitSize × fitSize, preserving aspect ratio
  const scale = Math.min(fitSize / w, fitSize / h);
  const newW = Math.round(w * scale);
  const newH = Math.round(h * scale);

  const padLeft = Math.round((outSize - newW) / 2);
  const padTop = Math.round((outSize - newH) / 2);

  await sharp(trimmed)
    .resize(newW, newH, { fit: 'fill' })
    .extend({
      top: padTop,
      bottom: outSize - newH - padTop,
      left: padLeft,
      right: outSize - newW - padLeft,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .png()
    .toFile(input); // overwrite in place

  console.log(`${name}: ${w}×${h} → trimmed → ${newW}×${newH} → ${outSize}×${outSize}`);
}

(async () => {
  for (const f of files) await normalize(f);
  console.log('All normalized.');
})();
