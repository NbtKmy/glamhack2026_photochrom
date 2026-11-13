import csv
import io
import json
import zipfile

import pytest

from glamhack2026_photochrom.build import load_records, run
from test_crop import _scan

_COLUMNS = [
    "identifier_swisscollections", "title", "date_of_publication_or_production",
    "date_of_publication_or_production_standardised", "subject_topic", "subject_title_of_work",
    "subject_geographical_entity", "subset", "image_files", "iiif_image_uris",
]


def _row(mms, subset, vlid, **kw):
    row = dict.fromkeys(_COLUMNS, "")
    row.update(
        identifier_swisscollections=mms, title=f"Title {mms}", subset=subset,
        date_of_publication_or_production="[1897]",
        date_of_publication_or_production_standardised="1897",
        subject_geographical_entity="Genf, ID: (DE-588)4020137-5###Schweiz, ID: (DE-588)x",
        image_files=f"images-{subset}-4k/{vlid}.jpg",
        iiif_image_uris=f"https://www.e-rara.ch/i3f/v21/{vlid}/full/full/0/default.jpg",
    )
    row.update(kw)
    return row


def make_csv(tmp_path):
    path = tmp_path / "photochrom-metadata.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLUMNS)
        w.writeheader()
        w.writerow(_row("991000000000000001", "recatalogued", "30418784"))
        w.writerow(_row("991000000000000002", "recatalogued", "99999999",
                        subject_title_of_work="Danae / Vecellio, Tiziano"))
        w.writerow(_row("991000000000000003", "legacy", "400013004"))
    return path


def make_zip(tmp_path):
    buf = io.BytesIO()
    _scan().save(buf, "JPEG")
    with zipfile.ZipFile(tmp_path / "images-recatalogued-preview.zip", "w") as z:
        z.writestr("images-recatalogued-preview/30418784.jpg", buf.getvalue())


def test_load_records_filters_and_parses(tmp_path):
    recs = load_records(make_csv(tmp_path))
    assert [r["id"] for r in recs] == ["991000000000000001", "991000000000000002"]
    assert recs[0]["iiif"] == "https://www.e-rara.ch/i3f/v21/30418784"
    assert recs[0]["image_file"] == "images-recatalogued-preview/30418784.jpg"
    assert recs[0]["erara"] == "https://www.e-rara.ch/id/30418784"
    assert recs[0]["place"] == "Genf"
    assert recs[0]["years"] == {1897: 1.0}
    assert [r["art"] for r in recs] == [False, True]


def test_run_writes_json_and_skips_missing_image(tmp_path, capsys):
    make_csv(tmp_path)
    make_zip(tmp_path)
    out = tmp_path / "colors.json"
    run(tmp_path, out, k=2)
    data = json.loads(out.read_text())
    assert len(data["codebook"]) == 2 and len(data["images"]) == 1
    img = data["images"][0]
    assert sum(img["shares"]) == pytest.approx(1, abs=0.01)
    assert img["years"] == {"1897": 1.0}
    assert len(img["crop"]) == 4
    assert "missing" in capsys.readouterr().err
