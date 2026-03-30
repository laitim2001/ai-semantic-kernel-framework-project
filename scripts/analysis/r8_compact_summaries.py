#!/usr/bin/env python3
"""R8-D1: Generate compact per-layer summaries for AI agent verification.

Each summary contains only classes with 5+ methods, with:
- class name, bases, docstring (first 150 chars)
- public method names + return types
- file path

Target: each summary < 5KB so agents can read layer summary + V9 file together.
"""

import json
from pathlib import Path

SUMMARY_DIR = Path(__file__).resolve().parent / "r8-layer-summaries"
COMPACT_DIR = Path(__file__).resolve().parent / "r8-compact-summaries"


def compact_layer(layer_id: str) -> dict:
    src = SUMMARY_DIR / f"{layer_id}-summary.json"
    if not src.exists():
        return {"layer": layer_id, "error": "not found"}

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Filter to important classes (5+ methods)
    important = []
    for cls in data.get("classes", []):
        mc = cls.get("method_count", len(cls.get("methods", [])))
        if mc >= 5:
            methods = []
            for m in cls.get("methods", []):
                name = m["name"] if isinstance(m, dict) else m
                if isinstance(m, dict):
                    ret = m.get("returns", "")
                    is_async = m.get("is_async", False)
                    prefix = "async " if is_async else ""
                    methods.append(f"{prefix}{name}() -> {ret}" if ret else f"{prefix}{name}()")
                else:
                    methods.append(f"{name}()")

            # Only method names (no args/returns) to save space
            method_names = []
            for m in cls.get("methods", []):
                name = m["name"] if isinstance(m, dict) else m
                if not name.startswith("_") or name.startswith("__init__"):
                    method_names.append(name)

            important.append({
                "name": cls["name"],
                "bases": cls.get("bases", [])[:2],
                "doc": (cls.get("docstring") or "")[:100].strip().split("\n")[0],
                "pub_methods": method_names[:10],
                "total_methods": mc,
            })

    # Sort by method count, cap at top 15
    important.sort(key=lambda x: -x["total_methods"])
    important = important[:15]

    return {
        "layer": layer_id,
        "files": data.get("total_files", 0),
        "loc": data.get("total_loc", 0),
        "total_classes": len(data.get("classes", [])),
        "shown_classes": len(important),
        "classes": important,
    }


def main():
    COMPACT_DIR.mkdir(exist_ok=True)

    print("Generating compact summaries for AI agent verification:")
    print(f"{'Layer':<6} {'Total':>6} {'5+meth':>7} {'Size':>8}")
    print("-" * 35)

    for layer_id in [f"L{i:02d}" for i in range(1, 12)]:
        result = compact_layer(layer_id)
        out_file = COMPACT_DIR / f"{layer_id}-compact.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        size = out_file.stat().st_size
        imp = result.get("important_classes", 0)
        total = result.get("total_classes", 0)
        print(f"{layer_id:<6} {total:>6} {imp:>7} {size:>7}B")

    print(f"\n[OK] Compact summaries saved to: {COMPACT_DIR}/")


if __name__ == "__main__":
    main()
