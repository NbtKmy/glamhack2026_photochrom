# Photochrom Colours

GLAMhack 2026 project. Which colours did the Zurich photochrom printers use, how did that change
over the years, and how far did their art reproductions drift from the original paintings?

Two static pages:

- **Colour bands by year** (`site/index.html`): one band per year, each layer is the share of one
  colour across that year's prints. Click a layer to list the prints richest in that colour, then a
  print to see its palette.
- **Photochrom vs painting** (`site/compare.html`): an art reproduction laid over the painting it
  copies. Drag, rotate and zoom to align it by hand, then fade it or switch to difference blending.

## Data

- Photochroms: Zentralbibliothek Zürich, *Photochrom Collection of the Zentralbibliothek Zürich*,
  v1.1, Zenodo, <https://doi.org/10.5281/zenodo.24141227>. Metadata CC0 1.0, images Public Domain
  Mark 1.0. Only the 1,952 *recatalogued* records are used (new scans, all on e-rara.ch), so the
  scan conditions are comparable.
- Images are shown from e-rara via IIIF; nothing is copied into this repository.
- Original paintings: Wikimedia Commons, found through Wikidata (GND ID → P227 → P18), plus
  hand-picked entries.

## How the colours are computed

1. Each scan is cropped to the print (the grey backdrop and the colour chart are removed).
2. A shared palette of 28 colours is learned with k-means in CIELAB over pixels from all prints,
   weighted towards saturated pixels so blues, greens and reds get their own colours.
3. Every print gets its share of each of the 28 colours (greys and paper count less).
4. Catalogue dates: a single year counts fully; a range of up to 10 years is spread evenly over its
   years; wider ranges (e.g. `1891/1914`) go to the *no date* band. Art reproductions are left out of
   the bands unless the checkbox is ticked.

Outputs in `site/data/`:

- `colors.json`: the shared palette and, per print, metadata, crop box and colour shares (used by the site).
- `features.json`: per print, its own 6-colour palette, mean Lab, lightness spread, mean chroma,
  colourfulness, a 12-bin hue histogram and its shares of the shared palette (for research).
- `paintings.json`: original paintings with their colour shares.

## Rebuild

Requires [uv](https://docs.astral.sh/uv/).

```sh
mkdir -p data
curl -L -o data/images-recatalogued-preview.zip \
  https://zenodo.org/api/records/24141227/files/images-recatalogued-preview.zip/content
curl -L -o data/photochrom-metadata.csv \
  https://zenodo.org/api/records/24141227/files/photochrom-metadata.csv/content

uv run glamhack2026-photochrom                    # colours, features and paintings
uv run glamhack2026-photochrom --paintings-only   # paintings only
uv run pytest
```

Extra paintings can be listed in `data/paintings-extra.csv` with the columns
`id,image,work,artist,source` (`id` is the MMS ID of the photochrom record).

## View locally

```sh
uv run python -m http.server -d site 8000
```

Then open <http://localhost:8000/>.
