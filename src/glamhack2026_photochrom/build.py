"""Preprocess the recatalogued photochroms into site/data/colors.json."""

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from .crop import crop_print
from .dates import year_weights
from .features import image_features
from .palette import build_codebook, color_shares, lab_to_hex, rgb_to_lab

_SAMPLES_PER_IMAGE = 500
_LONG_SIDE = 200


def _first(value: str) -> str:
    return value.split(" | ")[0].strip()


def _is_art(row: dict) -> bool:
    topic = row["subject_topic"]
    return "Gemälde" in topic or "Reproduktion" in topic or bool(row["subject_title_of_work"].strip())


def load_records(csv_path: Path) -> list[dict]:
    """Recatalogued records with the fields the site needs."""
    records = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["subset"] != "recatalogued":
                continue
            iiif = _first(row["iiif_image_uris"]).removesuffix("/full/full/0/default.jpg")
            vlid = Path(_first(row["image_files"])).stem
            records.append(
                {
                    "id": row["identifier_swisscollections"],
                    "title": row["title"],
                    "date": row["date_of_publication_or_production"],
                    "years": year_weights(row["date_of_publication_or_production_standardised"]),
                    "art": _is_art(row),
                    "iiif": iiif,
                    "image_file": f"images-recatalogued-preview/{vlid}.jpg",
                    "place": row["subject_geographical_entity"].split("###")[0].split(", ID:")[0],
                    "erara": f"https://www.e-rara.ch/id/{vlid}",
                }
            )
    return records


def _pixels(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    img.thumbnail((_LONG_SIDE, _LONG_SIDE))
    return np.asarray(img, dtype=np.uint8).reshape(-1, 3)


def run(
    data_dir: Path = Path("data"), out: Path = Path("site/data/colors.json"), k: int = 28
) -> None:
    records = load_records(data_dir / "photochrom-metadata.csv")
    rng = np.random.default_rng(0)
    kept, pixels, samples = [], [], []
    with zipfile.ZipFile(data_dir / "images-recatalogued-preview.zip") as z:
        names = set(z.namelist())
        for rec in records:
            if rec["image_file"] not in names:
                print(f"missing image for {rec['id']}: {rec['image_file']}", file=sys.stderr)
                continue
            cropped, box = crop_print(Image.open(io.BytesIO(z.read(rec["image_file"]))))
            px = _pixels(cropped)
            samples.append(px[rng.choice(len(px), min(_SAMPLES_PER_IMAGE, len(px)), replace=False)])
            pixels.append(px)
            kept.append({**rec, "crop": [round(float(b), 4) for b in box]})

    codebook = build_codebook(rgb_to_lab(np.concatenate(samples)), k=k)
    codebook_hex = [lab_to_hex(c) for c in codebook]
    images, features = [], []
    for rec, px in zip(kept, pixels):
        shares = [round(float(s), 3) for s in color_shares(rgb_to_lab(px), codebook)]
        rec = {key: v for key, v in rec.items() if key != "image_file"}
        rec["years"] = {str(y): w for y, w in rec["years"].items()} if rec["years"] else None
        images.append({**rec, "shares": shares})
        features.append(
            {"id": rec["id"], "title": rec["title"], "date": rec["date"], "crop": rec["crop"],
             "codebook_shares": shares, **image_features(px)}
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, {"codebook": codebook_hex, "images": images})
    # Research copy: every image's own palette and colour statistics, plus the shared codebook.
    _write_json(out.parent / "features.json", {"codebook": codebook_hex, "images": features}, indent=1)
    print(f"wrote {len(images)} images, {k} colours -> {out}", file=sys.stderr)


def _write_json(path: Path, data: dict, indent: int | None = None) -> None:
    separators = None if indent else (",", ":")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent, separators=separators), encoding="utf-8")
