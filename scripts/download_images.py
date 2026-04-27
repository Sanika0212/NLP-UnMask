"""
Download real anatomical images from Wikimedia Commons using the API
to resolve correct download URLs.

Run once: python scripts/download_images.py
Outputs to public/anatomy/
"""
import json
import time
import urllib.request
from pathlib import Path

DEST = Path(__file__).parent.parent / "public" / "anatomy"
DEST.mkdir(parents=True, exist_ok=True)

# Wikimedia Commons filenames → local output names
# These are verified Commons file names (case-sensitive)
FILES = {
    "brachial_plexus.png":  "Brachial_plexus.svg",
    "shoulder_joint.png":   "Shoulder_joint.svg",
    "median_nerve.png":     "Gray812.png",
    "ulnar_nerve.png":      "Gray811and813.PNG",
    "radial_nerve.png":     "Gray818.png",
    "axillary_nerve.png":   "Gray817.png",
    "peripheral_nerves.png":"Gray808.png",
    "spinal_cord.png":      "Gray672.png",
    # New topics
    "elbow_joint.png":           "Gray329.png",
    "carpal_bones.png":          "Gray219.png",
    "upper_limb_muscles.png":    "Gray408.png",
    "dermatomes.png":            "Gray799.png",
    "nerve_injury_syndromes.png":"Gray812and814.PNG",
}

HEADERS = {
    "User-Agent": "UnMaskBot/1.0 (educational anatomy tutor project; contact via github) Python/3",
}

API = "https://commons.wikimedia.org/w/api.php"


def get_download_url(commons_filename: str) -> str | None:
    """Use the Wikimedia API to get the direct download URL for a file."""
    params = (
        f"?action=query&titles=File:{urllib.request.quote(commons_filename)}"
        f"&prop=imageinfo&iiprop=url&format=json"
    )
    req = urllib.request.Request(API + params, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        pages = data["query"]["pages"]
        for page in pages.values():
            ii = page.get("imageinfo", [])
            if ii:
                return ii[0]["url"]
    except Exception as e:
        print(f"    API error for {commons_filename}: {e}")
    return None


for local_name, commons_name in FILES.items():
    out = DEST / local_name
    if out.exists() and out.stat().st_size > 5000:
        print(f"  skip  {local_name}")
        continue

    url = get_download_url(commons_name)
    if not url:
        print(f"  FAIL  {local_name} — could not resolve URL")
        time.sleep(1)
        continue

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        out.write_bytes(data)
        print(f"  ok    {local_name}  ({len(data)//1024}KB)  ← {url[:60]}")
    except Exception as e:
        print(f"  FAIL  {local_name}: {e}")
    time.sleep(2)

print("\nDone.")
