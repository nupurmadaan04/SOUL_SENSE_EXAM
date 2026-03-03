#!/usr/bin/env python3
"""
Index Mapping Parity Verifier

Compares Elasticsearch index mappings between two sources (files or ES _mapping endpoints)
and reports deterministic differences suitable for CI verification.

Usage examples:
  python scripts/index_mapping_parity.py --left mappings/dev_index.json --right mappings/prod_index.json
  python scripts/index_mapping_parity.py --left http://es-dev:9200/my_index/_mapping --right http://es-prod:9200/my_index/_mapping

The comparator normalizes mappings by removing meta fields and ordering properties
so results are deterministic for reviewers and CI.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

try:
    # Lightweight HTTP fetch; requests is nice but optional
    import requests
except Exception:
    requests = None


def load_source(path_or_url: str) -> Dict[str, Any]:
    """Load mapping JSON from a file path or URL.

    If the input is a URL (starts with http:// or https://) and `requests` is
    available, perform a GET and parse JSON. Otherwise read local file.
    """
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        if not requests:
            raise RuntimeError("requests package required to fetch mappings from URLs")
        resp = requests.get(path_or_url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    with open(path_or_url, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_mapping(obj: Any) -> Any:
    """Normalize mapping JSON by removing non-deterministic keys and sorting dicts.

    - Remove `_meta`, `dynamic_templates` (optionally), and `date_detection` keys
    - Keep `properties` but recursively normalize
    - Sort dictionary keys to make comparisons deterministic
    """
    if isinstance(obj, dict):
        out = {}
        for k in sorted(obj.keys()):
            if k in ("_meta", "_meta_fields"):
                continue
            # Top-level index settings/aliases are not part of mapping parity check
            if k in ("settings", "aliases"):
                continue
            if k == "dynamic_templates":
                # Keep dynamic templates but normalize their content
                out[k] = normalize_mapping(obj[k])
                continue
            if k == "properties":
                # Ensure properties are normalized and keys sorted
                out[k] = normalize_mapping(obj[k])
                continue
            out[k] = normalize_mapping(obj[k])
        return out
    elif isinstance(obj, list):
        return [normalize_mapping(i) for i in obj]
    else:
        return obj


def extract_mappings(root: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the mappings object from common ES mapping responses.

    Elasticsearch returns either a dict keyed by index name, or a direct mapping.
    This function normalizes to the inner `mappings` dict.
    """
    # If this looks like {index: {mappings: {...}}}
    if not isinstance(root, dict):
        return {}

    # If it's a one-key dict mapping index -> mapping
    keys = list(root.keys())
    if len(keys) == 1 and isinstance(root[keys[0]], dict) and "mappings" in root[keys[0]]:
        return root[keys[0]]["mappings"]

    # If the top-level has `mappings` directly
    if "mappings" in root:
        return root["mappings"]

    # Fallback: assume root itself is mappings-like
    return root


def compare_mappings(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Compare normalized mappings and return a diff-like dict describing differences."""
    na = normalize_mapping(extract_mappings(a))
    nb = normalize_mapping(extract_mappings(b))

    if na == nb:
        return {"equal": True, "differences": {}}

    # Lightweight diff: report keys present in one but not the other, and value mismatches
    diffs = {}
    keys = set(na.keys()) | set(nb.keys())
    for k in sorted(keys):
        va = na.get(k)
        vb = nb.get(k)
        if va == vb:
            continue
        diffs[k] = {"left": va, "right": vb}

    return {"equal": False, "differences": diffs}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Index mapping parity verifier")
    parser.add_argument("--left", required=True, help="Left mapping (file path or URL)")
    parser.add_argument("--right", required=True, help="Right mapping (file path or URL)")
    parser.add_argument("--output", help="Write JSON result to file")
    parser.add_argument("--fail-on-diff", action="store_true", help="Exit non-zero when differences found")

    args = parser.parse_args(argv)

    left = load_source(args.left)
    right = load_source(args.right)

    result = compare_mappings(left, right)

    out = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote result to {args.output}")
    else:
        print(out)

    if args.fail_on_diff and not result.get("equal", False):
        sys.exit(2)

    return result


if __name__ == "__main__":
    main()
