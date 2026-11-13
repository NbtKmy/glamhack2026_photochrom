import io
import json

from PIL import Image

from glamhack2026_photochrom.paintings import gnd_ids, run
from test_build import _COLUMNS, _row
import csv


def test_gnd_ids():
    row = {"subject_title_of_work": "Danae / Vecellio, Tiziano (1477-1576), ID: (DE-588)4791704-0"}
    assert gnd_ids(row) == ["4791704-0"]


def _csv(tmp_path):
    with open(tmp_path / "photochrom-metadata.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLUMNS)
        w.writeheader()
        w.writerow(_row("991000000000000011", "recatalogued", "1",
                        subject_title_of_work="Danae / Vecellio, Tiziano (1477-1576), ID: (DE-588)AAA"))
        w.writerow(_row("991000000000000012", "recatalogued", "2",
                        subject_title_of_work="Venus / Cabanel, Alexandre (1823-1889), ID: (DE-588)BBB"))


def colors_json(tmp_path):
    path = tmp_path / "colors.json"
    path.write_text(json.dumps({"codebook": ["#ff0000", "#0000ff"], "images": []}))
    return path


def stub_fetch(url: str) -> bytes:
    if "query.wikidata.org" in url:
        return json.dumps({"results": {"bindings": [
            {"g": {"value": "AAA"}, "item": {"value": "http://www.wikidata.org/entity/Q1"},
             "img": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/A.jpg"}},
            {"g": {"value": "BBB"}, "item": {"value": "http://www.wikidata.org/entity/Q2"},
             "img": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/B.jpg"}},
        ]}}).encode()
    if "A.jpg" in url:
        buf = io.BytesIO()
        Image.new("RGB", (40, 30), (220, 20, 20)).save(buf, "JPEG")
        return buf.getvalue()
    raise OSError(f"cannot fetch {url}")


def test_run_skips_failed_image_fetch(tmp_path):
    _csv(tmp_path)
    run(tmp_path, colors_json(tmp_path), tmp_path / "p.json", fetch=stub_fetch)
    out = json.loads((tmp_path / "p.json").read_text())
    assert len(out) == 1
    p = out[0]
    assert p["id"] == "991000000000000011"
    assert p["work"] == "Danae" and p["artist"] == "Vecellio, Tiziano"
    assert p["image"] == "https://commons.wikimedia.org/wiki/Special:FilePath/A.jpg?width=1200"
    assert p["source"] == "wikidata:Q1"
    assert p["shares"][0] > 0.9  # red painting -> red codebook colour


def test_run_adds_extra_csv(tmp_path):
    _csv(tmp_path)
    (tmp_path / "paintings-extra.csv").write_text(
        "id,image,work,artist,source\n"
        "991000000000000012,https://example.org/A.jpg,Venus,\"Cabanel, Alexandre\",colleague list\n",
        encoding="utf-8",
    )
    run(tmp_path, colors_json(tmp_path), tmp_path / "p.json", fetch=stub_fetch)
    ids = [p["id"] for p in json.loads((tmp_path / "p.json").read_text())]
    assert ids == ["991000000000000011", "991000000000000012"]


def test_work_and_artist_strips_catalogue_markup():
    from glamhack2026_photochrom.paintings import _work_and_artist
    assert _work_and_artist(
        "<<Die>> bekleidete Maja / Goya y Lucientes, Francisco José <<de>> (1746-1828), ID: (DE-588)x"
    ) == ("Die bekleidete Maja", "Goya y Lucientes, Francisco José de")
