// Remove light background from PNG icons — make it truly transparent
const sharp = require('sharp');
const path = require('path');

const files = ['runner', 'swimmer', 'biker', 'settings'];
const iconDir = 'C:/Users/simon/resilio-plus/frontend/icons';
const outDir = 'C:/Users/simon/resilio-plus/frontend/public/icons';

async function removeBg(name) {
  const input = path.join(iconDir, name + '.png');
  const output = path.join(outDir, name + '.png');

  const { data, info } = await sharp(input)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const { width, height, channels } = info;
  const pixels = new Uint8Array(data);

  // Sample background color from corner pixel
  const bgR = pixels[0], bgG = pixels[1], bgB = pixels[2];
  console.log(`${name}: bg sample = rgb(${bgR},${bgG},${bgB}), size ${width}x${height}`);

  // For each pixel: if close to background color → make transparent
  // Threshold: pixels that are lighter than the stroke color
  const threshold = 30; // how different from bg to keep as foreground

  for (let i = 0; i < width * height; i++) {
    const idx = i * channels;
    const r = pixels[idx], g = pixels[idx+1], b = pixels[idx+2];

    // Distance from background
    const dist = Math.sqrt(
      Math.pow(r - bgR, 2) +
      Math.pow(g - bgG, 2) +
      Math.pow(b - bgB, 2)
    );

    if (dist < threshold) {
      // Background pixel → make transparent
      pixels[idx + 3] = 0;
    } else {
      // Foreground pixel (stroke) → keep fully opaque
      // Also normalize stroke to pure black for clean inversion
      const darkness = Math.min(r, g, b);
      // Smooth alpha based on distance for anti-aliasing
      const alpha = Math.min(255, Math.round((dist / threshold) * 255 * 2));
      pixels[idx + 3] = Math.min(255, alpha);
    }
  }

  await sharp(Buffer.from(pixels), {
    raw: { width, height, channels }
  })
    .png()
    .toFile(output);

  console.log(`${name}: saved to ${output}`);
}

(async () => {
  for (const f of files) {
    await removeBg(f);
  }
  console.log('All done.');
})();
