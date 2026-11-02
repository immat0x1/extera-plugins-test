#!/usr/bin/env python3
import ast
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
INDEX = ROOT / "extera-plugins.json"
ARCHIVE_SUFFIXES = {".elyx", ".eaf"}

REPOSITORY = {
    "schema": 1,
    "name": "exteraGram Test Plugins",
    "author": "@exteraDev",
}

FIELDS = (
    "id", "name", "description", "author", "version", "icon",
    "app_version", "sdk_version", "requirements", "category",
)


def read_plugin_file(path):
    meta = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.startswith("__") and target.id.endswith("__"):
            key = target.id[2:-2]
            if key in FIELDS:
                meta[key] = ast.literal_eval(node.value)
    return meta


def load_structured(name, data):
    if name.endswith(".json"):
        return json.loads(data)
    import yaml
    return yaml.safe_load(data)


def read_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        meta_path = None
        for refmap in ("refmap.yaml", "refmap.yml", "refmap.json"):
            if refmap in names:
                meta_path = (load_structured(refmap, archive.read(refmap)) or {}).get("metainfo")
                break
        if meta_path is None:
            meta_path = next((n for n in ("metainfo.yaml", "metainfo.yml", "metainfo.json") if n in names), None)
        if meta_path is None:
            sys.exit(f"{path}: no metadata file")
        raw = load_structured(meta_path, archive.read(meta_path)) or {}
    return {key.strip("_"): value for key, value in raw.items() if key.strip("_") in FIELDS}


def main():
    previous = {}
    if INDEX.exists():
        previous = {p["id"]: p for p in json.loads(INDEX.read_text(encoding="utf-8")).get("plugins", [])}

    plugins = []
    for path in sorted(PLUGINS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix == ".plugin":
            meta = read_plugin_file(path)
        elif path.suffix in ARCHIVE_SUFFIXES:
            meta = read_archive(path)
        else:
            continue

        missing = [key for key in ("id", "name", "version") if not meta.get(key)]
        if missing:
            sys.exit(f"{path}: missing {', '.join(missing)}")
        if isinstance(meta.get("requirements"), list):
            meta["requirements"] = ", ".join(meta["requirements"])

        data = path.read_bytes()
        entry = {
            **meta,
            "file": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        old = previous.get(meta["id"], {})
        if old.get("sha256") == entry["sha256"] and old.get("updated_at"):
            entry["updated_at"] = old["updated_at"]
        else:
            entry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        plugins.append(entry)

    ids = [p["id"] for p in plugins]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        sys.exit(f"duplicate plugin ids: {', '.join(duplicates)}")

    index = {**REPOSITORY, "plugins": plugins}
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{INDEX.name}: {len(plugins)} plugins")


if __name__ == "__main__":
    main()
