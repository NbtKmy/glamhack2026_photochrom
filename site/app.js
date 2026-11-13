// View 1: colour bands per year -> images with that colour -> detail with palette.
import { displayOrder, escapeHtml, iiifUrl, loadColors, loadPaintings, paletteHtml, topColours } from "./common.js";

const UNDATED = "undated";
const SPARSE_N = 10; // bands with fewer records are drawn faded
const MAX_RESULTS = 60;

const $ = (id) => document.getElementById(id);
const state = { data: null, paintings: new Map(), order: [], bands: [], band: null, colour: null, image: null };

function buildBands(images, includeArt) {
  const k = state.data.codebook.length;
  const byKey = new Map();
  const add = (key, img, w) => {
    if (!byKey.has(key)) byKey.set(key, { key, n: 0, sums: new Array(k).fill(0), members: [] });
    const b = byKey.get(key);
    b.n += w;
    img.shares.forEach((s, i) => (b.sums[i] += s * w));
    b.members.push(img);
  };
  for (const img of images) {
    if (img.art && !includeArt) continue;
    if (img.years) for (const [y, w] of Object.entries(img.years)) add(y, img, w);
    else add(UNDATED, img, 1);
  }
  const bands = [...byKey.values()].map((b) => ({ ...b, shares: b.sums.map((s) => s / b.n) }));
  return bands.sort((a, b) => (a.key === UNDATED) - (b.key === UNDATED) || a.key.localeCompare(b.key));
}

function renderBands() {
  const { codebook } = state.data;
  $("bands").innerHTML = state.bands
    .map((b) => {
      const layers = state.order
        .map((i) =>
          `<div class="layer${state.band === b.key && state.colour === i ? " selected" : ""}" data-band="${b.key}" data-colour="${i}"` +
          ` style="flex:${b.shares[i]};background:${codebook[i]}" title="${codebook[i]} · ${(b.shares[i] * 100).toFixed(1)}%"></div>`)
        .join("");
      const label = b.key === UNDATED ? "no<br>date" : b.key;
      return `<div class="band${b.key === UNDATED ? " undated" : ""}${b.n < SPARSE_N ? " sparse" : ""}">` +
        `<div class="stack">${layers}</div><div class="label"><b>${label}</b>${b.n < 1 ? "<1" : Math.round(b.n)}</div></div>`;
    })
    .join("");
}

function showPalette(label, shares) {
  $("paletteLabel").innerHTML = label;
  $("palette").innerHTML = paletteHtml(topColours(shares, state.data.codebook));
}

function selectLayer(bandKey, colour) {
  state.band = bandKey;
  state.colour = colour;
  const band = state.bands.find((b) => b.key === bandKey);
  const hex = state.data.codebook[colour];
  const members = [...new Set(band.members)].filter((img) => img.shares[colour] >= 0.005).sort((a, b) => b.shares[colour] - a.shares[colour]).slice(0, MAX_RESULTS);
  const where = bandKey === UNDATED ? "undated" : bandKey;
  $("resultsTitle").innerHTML = `<span class="chip" style="background:${hex}"></span>Prints rich in ${hex} · ${where} (top ${members.length})`;
  $("thumbs").innerHTML = members
    .map((img) =>
      `<button data-id="${img.id}" title="${escapeHtml(img.title)}"><img loading="lazy" src="${iiifUrl(img, 200)}" alt="${escapeHtml(img.title)}">` +
      `<span class="pct">${(img.shares[colour] * 100).toFixed(0)}%</span></button>`)
    .join("");
  $("results").hidden = false;
  showPalette(`Colours of ${where}<br>(n=${band.n.toFixed(1)})`, band.shares);
  renderBands();
  $("results").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function selectImage(id) {
  const img = state.data.images.find((i) => i.id === id);
  state.image = img;
  const painting = state.paintings.get(img.id);
  $("detail").innerHTML =
    `<div><img src="${iiifUrl(img, 800)}" alt="${escapeHtml(img.title)}"></div>` +
    `<div><h3>${escapeHtml(img.title)}</h3>` +
    `<div class="palette">${paletteHtml(topColours(img.shares, state.data.codebook))}</div>` +
    `<dl><dt>Date</dt><dd>${escapeHtml(img.date)}</dd><dt>Place</dt><dd>${escapeHtml(img.place || "—")}</dd>` +
    `<dt>Type</dt><dd>${img.art ? "Art reproduction" : "View / scene"}</dd></dl>` +
    `<p><a href="${img.erara}" target="_blank" rel="noopener">View on e-rara</a>` +
    (painting ? ` · <a href="compare.html?id=${img.id}">Compare with the painting</a>` : "") + `</p></div>`;
  $("detail").hidden = false;
  showPalette(escapeHtml(img.title.slice(0, 60)), img.shares);
  $("detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function refresh() {
  state.bands = buildBands(state.data.images, $("includeArt").checked);
  const total = state.bands.reduce((s, b) => s + b.n, 0);
  $("status").textContent = `${Math.round(total)} prints counted`;
  if (state.band && state.colour !== null && state.bands.some((b) => b.key === state.band)) selectLayer(state.band, state.colour);
  else renderBands();
}

async function main() {
  try {
    state.data = await loadColors();
  } catch (e) {
    $("status").textContent = `Could not load data: ${e.message}`;
    return;
  }
  state.paintings = new Map((await loadPaintings()).map((p) => [p.id, p]));
  state.order = displayOrder(state.data.codebook);
  $("bands").addEventListener("click", (e) => {
    const layer = e.target.closest(".layer");
    if (layer) selectLayer(layer.dataset.band, Number(layer.dataset.colour));
  });
  $("thumbs").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-id]");
    if (btn) selectImage(btn.dataset.id);
  });
  $("includeArt").addEventListener("change", refresh);
  refresh();
  const all = buildBands(state.data.images, true).reduce((acc, b) => acc.map((s, i) => s + b.shares[i] * b.n), new Array(state.data.codebook.length).fill(0));
  const sum = all.reduce((a, b) => a + b, 0);
  showPalette("Whole collection", all.map((s) => s / sum));
}

main();
