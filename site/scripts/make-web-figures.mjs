// Makes web copies (WebP, max 1200 px wide) of the original PNGs.
// Originals stay in public/figures for the "view full size" link.
import sharp from 'sharp';
import fs from 'node:fs';
import path from 'node:path';

const srcDir = 'public/figures';
const outDir = 'public/figures/web';
fs.mkdirSync(outDir, { recursive: true });
const meta = {};
for (const f of fs.readdirSync(srcDir).filter((n) => n.endsWith('.png')).sort()) {
  const id = path.basename(f, '.png');
  const orig = await sharp(path.join(srcDir, f)).metadata();
  const w = Math.min(1200, orig.width);
  const info = await sharp(path.join(srcDir, f))
    .resize({ width: w })
    .webp({ quality: 82 })
    .toFile(path.join(outDir, id + '.webp'));
  meta[id] = { width: info.width, height: info.height, origWidth: orig.width, origHeight: orig.height };
}
fs.writeFileSync('src/data/figures.json', JSON.stringify(meta, null, 2));
console.log(meta);
