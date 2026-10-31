#!/usr/bin/env python3
"""
OpenHub Catalog Generator
Scans modules/ directory and builds catalog.json for GitHub and remote client indexing.
"""
import os
import json

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(REPO_ROOT, "modules")
CATALOG_FILE = os.path.join(REPO_ROOT, "catalog.json")

def generate_catalog():
    catalog = []
    if not os.path.exists(MODULES_DIR):
        print(f"Directory not found: {MODULES_DIR}")
        return catalog

    for item in sorted(os.listdir(MODULES_DIR)):
        if item == "scratch" or item.startswith("__") or item.startswith("."):
            continue
        item_path = os.path.join(MODULES_DIR, item)
        if not os.path.isdir(item_path):
            continue

        m_path = os.path.join(item_path, "manifest.json")
        if not os.path.exists(m_path):
            continue

        try:
            with open(m_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"Skipping {item}: error parsing manifest: {e}")
            continue

        # Collect files in directory
        files = []
        for f in sorted(os.listdir(item_path)):
            if f.startswith(".") or f == "__pycache__":
                continue
            if os.path.isfile(os.path.join(item_path, f)):
                files.append(f)

        entry = {
            "id": manifest.get("id", item),
            "dir_name": item,
            "name": manifest.get("name", item.replace("_", " ").title()),
            "version": manifest.get("version", "1.0.0"),
            "author": manifest.get("author", "community"),
            "category": manifest.get("category", "Tools"),
            "description": manifest.get("description", ""),
            "entrypoint": manifest.get("entrypoint", "main.py"),
            "trust_level": manifest.get("trust_level", "trusted"),
            "files": files
        }
        catalog.append(entry)

    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print(f"✅ Generated {CATALOG_FILE} with {len(catalog)} sub-apps.")
    return catalog

if __name__ == "__main__":
    generate_catalog()
