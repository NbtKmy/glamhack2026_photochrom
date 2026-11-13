# Photochrom Colours Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 年代別の色の帯から photochrom を探せる画面と、絵画複製を元絵画に重ねて見比べる画面を、静的サイトとして作る。

**Architecture:** Python（uv）の前処理で、Zenodo の 800px プレビューからプリント部分を切り出し、全画像共通の色見本（Lab k-means）に対する色の割合を計算して `site/data/*.json` に出す。`site/` はビルドなしの HTML + JS で、JSON を読み、画像は e-rara IIIF から表示する。

**Tech Stack:** Python 3.13, uv, Pillow, numpy, scikit-learn, pytest / 素の HTML + JavaScript（ES modules）

**Spec:** `docs/superpowers/specs/2026-11-13-photochrom-colors-design.md`

## Global Constraints

- 対象は `subset == "recatalogued"` の記録のみ（1,952件）。
- 画像入力は `data/images-recatalogued-preview.zip`、メタデータは `data/photochrom-metadata.csv`。`data/` は git 管理外。画像はコミットしない。
- CSV のキー `identifier_swisscollections` は常に文字列として扱う。CSV 先頭列名には BOM が付く → `encoding="utf-8-sig"` で読む。
- 複数画像の記録は `iiif_image_uris` / `recatalogued_page_ids` の最初の1つを使う（区切りは ` | `）。
- 色見本の色数 `K = 28`、k-means の `random_state = 0`。
- 年代: 単年 → その年に重み 1。幅 2〜9年（例 `1902/1904`）→ 各年に `1/n`。幅 10年以上 or 解析不能 → 年代不明（`None`）。
- 絵画複製の判定: `subject_topic` に `Gemälde` か `Reproduktion` を含む、または `subject_title_of_work` が空でない。
- 絵画複製は年代の帯から既定で除外し、画面のチェックボックスで含められる。
- フロントエンドはビルドなし。外部ライブラリ不使用。

## Review Focus

1. プリントが背景グレーに近い画像（暗い夜景など）でクロップが失敗 → 画像全体の中央 80% にフォールバックし、空画像にしない。（Task 2 にテスト）
2. 想定外の日付文字列（`104 /1914`、空文字）→ 年代不明として扱い、落ちない。（Task 2 にテスト）
3. メタデータにあって zip にない画像 / `iiif_image_uris` が空の記録（5件）→ 警告を出してスキップし、処理は続行。（Task 3 にテスト）
4. 件数が極端に少ない年（1890年 5件）→ 帯に件数 n を表示し、割合だけで誤解させない。（Task 4 の確認項目）
5. Commons の絵画画像が取得できない → その作品だけスキップし、`paintings.json` の他の作品は出す。（Task 5 にテスト）

---

### Task 1: 依存関係と色処理の基礎（Lab 変換・色見本・色の割合）

**Files:**
- Modify: `pyproject.toml`（`uv add pillow numpy scikit-learn` と `uv add --dev pytest` で）
- Modify: `.gitignore`（61行目 `tmbootpicker.efi.superpowers/` を `tmbootpicker.efi` と `.superpowers/` の2行に直す）
- Create: `src/glamhack2026_photochrom/palette.py`
- Test: `tests/test_palette.py`

**Interfaces:**
- Produces:
  - `rgb_to_lab(rgb: np.ndarray) -> np.ndarray` — `(N,3)` uint8 sRGB → `(N,3)` float CIELAB（D65）
  - `lab_to_hex(lab: np.ndarray) -> str` — `(3,)` → `"#rrggbb"`
  - `build_codebook(lab_samples: np.ndarray, k: int = 28, seed: int = 0) -> np.ndarray` — `(k,3)` Lab。L の昇順に並べる。
  - `color_shares(lab_pixels: np.ndarray, codebook: np.ndarray) -> np.ndarray` — `(k,)` 合計 1。重み `w = 0.3 + min(chroma, 60) / 60`（chroma = √(a²+b²)）。

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_rgb_to_lab_white_and_black():
    lab = rgb_to_lab(np.array([[255,255,255],[0,0,0]], dtype=np.uint8))
    assert lab[0] == pytest.approx([100, 0, 0], abs=0.5)
    assert lab[1] == pytest.approx([0, 0, 0], abs=0.5)

def test_lab_to_hex_roundtrip():
    assert lab_to_hex(rgb_to_lab(np.array([[255,0,0]], dtype=np.uint8))[0]) == "#ff0000"

def test_build_codebook_shape_and_order():
    rng = np.random.default_rng(0)
    cb = build_codebook(rng.uniform([0,-50,-50],[100,50,50],(5000,3)), k=28)
    assert cb.shape == (28, 3) and np.all(np.diff(cb[:,0]) >= 0)

def test_color_shares_sums_to_one_and_prefers_chroma():
    cb = np.array([[50,0,0],[50,60,0]], dtype=float)   # 灰色, 赤
    px = np.array([[50,0,0]]*50 + [[50,60,0]]*50, dtype=float)
    s = color_shares(px, cb)
    assert s.sum() == pytest.approx(1)
    assert s[1] > s[0]   # 同じ画素数なら彩度の高い色が大きい
```

- [ ] **Step 2: 失敗を確認** — Run: `uv run pytest tests/test_palette.py -v` / Expected: FAIL（`ModuleNotFoundError`）
- [ ] **Step 3: `palette.py` を実装** — Lab 変換は numpy で sRGB → linear → XYZ（D65）→ Lab を自前実装。k-means は `sklearn.cluster.KMeans(n_clusters=k, random_state=seed, n_init=4)`。最近傍は `((px[:,None]-cb[None])**2).sum(-1).argmin(1)`。
- [ ] **Step 4: 成功を確認** — Run: `uv run pytest tests/test_palette.py -v` / Expected: 4 passed
- [ ] **Step 5: Commit** — `git add pyproject.toml uv.lock .gitignore .python-version src tests && git commit -m "feat: add Lab colour codebook and share computation"`

---

### Task 2: プリントの切り出しと年代の解析

**Files:**
- Create: `src/glamhack2026_photochrom/crop.py`
- Create: `src/glamhack2026_photochrom/dates.py`
- Test: `tests/test_crop.py`, `tests/test_dates.py`

**Interfaces:**
- Produces:
  - `crop_print(img: PIL.Image.Image) -> tuple[PIL.Image.Image, tuple[float,float,float,float]]` — 切り出した画像と、元画像に対する相対矩形 `(x0,y0,x1,y1)`（0〜1）。
  - `year_weights(std: str) -> dict[int, float] | None`

- [ ] **Step 1: 失敗するテストを書く**

```python
def _scan(w=400, h=340, print_box=(20,10,380,250), chart_y=(270,320)):
    img = Image.new("RGB", (w,h), (58,58,58))            # 背景グレー
    d = ImageDraw.Draw(img)
    d.rectangle(print_box, fill=(120,160,200))           # プリント
    d.rectangle((40,chart_y[0],360,chart_y[1]), fill=(220,220,220))  # チャート
    return img

def test_crop_print_finds_print_and_excludes_chart():
    out, box = crop_print(_scan())
    assert box == pytest.approx((20/400, 10/340, 381/400, 251/340), abs=0.02)

def test_crop_print_fallback_when_print_matches_background():
    img = Image.new("RGB", (400,300), (58,58,58))
    out, box = crop_print(img)
    assert box == pytest.approx((0.1, 0.1, 0.9, 0.9)) and out.size[0] > 0

@pytest.mark.parametrize("s,expected", [
    ("1897", {1897: 1.0}),
    ("1902/1904", {1902: 1/3, 1903: 1/3, 1904: 1/3}),
    ("1891/1914", None),
    ("104 /1914", None),
    ("", None),
])
def test_year_weights(s, expected):
    assert year_weights(s) == (pytest.approx(expected) if expected else None)
```

- [ ] **Step 2: 失敗を確認** — Run: `uv run pytest tests/test_crop.py tests/test_dates.py -v` / Expected: FAIL
- [ ] **Step 3: `crop.py` を実装** — 背景色は四隅 10×10px の中央値。各画素で背景色との RGB 距離 > 25 を前景とする。行ごとの前景率 > 0.5 の行を上から連続でたどり、最初の連続ブロック（＝プリント。下のチャートは別ブロック）を縦範囲とする。その範囲内で列ごとの前景率 > 0.5 の最小〜最大を横範囲とする。ブロック高さが画像高さの 20% 未満なら中央 80% にフォールバック。
- [ ] **Step 4: `dates.py` を実装** — 正規表現 `^\d{4}$` / `^(\d{4})/(\d{4})$` のみ受け付ける。
- [ ] **Step 5: 実画像で目視確認** — 実プレビュー4枚（`30617335`, `30418784`, `30470700`, `31869452`）に `crop_print` をかけ、scratchpad に保存して目で見る。チャートと背景が消えていること。
- [ ] **Step 6: 成功を確認** — Run: `uv run pytest -v` / Expected: all passed
- [ ] **Step 7: Commit** — `git commit -m "feat: crop print area and parse catalogue dates"`

---

### Task 3: 前処理パイプライン → `site/data/colors.json`

**Files:**
- Create: `src/glamhack2026_photochrom/build.py`
- Modify: `src/glamhack2026_photochrom/__init__.py`（`main()` が `build.run()` を呼ぶ）
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: Task 1・2 の全関数
- Produces:
  - `load_records(csv_path: Path) -> list[dict]` — recatalogued のみ。各 dict: `id, title, date, years, art, iiif, image_file, place, erara`
    - `iiif`: 最初の URI から `/full/full/0/default.jpg` を除いたベース（例 `https://www.e-rara.ch/i3f/v21/30418784`）
    - `image_file`: zip 内パス `images-recatalogued-preview/<page_vlid>.jpg`（`image_files` 列の最初の値のファイル名部分を使う）
    - `erara`: `https://www.e-rara.ch/id/<page_vlid>`
  - `run(data_dir: Path = Path("data"), out: Path = Path("site/data/colors.json")) -> None`
  - 出力 JSON の形（フロントエンドはこれを前提にする）:

```json
{
  "codebook": ["#1a1c20", "..."],
  "images": [
    {"id": "991...", "title": "...", "date": "[1897]", "years": {"1897": 1.0},
     "art": false, "iiif": "https://www.e-rara.ch/i3f/v21/30418784",
     "crop": [0.03, 0.02, 0.97, 0.78], "place": "Genf", "erara": "https://www.e-rara.ch/id/30418784",
     "shares": [0.0, 0.12, "... K 個, 小数3桁"]}
  ]
}
```

- `run` の処理: 各画像を zip から読み → `crop_print` → 長辺 200px に縮小 → Lab。全画像から 1枚あたり 500 画素を無作為抽出（`np.random.default_rng(0)`）して `build_codebook`。その後各画像で `color_shares`。`place` は `subject_geographical_entity` の最初の要素の `, ID:` より前。

- [ ] **Step 1: 失敗するテストを書く** — 小さな CSV（recatalogued 2件・legacy 1件、うち1件は zip に画像なし）と、Task 2 の `_scan()` 画像1枚入りの zip を `tmp_path` に作る。

```python
def test_load_records_filters_and_parses(tmp_path):
    recs = load_records(make_csv(tmp_path))
    assert [r["id"] for r in recs] == ["991000000000000001", "991000000000000002"]
    assert recs[0]["iiif"] == "https://www.e-rara.ch/i3f/v21/30418784"

def test_run_writes_json_and_skips_missing_image(tmp_path, capsys):
    make_csv(tmp_path); make_zip(tmp_path)
    out = tmp_path / "colors.json"
    run(tmp_path, out, k=2)
    data = json.loads(out.read_text())
    assert len(data["codebook"]) == 2 and len(data["images"]) == 1
    assert sum(data["images"][0]["shares"]) == pytest.approx(1, abs=0.01)
    assert "missing" in capsys.readouterr().err
```

（`run` はテスト用に `k: int = 28` 引数も受ける）

- [ ] **Step 2: 失敗を確認** — Run: `uv run pytest tests/test_build.py -v` / Expected: FAIL
- [ ] **Step 3: `build.py` を実装**
- [ ] **Step 4: 成功を確認** — Run: `uv run pytest -v` / Expected: all passed
- [ ] **Step 5: 本番データで実行** — Run: `uv run glamhack2026-photochrom` / Expected: `site/data/colors.json` が生成され、`images` が約 1,947 件、ファイルは 1MB 前後。色見本 28 色を HTML スウォッチで書き出して目視（カラーチャートの原色のような不自然な色が無いこと）。
- [ ] **Step 6: Commit** — `git add src tests site/data/colors.json && git commit -m "feat: build colour data for recatalogued photochroms"`

---

### Task 4: 画面1 — 年代の色の帯

**Files:**
- Create: `site/index.html`, `site/style.css`, `site/app.js`, `site/common.js`

**Interfaces:**
- Consumes: `site/data/colors.json`（Task 3 の形）
- Produces（`common.js`）:
  - `loadColors(): Promise<{codebook: string[], images: object[]}>`
  - `iiifUrl(img, width: number): string` — `crop` を IIIF の `pct:` 領域に変換: `${img.iiif}/pct:${x0*100},${y0*100},${(x1-x0)*100},${(y1-y0)*100}/${width},/0/default.jpg`

画面の仕様:
- 上部: 年ごとの縦帯（`years` を持つ画像の年を昇順）＋ 右端に「年代不明」帯。各帯の値 = Σ(年の重み × shares) / Σ(年の重み)。各帯の下に年と件数 n（重みの合計、小数1桁）。
- 帯の中で色の層を色見本順（L 昇順）に積む。
- チェックボックス「絵画複製を含める」（既定オフ）で `art: true` の画像を集計に入れる。
- 色の層クリック → 下に一覧: その年（年代不明帯ならその集合）の画像を、その色の share 降順で最大 60 件、サムネイル（`iiifUrl(img, 160)`）。
- サムネイルクリック → 詳細パネル: `iiifUrl(img, 800)`、その画像の上位 6 色パレット（色見本の色と割合 %）、タイトル、日付、場所、e-rara リンク。絵画複製で `paintings.json` に対応があれば（ファイルが無い・読めない場合はリンクを出さずに続行）「元絵画と比べる」リンク → `compare.html?id=<id>`。
- 画面下部に、選択中の画像（未選択なら選択中の年）のパレットを常時表示。

- [ ] **Step 1: 実装**
- [ ] **Step 2: ローカルで確認** — Run: `uv run python -m http.server -d site 8000`。Playwright で `http://localhost:8000/` を開きスクリーンショット。確認: 帯が年順に並び各帯に n が出る / 1897 年の青系の層をクリック → 一覧に青い空の多い画像が並ぶ / サムネイル → 詳細とパレット / チェックボックスで帯が変わる / コンソールエラーなし。
- [ ] **Step 3: Commit** — `git commit -m "feat: year colour bands view"`

---

### Task 5: 元絵画データ → `site/data/paintings.json`

**Files:**
- Create: `src/glamhack2026_photochrom/paintings.py`
- Modify: `src/glamhack2026_photochrom/__init__.py`（`main()` の後に `paintings.run()` も呼ぶ。引数 `--paintings-only` で単独実行可）
- Test: `tests/test_paintings.py`

**Interfaces:**
- Consumes: `load_records`、`palette.rgb_to_lab`, `palette.color_shares`、`colors.json` の `codebook`
- Produces:
  - `gnd_ids(record_row: dict) -> list[str]` — `subject_title_of_work` から `\(DE-588\)([0-9X-]+)` を抽出
  - `run(data_dir: Path = Path("data"), colors: Path = Path("site/data/colors.json"), out: Path = Path("site/data/paintings.json"), fetch=urllib_fetch) -> None`
  - 出力 JSON:

```json
[{"id": "991...", "work": "Naissance de Venus", "artist": "Cabanel, Alexandre",
  "image": "https://commons.wikimedia.org/wiki/Special:FilePath/<file>?width=1200",
  "source": "wikidata:Q...", "shares": [0.0, "... K 個"]}]
```

- Wikidata SPARQL: `VALUES ?g {...} ?item wdt:P227 ?g . ?item wdt:P18 ?img`（User-Agent `photochrom-glamhack/0.1`）。`work`/`artist` は `subject_title_of_work` の `/` の前後から取る。
- 絵画の `shares`: `?width=400` で取得 → Lab → `color_shares`（クロップなし）。
- 手動追加: `data/paintings-extra.csv`（列 `id,image,work,artist,source`）があれば同じ処理で追加。同僚のリストはここに入れる。

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_gnd_ids():
    row = {"subject_title_of_work": "Danae / Vecellio, Tiziano (1477-1576), ID: (DE-588)4791704-0"}
    assert gnd_ids(row) == ["4791704-0"]

def test_run_skips_failed_image_fetch(tmp_path):
    # fetch スタブ: SPARQL は2作品を返し、画像取得は1つ目だけ成功、2つ目は例外
    run(tmp_path, colors_json(tmp_path), tmp_path / "p.json", fetch=stub_fetch)
    assert len(json.loads((tmp_path / "p.json").read_text())) == 1
```

- [ ] **Step 2: 失敗を確認** — Run: `uv run pytest tests/test_paintings.py -v` / Expected: FAIL
- [ ] **Step 3: `paintings.py` を実装**
- [ ] **Step 4: 成功を確認** — Run: `uv run pytest -v` / Expected: all passed
- [ ] **Step 5: 本番実行** — Run: `uv run glamhack2026-photochrom --paintings-only` / Expected: `paintings.json` に約 9 件
- [ ] **Step 6: Commit** — `git commit -m "feat: fetch original paintings via Wikidata"`

---

### Task 6: 画面2 — 元絵画との重ね合わせ

**Files:**
- Create: `site/compare.html`, `site/compare.js`
- Modify: `site/style.css`

**Interfaces:**
- Consumes: `loadColors`, `iiifUrl`（`common.js`）、`site/data/paintings.json`

画面の仕様:
- `?id=` 無しなら左に絵画複製の一覧（`paintings.json` の全件、サムネイル）。選ぶと右に重ね合わせ。
- 下: 元絵画（`image`）。上: photochrom（`iiifUrl(img, 1200)`）、CSS `transform: translate() rotate() scale()`。
- 操作: ドラッグ＝移動、`Shift`+ドラッグ＝回転、ホイール＝拡大縮小。リセットボタン。透明度スライダー（0〜100、既定 50）。
- 下部に photochrom と元絵画のパレット（各上位 6 色と割合）を2段で並べる。
- 画面1へ戻るリンク。

- [ ] **Step 1: 実装**
- [ ] **Step 2: ローカルで確認** — Playwright で `compare.html` を開く。確認: 一覧から Cabanel を選ぶ → 重なって表示 / ドラッグ・回転・ホイールが効く / スライダーで透ける / パレット2段 / 画面1の詳細から `compare.html?id=` で直接開ける / コンソールエラーなし。
- [ ] **Step 3: Commit** — `git commit -m "feat: painting overlay comparison view"`

---

### Task 7: 仕上げと公開準備

**Files:**
- Modify: `README.md`（目的・データ出典とライセンス表記・再生成手順 `uv run glamhack2026-photochrom`・ローカル表示手順）

- [ ] **Step 1: README を書く** — 出典: Zenodo `10.5281/zenodo.24141227`（メタデータ CC0、画像 PDM 1.0）、絵画画像は Wikimedia Commons。
- [ ] **Step 2: 全体確認** — `uv run pytest -v` が全部通る。両画面をスクリーンショットで確認。
- [ ] **Step 3: Commit** — `git commit -m "docs: README with data sources and usage"`
- [ ] **Step 4: GitHub Pages 公開** — **ユーザーに確認してから**。`site/` を公開ディレクトリにする。
