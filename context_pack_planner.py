#!/usr/bin/env python3
"""context-pack-planner: pack prioritized documents into a fixed context
budget deterministically (greedy first-fit with must-include reserve),
producing a reproducible plan with a content hash. Pure stdlib."""

import argparse
import hashlib
import json
import sys


def validate_manifest(m):
    """Return list of error strings (empty if valid)."""
    errs = []
    if not isinstance(m, dict):
        return ["manifest must be a JSON object"]
    b = m.get("budget")
    if not isinstance(b, int) or isinstance(b, bool) or b <= 0:
        errs.append("'budget' must be a positive integer")
    r = m.get("reserve", 0)
    if not isinstance(r, int) or isinstance(r, bool) or r < 0:
        errs.append("'reserve' must be a non-negative integer")
    elif isinstance(b, int) and not isinstance(b, bool) and r > b:
        errs.append("'reserve' must not exceed 'budget'")
    docs = m.get("docs", [])
    if not isinstance(docs, list):
        errs.append("'docs' must be a list")
        return errs
    names = set()
    for i, d in enumerate(docs):
        if not isinstance(d, dict):
            errs.append("docs[%d] must be an object" % i)
            continue
        name = d.get("name")
        if not name or not isinstance(name, str):
            errs.append("docs[%d]: 'name' must be a non-empty string" % i)
        elif name in names:
            errs.append("docs[%d]: duplicate name '%s'" % (i, name))
        else:
            names.add(name)
        t = d.get("tokens", 0)
        if not isinstance(t, int) or isinstance(t, bool) or t < 0:
            errs.append("docs[%d]: 'tokens' must be a non-negative integer" % i)
        pr = d.get("priority", 100)
        if not isinstance(pr, int) or isinstance(pr, bool):
            errs.append("docs[%d]: 'priority' must be an integer" % i)
    return errs


def plan(manifest):
    """Compute the packing plan. Raises ValueError on invalid manifest."""
    errs = validate_manifest(manifest)
    if errs:
        raise ValueError("; ".join(errs))
    budget = manifest["budget"]
    reserve = manifest.get("reserve", 0)
    docs = list(manifest.get("docs", []))
    must = [d for d in docs if d.get("must")]
    rest = [d for d in docs if not d.get("must")]
    must.sort(key=lambda d: (d.get("tokens", 0), d.get("name", "")))
    rest.sort(key=lambda d: (d.get("priority", 100), d.get("tokens", 0), d.get("name", "")))

    included, skipped = [], []
    used = reserve

    for d in must:
        t = d.get("tokens", 0)
        if used + t <= budget:
            used += t
            included.append({"name": d["name"], "tokens": t, "partial": False})
        else:
            skipped.append({"name": d["name"], "tokens": t, "reason": "must_doc_exceeds_budget"})

    for d in rest:
        t = d.get("tokens", 0)
        if used + t <= budget:
            used += t
            included.append({"name": d["name"], "tokens": t, "partial": False})
        elif d.get("truncate"):
            room = budget - used
            if room > 0:
                used = budget
                included.append({"name": d["name"], "tokens": room, "partial": True, "dropped_tokens": t - room})
            else:
                skipped.append({"name": d["name"], "tokens": t, "reason": "no_room_to_truncate"})
        else:
            skipped.append({"name": d["name"], "tokens": t, "reason": "insufficient_budget"})

    core = {
        "budget": budget,
        "reserve": reserve,
        "used": used,
        "budget_left": budget - used,
        "included": included,
        "skipped": skipped,
    }
    digest = hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    core["plan_hash"] = digest[:16]
    return core


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="context-pack-planner",
        description="Pack prioritized documents into a fixed context budget; output a reproducible plan.",
    )
    p.add_argument("--manifest", help="manifest JSON file; omit to read from stdin")
    p.add_argument("--out", help="write plan JSON to this file (default stdout)")
    args = p.parse_args(argv)

    try:
        if args.manifest:
            with open(args.manifest, "r", encoding="utf-8") as f:
                m = json.load(f)
        else:
            m = json.load(sys.stdin)
    except Exception as exc:
        print("error: cannot load manifest: %s" % exc, file=sys.stderr)
        return 2

    try:
        result = plan(m)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
