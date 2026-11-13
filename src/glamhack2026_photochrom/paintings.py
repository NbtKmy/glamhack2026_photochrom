"""Find the original paintings of art reproductions -> site/data/paintings.json."""

import csv
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from .palette import color_shares, rgb_to_lab

_UA = "photochrom-glamhack/0.1"
_SPARQL = "https://query.wikidata.org/sparql?format=json&query="


def urllib_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read()


def gnd_ids(record_row: dict) -> list[str]:
    return re.findall(r"\(DE-588\)([0-9A-Za-z-]+)", record_row["subject_title_of_work"])


def _work_and_artist(title_of_work: str) -> tuple[str, str]:
    first = title_of_work.split("###")[0].split(", ID:")[0]
    first = first.replace("<<", "").replace(">>", "")  # catalogue non-sorting markup
    work, _, artist = first.partition(" / ")
    return work.strip(), re.sub(r"\s*\(.*\)$", "", artist).strip()


def _with_width(url: str, width: int) -> str:
    return f"{url}?width={width}"


def _shares(image_bytes: bytes, codebook_lab: np.ndarray) -> list[float]:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((200, 200))
    lab = rgb_to_lab(np.asarray(img, dtype=np.uint8).reshape(-1, 3))
    return [round(float(s), 3) for s in color_shares(lab, codebook_lab)]


def run(
    data_dir: Path = Path("data"),
    colors: Path = Path("site/data/colors.json"),
    out: Path = Path("site/data/paintings.json"),
    fetch: Callable[[str], bytes] = urllib_fetch,
) -> None:
    codebook = json.loads(colors.read_text(encoding="utf-8"))["codebook"]
    codebook_lab = rgb_to_lab(np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in codebook], dtype=np.uint8))

    by_gnd: dict[str, list[dict]] = {}
    rows: dict[str, dict] = {}
    with open(data_dir / "photochrom-metadata.csv", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["subset"] != "recatalogued":
                continue
            rows[row["identifier_swisscollections"]] = row
            for g in gnd_ids(row):
                by_gnd.setdefault(g, []).append(row)

    candidates = []  # (mms id, image url, work, artist, source)
    if by_gnd:
        values = " ".join(f'"{g}"' for g in by_gnd)
        query = f"SELECT ?g ?item ?img WHERE {{ VALUES ?g {{ {values} }} ?item wdt:P227 ?g . ?item wdt:P18 ?img }}"
        seen_gnd = set()
        for b in json.loads(fetch(_SPARQL + urllib.parse.quote(query)))["results"]["bindings"]:
            g = b["g"]["value"]
            if g in seen_gnd:  # several images for one work: keep the first
                continue
            seen_gnd.add(g)
            image = b["img"]["value"].replace("http://", "https://", 1)
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            for row in by_gnd[g]:
                work, artist = _work_and_artist(row["subject_title_of_work"])
                candidates.append((row["identifier_swisscollections"], _with_width(image, 1200), work, artist,
                                   f"wikidata:{qid}", _with_width(image, 400)))

    extra = data_dir / "paintings-extra.csv"
    if extra.exists():
        with open(extra, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row["id"] not in rows:
                    print(f"paintings-extra: unknown record {row['id']}", file=sys.stderr)
                    continue
                candidates.append((row["id"], row["image"], row["work"], row["artist"], row["source"], row["image"]))

    paintings, done = [], set()
    for mms, image, work, artist, source, thumb in candidates:
        if mms in done:
            continue
        try:
            shares = _shares(fetch(thumb), codebook_lab)
        except Exception as e:  # one unreachable image must not stop the rest
            print(f"skip {mms} ({work}): {e}", file=sys.stderr)
            continue
        done.add(mms)
        paintings.append({"id": mms, "work": work, "artist": artist, "image": image, "source": source, "shares": shares})

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(paintings, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(paintings)} paintings -> {out}", file=sys.stderr)
