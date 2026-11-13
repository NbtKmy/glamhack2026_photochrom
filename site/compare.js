// View 2: lay a photochrom over its original painting and align it by hand.
import { escapeHtml, iiifUrl, loadColors, loadPaintings, paletteHtml, topColours } from "./common.js";

const $ = (id) => document.getElementById(id);
const view = { x: 0, y: 0, rotate: 0, scale: 1 };
let data, paintings, imagesById;

function applyTransform() {
  $("overlay").style.transform =
    `translate(-50%, -50%) translate(${view.x}px, ${view.y}px) rotate(${view.rotate}deg) scale(${view.scale})`;
  $("rotate").value = view.rotate;
  $("scale").value = view.scale;
}

function reset() {
  Object.assign(view, { x: 0, y: 0, rotate: 0, scale: 1 });
  fitOverlay();
  applyTransform();
}

// Start with the photochrom at the painting's displayed size, so only fine-tuning is left.
function fitOverlay() {
  const p = $("painting"), o = $("overlay");
  if (!p.naturalWidth || !o.naturalWidth) return;
  const pr = p.getBoundingClientRect();
  const fit = Math.min(pr.width / o.naturalWidth, pr.height / o.naturalHeight);
  o.style.width = `${o.naturalWidth * fit}px`;
  o.style.maxWidth = "none";
  o.style.maxHeight = "none";
}

function select(id) {
  const painting = paintings.find((p) => p.id === id);
  const img = imagesById.get(id);
  if (!painting || !img) return;
  history.replaceState(null, "", `?id=${encodeURIComponent(id)}`);
  document.querySelectorAll("#list button").forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  $("painting").src = painting.image;
  $("overlay").src = iiifUrl(img, 1200);
  $("painting").alt = `${painting.work} by ${painting.artist}`;
  $("overlay").alt = img.title;
  $("meta").innerHTML =
    `<p><b>${escapeHtml(painting.work)}</b> · ${escapeHtml(painting.artist)}<br>` +
    `Photochrom: ${escapeHtml(img.title)} (${escapeHtml(img.date)}) · <a href="${img.erara}" target="_blank" rel="noopener">e-rara</a> · ` +
    `Painting image: ${escapeHtml(painting.source)}</p>`;
  $("palPhotochrom").innerHTML = paletteHtml(topColours(img.shares, data.codebook));
  $("palPainting").innerHTML = paletteHtml(topColours(painting.shares, data.codebook));
  reset();
}

function wireStage() {
  const overlay = $("overlay");
  let drag = null;
  overlay.addEventListener("pointerdown", (e) => {
    overlay.setPointerCapture(e.pointerId);
    drag = { x: e.clientX, y: e.clientY, rotate: e.shiftKey, start: { ...view } };
  });
  overlay.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (drag.rotate) view.rotate = drag.start.rotate + dx * 0.1;
    else Object.assign(view, { x: drag.start.x + dx, y: drag.start.y + dy });
    applyTransform();
  });
  overlay.addEventListener("pointerup", () => (drag = null));
  $("stage").addEventListener("wheel", (e) => {
    e.preventDefault();
    const step = e.altKey ? 0.002 : 0.01; // Alt for fine zoom
    view.scale = Math.min(3, Math.max(0.3, view.scale * (1 - Math.sign(e.deltaY) * step * 3)));
    applyTransform();
  }, { passive: false });
  $("opacity").addEventListener("input", (e) => (overlay.style.opacity = e.target.value / 100));
  $("rotate").addEventListener("input", (e) => { view.rotate = Number(e.target.value); applyTransform(); });
  $("scale").addEventListener("input", (e) => { view.scale = Number(e.target.value); applyTransform(); });
  $("difference").addEventListener("change", (e) => (overlay.style.mixBlendMode = e.target.checked ? "difference" : "normal"));
  $("reset").addEventListener("click", reset);
  $("painting").addEventListener("load", reset);
  overlay.addEventListener("load", reset);
  overlay.style.opacity = 0.5;
}

async function main() {
  [data, paintings] = await Promise.all([loadColors(), loadPaintings()]);
  imagesById = new Map(data.images.map((i) => [i.id, i]));
  paintings = paintings.filter((p) => imagesById.has(p.id));
  if (!paintings.length) {
    $("meta").textContent = "No paintings available yet.";
    return;
  }
  $("list").innerHTML = paintings
    .map((p) => `<button data-id="${p.id}"><img loading="lazy" src="${iiifUrl(imagesById.get(p.id), 120)}" alt="">` +
      `<span>${escapeHtml(p.work)}<br><small>${escapeHtml(p.artist)}</small></span></button>`)
    .join("");
  $("list").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-id]");
    if (btn) select(btn.dataset.id);
  });
  wireStage();
  const wanted = new URLSearchParams(location.search).get("id");
  select(paintings.some((p) => p.id === wanted) ? wanted : paintings[0].id);
}

main();
