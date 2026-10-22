#!/usr/bin/env python3
"""Build self-contained HTML from the source template and JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    html = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
    data = json.loads((ROOT / "data/cases.json").read_text(encoding="utf-8"))["cases"]
    heroes = json.loads((ROOT / "data/heroes.json").read_text(encoding="utf-8"))
    queue = json.loads((ROOT / "data/research-queue.json").read_text(encoding="utf-8"))["items"]
    for key, value in {
        "__HEROES_JSON__": heroes["heroes"],
        "__ALIASES_JSON__": heroes["aliases"],
        "__CASES_JSON__": data,
        "__QUEUE_JSON__": queue,
    }.items():
        if html.count(key) != 1:
            raise ValueError(f"Missing or repeated marker: {key}")
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        html = html.replace(key, text)
    for name in ("index.html", "dist/index.html"):
        out = ROOT / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    print(f"Built {len(data)} cases, {len(heroes['heroes'])} heroes and {len(queue)} research leads")

if __name__ == "__main__":
    main()
