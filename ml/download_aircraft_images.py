"""
Download aircraft reference images from Wikimedia Commons via their API.
Uses the MediaWiki API to get proper image URLs (avoids hotlink blocking).
"""
import requests
import time
from pathlib import Path

OUT = Path(__file__).parent.parent / "backend" / "storage" / "aircraft_images"
OUT.mkdir(parents=True, exist_ok=True)

# Wikimedia Commons filenames (exact filenames on Commons)
AIRCRAFT_IMAGES = {
    "Su-35S": "Sukhoi_Su-35S_at_MAKS-2011_airshow.jpg",
    "Su-30SM": "Sukhoi_Su-30SM_in_flight_2014.jpg",
    "Su-27SM": "Sukhoi_Su-27_in_2010.jpg",
    "Su-33": "Su-33_2009.jpg",
    "Su-34": "Russian_Air_Force_Sukhoi_Su-34_Beltyukov.jpg",
    "Su-24M": "Sukhoi_Su-24_inflight_Mishin.jpg",
    "Su-25": "Sukhoi_Su-25_in_2012.jpg",
    "Su-57": "Sukhoi_Su-57_at_MAKS_2019.jpg",
    "MiG-29": "Russian_Air_Force_MiG-29_%289-13%29.jpg",
    "MiG-31BM": "Russian_Air_Force_MiG-31_Pichugin.jpg",
    "Tu-95MS": "Tu-95_in_flight.jpg",
    "Tu-160": "Tupolev_Tu-160_in_2014.jpg",
    "Tu-22M3": "Tupolev_Tu-22M-3_in_flight.jpg",
    "Il-76": "Russian_Air_Force_Ilyushin_Il-76MD.jpg",
    "Il-78": "IL78M_RF-94283_23red_%2814034298050%29.jpg",
    "A-50": "Beriev_A-50.jpg",
    "Ka-52": "Ka-52_%284%29.jpg",
    "Mi-8": "Mi-8MTV-5.jpg",
    "An-124": "Antonov_An-124_Ruslan.jpg",
    "F-15": "F-15E_391st_Bold_Tigers_Bagram.jpg",
    "F-16": "F-16_June_2008.jpg",
    "F-22": "Lockheed_Martin_F-22A_Raptor_JSOH.jpg",
    "FA-18": "FA-18_Hornet_VFA-41.jpg",
    "B-52": "B-52H_static_display_arms_702.jpg",
    "B-1B": "B-1B_over_the_pacific_ocean.jpg",
    "C-130": "Lockheed_C-130_Hercules.jpg",
    "C-17": "C17_aircraft_alt.jpg",
    "C-5": "C-5_Galaxy_Delivery.jpg",
    "KC-135": "KC-135R_-_22ARW.jpg",
    "KC-10": "KC-10A_Extender.jpg",
    "E-3": "E-3_Sentry_exercise_Green_Flag.jpg",
    "E-8": "USAF_E-8C_Joint_STARS.jpg",
    "P-3C": "Lockheed_P-3C_Orion.jpg",
    "F-14A_Tomcat": "Grumman_F-14_Tomcat.jpg",
    "F-4E_Phantom": "McDonnell_Douglas_F-4E_Phantom_II%2C_Iran_-_Air_Force_AN1618814.jpg",
    "F-5E_Tiger_II": "Northrop_F-5E_%28Tail_No._01557%29_061006-F-1234S-073.jpg",
}

# Aliases — same airframe, save under multiple names
ALIASES = {
    "Su-24MK": "Su-24M",
    "Su-25SM": "Su-25",
    "MiG-29A": "MiG-29",
    "MiG-29K": "MiG-29",
    "MiG-29SMT": "MiG-29",
    "An-26": "C-130",  # similar shape placeholder
    "Il-20": "Il-76",  # similar shape placeholder
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Vauban-IMINT/1.0 (https://github.com/xdYanou/Vauban-IMINT; research project)"


def get_image_url(commons_filename: str) -> str | None:
    """Use MediaWiki API to get a direct image URL."""
    resp = SESSION.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query",
        "titles": f"File:{commons_filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 640,
        "format": "json",
    })
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo", [{}])[0]
        return info.get("thumburl") or info.get("url")
    return None


def download():
    print(f"Downloading aircraft images to {OUT}")
    print()

    for name, commons_file in AIRCRAFT_IMAGES.items():
        fname = f"{name}.jpg"
        outpath = OUT / fname

        if outpath.exists() and outpath.stat().st_size > 1000:
            print(f"  SKIP {name} (exists)")
            continue

        url = get_image_url(commons_file)
        if not url:
            print(f"  FAIL {name}: couldn't resolve URL")
            continue

        try:
            r = SESSION.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                outpath.write_bytes(r.content)
                print(f"  OK   {name} ({len(r.content)//1024}KB)")
            else:
                print(f"  FAIL {name}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  ERR  {name}: {e}")

        time.sleep(0.5)  # Be nice to Wikimedia

    # Create aliases
    print()
    for alias, source in ALIASES.items():
        src = OUT / f"{source}.jpg"
        dst = OUT / f"{alias}.jpg"
        if src.exists() and not dst.exists():
            import shutil
            shutil.copy2(src, dst)
            print(f"  ALIAS {alias} -> {source}")

    print()
    total = len(list(OUT.glob("*.jpg")))
    print(f"Done: {total} images in {OUT}")


if __name__ == "__main__":
    download()
