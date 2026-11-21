#!/usr/bin/env python3
"""
Bulk-download candidate aircraft photos from Wikimedia Commons categories.

For each aircraft name it:
  1. looks up the Commons category (explicit mapping below, with a search fallback)
  2. lists image files in that category
  3. downloads the first N candidates, center-crops to 16:9 and resizes to 640x360
  4. saves them as backend/storage/aircraft_images/candidates/<Name>/<Name>_1.jpg ...
  5. copies candidate #1 to backend/storage/aircraft_images/<Name>.jpg (the final file)
  6. appends author/license/source to credits.csv

Usage:
    pip install requests pillow
    python download_aircraft_images.py                 # all 40
    python download_aircraft_images.py --only Su-34 F-16
    python download_aircraft_images.py --per-aircraft 5

After running, review candidates/<Name>/ and replace <Name>.jpg with a
better candidate where #1 is poor. Names listed under "NEEDS MANUAL REVIEW"
at the end had no or weak matches.
"""
import argparse
import csv
import io
import re
import shutil
import sys
import time
from pathlib import Path

import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
OUT_DIR = Path("backend/storage/aircraft_images")
TARGET = (640, 360)
HEADERS = {
    # Wikimedia asks for a descriptive User-Agent. Put your own contact here.
    "User-Agent": "AircraftImageFetcher/1.0 (personal project; contact: you@example.com)"
}

# filename (without .jpg) -> Commons category name (without "Category:")
CATEGORIES = {
    "Su-35S": "Sukhoi Su-35S",
    "Su-30SM": "Sukhoi Su-30SM",
    "Su-27SM": "Sukhoi Su-27SM",
    "Su-33": "Sukhoi Su-33",
    "Su-34": "Sukhoi Su-34",
    "Su-24M": "Sukhoi Su-24M",
    "Su-24MK": "Sukhoi Su-24",
    "Su-25": "Sukhoi Su-25",
    "Su-25SM": "Sukhoi Su-25SM",
    "Su-57": "Sukhoi Su-57",
    "MiG-29": "Mikoyan MiG-29",
    "MiG-29A": "Mikoyan MiG-29",
    "MiG-29K": "Mikoyan MiG-29K",
    "MiG-29SMT": "Mikoyan MiG-29SMT",
    "MiG-31BM": "Mikoyan MiG-31",
    "Tu-95MS": "Tupolev Tu-95MS",
    "Tu-160": "Tupolev Tu-160",
    "Tu-22M3": "Tupolev Tu-22M3",
    "Il-76": "Ilyushin Il-76",
    "Il-78": "Ilyushin Il-78",
    "Il-20": "Ilyushin Il-20",
    "A-50": "Beriev A-50",
    "An-26": "Antonov An-26",
    "An-124": "Antonov An-124",
    "Ka-52": "Kamov Ka-52",
    "Mi-8": "Mil Mi-8",
    "F-15": "McDonnell Douglas F-15 Eagle",
    "F-16": "General Dynamics F-16 Fighting Falcon",
    "F-22": "Lockheed Martin F-22 Raptor",
    "FA-18": "McDonnell Douglas F/A-18 Hornet",
    "B-52": "Boeing B-52 Stratofortress",
    "B-1B": "Rockwell B-1B Lancer",
    "C-130": "Lockheed C-130 Hercules",
    "C-17": "Boeing C-17 Globemaster III",
    "C-5": "Lockheed C-5 Galaxy",
    "KC-135": "Boeing KC-135 Stratotanker",
    "KC-10": "McDonnell Douglas KC-10 Extender",
    "E-3": "Boeing E-3 Sentry",
    "E-8": "Northrop Grumman E-8 Joint STARS",
    "P-3C": "Lockheed P-3C Orion",
    "F-14A_Tomcat": "Grumman F-14A Tomcat",
    "F-4E_Phantom": "McDonnell Douglas F-4E Phantom II",
    "F-5E_Tiger_II": "Northrop F-5E Tiger II",
    "Saeqeh": "HESA Saeqeh",
    "Kowsar": "HESA Kowsar",
}

# Words in a file title that suggest it's not a plain photo of the aircraft.
BAD_WORDS = re.compile(
    r"\b(diagram|drawing|logo|insignia|badge|patch|map|cockpit|interior|"
    r"model|toy|museum card|schematic|blueprint|silhouette|svg|emblem|"
    r"flag|stamp|poster|cartoon|render)\b",
    re.I,
)


def api_get(params):
    params = {"format": "json", "formatversion": "2", **params}
    for attempt in range(4):
        r = requests.get(API, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            time.sleep(2 + attempt * 3)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Rate limited by Commons API")


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def category_exists(name):
    data = api_get({"action": "query", "titles": f"Category:{name}"})
    page = data["query"]["pages"][0]
    return not page.get("missing", False)


def search_category(query):
    """Fallback: search Commons for a category matching the query."""
    data = api_get({
        "action": "query", "list": "search", "srnamespace": 14,
        "srsearch": query, "srlimit": 5,
    })
    hits = data["query"]["search"]
    return hits[0]["title"].replace("Category:", "") if hits else None


def list_files(category, limit=60):
    """Image files directly in the category."""
    data = api_get({
        "action": "query", "generator": "categorymembers",
        "gcmtitle": f"Category:{category}", "gcmtype": "file",
        "gcmlimit": limit,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1280,
    })
    pages = data.get("query", {}).get("pages", [])
    files = []
    for p in pages:
        info = (p.get("imageinfo") or [None])[0]
        if not info or info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        title = p["title"]
        if BAD_WORDS.search(title):
            continue
        w, h = info.get("width", 0), info.get("height", 0)
        if w < 800 or h < 450:        # too small to crop to 640x360 cleanly
            continue
        if w / h < 1.2:               # portrait / near-square crops badly
            continue
        meta = info.get("extmetadata", {})
        files.append({
            "title": title,
            "url": info.get("thumburl") or info["url"],
            "page": info.get("descriptionurl", ""),
            "w": w, "h": h,
            "author": strip_html(meta.get("Artist", {}).get("value")),
            "license": strip_html(meta.get("LicenseShortName", {}).get("value")),
        })
    # Prefer larger, landscape-ish images first.
    files.sort(key=lambda f: (abs(f["w"] / f["h"] - 16 / 9), -f["w"]))
    return files


def crop_resize(img):
    img = img.convert("RGB")
    tw, th = TARGET
    target_ratio = tw / th
    w, h = img.size
    if w / h > target_ratio:                      # too wide: trim sides
        nw = int(h * target_ratio)
        x0 = (w - nw) // 2
        img = img.crop((x0, 0, x0 + nw, h))
    else:                                         # too tall: trim top/bottom
        nh = int(w / target_ratio)
        y0 = (h - nh) // 2
        img = img.crop((0, y0, w, y0 + nh))
    return img.resize(TARGET, Image.LANCZOS)


def download_image(url):
    for attempt in range(4):
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 429:
            time.sleep(2 + attempt * 3)
            continue
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))
    raise RuntimeError("Rate limited downloading image")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="Only these names (e.g. Su-34 F-16)")
    ap.add_argument("--per-aircraft", type=int, default=4)
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    cand_root = out / "candidates"
    out.mkdir(parents=True, exist_ok=True)
    cand_root.mkdir(parents=True, exist_ok=True)

    names = args.only or list(CATEGORIES)
    unknown = [n for n in names if n not in CATEGORIES]
    if unknown:
        sys.exit(f"Unknown names: {unknown}")

    credits_path = out / "credits.csv"
    new_file = not credits_path.exists()
    review = []

    with open(credits_path, "a", newline="", encoding="utf-8") as cf:
        cw = csv.writer(cf)
        if new_file:
            cw.writerow(["filename", "candidate_file", "commons_title",
                         "author", "license", "source_page"])

        for name in names:
            cat = CATEGORIES[name]
            print(f"\n[{name}] category: {cat}")
            try:
                if not category_exists(cat):
                    alt = search_category(cat)
                    print(f"   category missing, search suggests: {alt}")
                    cat = alt
                if not cat:
                    review.append((name, "no category found"))
                    continue

                files = list_files(cat)
                if not files:
                    review.append((name, f"no usable files in '{cat}'"))
                    print("   no usable files")
                    continue

                cdir = cand_root / name
                cdir.mkdir(exist_ok=True)
                saved = 0
                for f in files:
                    if saved >= args.per_aircraft:
                        break
                    try:
                        img = crop_resize(download_image(f["url"]))
                    except Exception as e:
                        print(f"   skip {f['title']}: {e}")
                        continue
                    saved += 1
                    cpath = cdir / f"{name}_{saved}.jpg"
                    img.save(cpath, "JPEG", quality=88)
                    cw.writerow([f"{name}.jpg", cpath.name, f["title"],
                                 f["author"], f["license"], f["page"]])
                    print(f"   saved {cpath.name}  ({f['license']})")
                    time.sleep(0.5)

                if saved:
                    shutil.copyfile(cdir / f"{name}_1.jpg", out / f"{name}.jpg")
                    if saved < 2 or cat != CATEGORIES[name]:
                        review.append((name, f"only {saved} candidate(s) / fallback category '{cat}'"))
                else:
                    review.append((name, "downloads all failed"))
            except Exception as e:
                review.append((name, f"error: {e}"))
                print(f"   error: {e}")

    print("\n" + "=" * 60)
    if review:
        print("NEEDS MANUAL REVIEW:")
        for n, why in review:
            print(f"  - {n}: {why}")
    print(
        "\nDone. Check candidates/<Name>/ and replace <Name>.jpg if #1 is poor."
        "\nNote: variant-specific names (Su-24MK, MiG-29A, Su-25SM...) may share a"
        "\nparent category, so the photo may show a different variant."
        "\nKeep credits.csv; most Commons licenses require attribution."
    )


if __name__ == "__main__":
    main()
