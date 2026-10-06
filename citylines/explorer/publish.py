"""Copy a validated derived bundle into a local static gallery, without deploying."""
import argparse
import json
from pathlib import Path
import shutil
from .export import write_json


def publish(bundle, root):
    bundle, root = Path(bundle), Path(root)
    manifest = json.loads((bundle / "manifest.json").read_text())
    required = ["manifest.json", "report.json", manifest["geometry"], *[d["file"] for d in manifest["dates"]]]
    city, version = manifest["city"], manifest["bundle"]
    if not city or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in city):
        raise ValueError("Published city ids must use lowercase ASCII letters, digits, hyphens or underscores")
    if len(version) != 16 or any(c not in "0123456789abcdef" for c in version):
        raise ValueError("Invalid bundle version")
    if any(Path(name).name != name or not (bundle / name).is_file() for name in required):
        raise ValueError("Incomplete bundle or invalid asset filename")
    destination = root / "data" / city / version
    destination.mkdir(parents=True, exist_ok=True)
    for name in required:
        shutil.copy2(bundle / name, destination / name)
    catalog_path = root / "catalog.json"
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {"schemaVersion": 1, "cities": []}
    entry = {"city": city, "title": manifest["title"], "manifest": f"data/{city}/{version}/manifest.json"}
    catalog["cities"] = [c for c in catalog["cities"] if c["city"] != city] + [entry]
    catalog["cities"].sort(key=lambda c: c["title"])
    write_json(catalog_path, catalog)
    return destination


def main():
    parser = argparse.ArgumentParser(description="Add an exported bundle to the local static gallery; no deployment")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--gallery-root", type=Path, default=Path("docs/explore"))
    args = parser.parse_args()
    try:
        print(publish(args.bundle, args.gallery_root))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Gallery staging failed: {exc}\n")


if __name__ == "__main__":
    main()
