// Shared helpers for both views.

export async function loadColors() {
  const res = await fetch("data/colors.json");
  if (!res.ok) throw new Error(`colors.json: ${res.status}`);
  return res.json();
}

export async function loadPaintings() {
  try {
    const res = await fetch("data/paintings.json");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}

// IIIF URL for the print area only (crop is relative x0,y0,x1,y1).
export function iiifUrl(img, width) {
  const [x0, y0, x1, y1] = img.crop;
  const pct = (v) => (v * 100).toFixed(2);
  return `${img.iiif}/pct:${pct(x0)},${pct(y0)},${pct(x1 - x0)},${pct(y1 - y0)}/${width},/0/default.jpg`;
}

function hsl(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
  if (d === 0) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return { h: (h * 60 + 360) % 360, s, l };
}

// Codebook indices in display order: chromatic colours by hue, then neutrals by lightness.
export function displayOrder(codebook) {
  const info = codebook.map((hex, i) => ({ i, ...hsl(hex) }));
  const neutral = (c) => c.s < 0.18;
  const chromatic = info.filter((c) => !neutral(c)).sort((a, b) => ((a.h + 330) % 360) - ((b.h + 330) % 360));
  const greys = info.filter(neutral).sort((a, b) => b.l - a.l);
  return [...chromatic, ...greys].map((c) => c.i);
}

// Top n colours of a share vector, as [{index, hex, share}].
export function topColours(shares, codebook, n = 6) {
  return shares
    .map((share, index) => ({ index, hex: codebook[index], share }))
    .sort((a, b) => b.share - a.share)
    .slice(0, n);
}

export function paletteHtml(colours) {
  return colours
    .map(
      (c) =>
        `<div class="swatch" style="flex:${c.share * 100};background:${c.hex}" title="${c.hex} · ${(c.share * 100).toFixed(1)}%">` +
        `<span>${c.hex}<br>${(c.share * 100).toFixed(1)}%</span></div>`
    )
    .join("");
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`);
}
