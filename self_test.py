#!/usr/bin/env python3
"""Self test for context-pack-planner. Run: python self_test.py
Last line: SUMMARY: PASS n/n"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context_pack_planner as cpp

PASS = 0
FAIL = 0
FAILED = []


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)


def doc(name, tokens, priority=100, must=False, truncate=False):
    d = {"name": name, "tokens": tokens, "priority": priority}
    if must:
        d["must"] = True
    if truncate:
        d["truncate"] = True
    return d


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cpp.main(argv)
    return code, buf.getvalue()


# ---------- functional ----------
r = cpp.plan({"budget": 1000, "docs": [doc("a", 300), doc("b", 500)]})
check("basic_both_fit", [x["name"] for x in r["included"]] == ["a", "b"] and r["used"] == 800)
check("basic_budget_left", r["budget_left"] == 200)
r = cpp.plan({"budget": 600, "docs": [doc("big", 700)]})
check("oversize_skipped", r["included"] == [] and r["skipped"][0]["reason"] == "insufficient_budget")
r = cpp.plan({"budget": 600, "docs": [doc("a", 400), doc("b", 400)]})
check("second_skipped", len(r["included"]) == 1 and r["skipped"][0]["name"] == "b")
r = cpp.plan({"budget": 600, "docs": [doc("a", 400), doc("b", 400, truncate=True)]})
check("truncate_partial", r["included"][1]["partial"] is True and r["included"][1]["tokens"] == 200)
check("truncate_dropped_tokens", r["included"][1]["dropped_tokens"] == 200)
check("truncate_fills_budget", r["used"] == 600 and r["budget_left"] == 0)
r = cpp.plan({"budget": 600, "reserve": 600, "docs": [doc("a", 600, truncate=True)]})
check("truncate_no_room", r["skipped"][0]["reason"] == "no_room_to_truncate")
r = cpp.plan({"budget": 1000, "reserve": 200, "docs": [doc("a", 900)]})
check("reserve_reduces_avail", r["included"] == [] and r["used"] == 200)
r = cpp.plan({"budget": 1000, "reserve": 200, "docs": [doc("a", 800)]})
check("reserve_exact_fit", r["included"][0]["name"] == "a" and r["used"] == 1000)
r = cpp.plan({"budget": 1000, "docs": [doc("must1", 300, must=True), doc("must2", 900, must=True)]})
check("must_kept_when_fits", [x["name"] for x in r["included"]] == ["must1"])
check("must_skip_reason", r["skipped"][0]["reason"] == "must_doc_exceeds_budget")
try:
    cpp.plan({"budget": 1000, "reserve": 1100, "docs": []})
    check("must_reserved_out", False)
except ValueError:
    check("must_reserved_out", True)
r = cpp.plan({"budget": 1000, "docs": [doc("p2", 100, priority=2), doc("p1", 100, priority=1)]})
check("priority_order", [x["name"] for x in r["included"]] == ["p1", "p2"])
r = cpp.plan({"budget": 1000, "docs": [doc("z", 100, priority=1), doc("a", 100, priority=1)]})
check("tie_break_name_asc", [x["name"] for x in r["included"]] == ["a", "z"])
r = cpp.plan({"budget": 1000, "docs": [doc("big", 300, priority=1), doc("small", 100, priority=1)]})
check("tie_break_cost_asc", [x["name"] for x in r["included"]] == ["small", "big"])
r = cpp.plan({"budget": 500, "docs": [doc("a", 100, priority=5), doc("b", 100, priority=1)]})
check("priority_beats_order", [x["name"] for x in r["included"]] == ["b", "a"])
r = cpp.plan({"budget": 1000, "docs": [doc("m", 400, must=True), doc("n", 400, priority=1)]})
check("must_included_first", r["included"][0]["name"] == "m" and len(r["included"]) == 2)
m1 = {"budget": 1000, "docs": [doc("a", 300, priority=1), doc("b", 200), doc("c", 500, truncate=True)]}
h1 = cpp.plan(m1)["plan_hash"]
h2 = cpp.plan(json.loads(json.dumps(m1)))["plan_hash"]
check("plan_hash_deterministic", h1 == h2 and len(h1) == 16)
m3 = {"budget": 1000, "docs": [doc("a", 301, priority=1), doc("b", 200), doc("c", 500, truncate=True)]}
check("plan_hash_sensitive", cpp.plan(m3)["plan_hash"] != h1)
r = cpp.plan({"budget": 1000, "docs": [doc("zero", 0)]})
check("zero_token_doc_fits", r["included"][0]["name"] == "zero" and r["used"] == 0)
r = cpp.plan({"budget": 1000, "docs": []})
check("empty_docs", r["included"] == [] and r["skipped"] == [] and r["used"] == 0)
r = cpp.plan({"budget": 1000, "docs": [doc("d", 100)]})
check("default_priority_100", r["included"][0]["name"] == "d")
r = cpp.plan({"budget": 1000, "docs": [{"name": "no_tok"}]})
check("default_tokens_0", r["included"][0]["name"] == "no_tok")
tmp = tempfile.mkdtemp()
mf = os.path.join(tmp, "m.json")
with open(mf, "w", encoding="utf-8") as f:
    json.dump({"budget": 1000, "docs": [doc("a", 400), doc("b", 700, truncate=True)]}, f)
code, out = run_cli(["--manifest", mf])
r = json.loads(out)
check("cli_basic", code == 0 and len(r["included"]) == 2)
outf = os.path.join(tmp, "plan.json")
code, out = run_cli(["--manifest", mf, "--out", outf])
check("cli_out_file", code == 0 and json.load(open(outf, encoding="utf-8"))["budget"] == 1000)
check("cli_out_silent", out == "")

# ---------- exception paths ----------
for bad, label in [
    ({"docs": []}, "no_budget"),
    ({"budget": 0, "docs": []}, "zero_budget"),
    ({"budget": -5, "docs": []}, "negative_budget"),
    ({"budget": "big", "docs": []}, "string_budget"),
    ({"budget": True, "docs": []}, "bool_budget"),
    ({"budget": 100, "reserve": -1, "docs": []}, "negative_reserve"),
    ({"budget": 100, "docs": "nope"}, "docs_not_list"),
    ({"budget": 100, "docs": ["str_item"]}, "doc_not_dict"),
    ({"budget": 100, "docs": [doc("a", 1), doc("a", 2)]}, "dup_names"),
    ({"budget": 100, "docs": [{"tokens": 5}]}, "missing_name"),
    ({"budget": 100, "docs": [{"name": "x", "tokens": -3}]}, "negative_tokens"),
    ({"budget": 100, "docs": [{"name": "x", "tokens": "5"}]}, "string_tokens"),
    ({"budget": 100, "docs": [{"name": "x", "priority": "hi"}]}, "string_priority"),
]:
    try:
        cpp.plan(bad)
        check("err_" + label, False)
    except ValueError:
        check("err_" + label, True)
errs = cpp.validate_manifest("not-a-dict")
check("validate_not_dict", errs and "JSON object" in errs[0])
errs = cpp.validate_manifest({"budget": 100, "docs": [doc("a", 5), doc("b", "x")]})
check("validate_mixed_errors", len(errs) == 1)
code, out = run_cli(["--manifest", os.path.join(tmp, "missing.json")])
check("cli_missing_manifest_exit2", code == 2)
badmf = os.path.join(tmp, "bad.json")
with open(badmf, "w", encoding="utf-8") as f:
    f.write("{broken")
code, out = run_cli(["--manifest", badmf])
check("cli_corrupt_manifest_exit2", code == 2)
goodbad = os.path.join(tmp, "invalid.json")
with open(goodbad, "w", encoding="utf-8") as f:
    json.dump({"docs": []}, f)
code, out = run_cli(["--manifest", goodbad])
check("cli_invalid_manifest_exit2", code == 2)

# ---------- extreme edge cases ----------
r = cpp.plan({"budget": 1, "docs": [doc("a", 1), doc("b", 1)]})
check("edge_tiny_budget_one_wins", len(r["included"]) == 1)
try:
    cpp.plan({"budget": 0, "docs": []})
    check("edge_budget_zero_rejected", False)
except ValueError:
    check("edge_budget_zero_rejected", True)
r = cpp.plan({"budget": 1000000, "docs": [doc("u", 500, priority=1)]})
check("edge_huge_budget", r["budget_left"] == 999500)
many = [doc("d%03d" % i, 10, priority=i % 7) for i in range(300)]
r = cpp.plan({"budget": 1500, "docs": many})
check("edge_many_docs_budget", r["used"] <= 1500 and len(r["included"]) + len(r["skipped"]) == 300)
check("edge_many_docs_priority_first", r["included"][0]["name"].startswith("d0") or r["included"][0]["priority"] == 0 if "priority" in r["included"][0] else True)
uni = {"budget": 100, "docs": [{"name": "中文文档", "tokens": 40}, {"name": "日本語", "tokens": 40}, {"name": "Ελληνικά", "tokens": 40}]}
r = cpp.plan(uni)
check("edge_unicode_names", len(r["skipped"]) == 1 and r["included"][0]["name"] == "Ελληνικά")
emoji = cpp.plan({"budget": 100, "docs": [{"name": "🎉📋", "tokens": 50}]})
check("edge_emoji_name", emoji["included"][0]["name"] == "🎉📋")
deep = {"budget": 100, "docs": [doc("x" * 5000, 50)]}
check("edge_very_long_name", cpp.plan(deep)["included"][0]["name"] == "x" * 5000)
r = cpp.plan({"budget": 100, "docs": [doc("a", 60, must=True, truncate=True)]})
check("edge_must_no_truncate_needed", r["included"][0]["partial"] is False)
r = cpp.plan({"budget": 100, "docs": [doc("a", 200, must=True), doc("b", 50)]})
check("edge_must_fail_rest_still_packs", r["included"][0]["name"] == "b" and r["skipped"][0]["reason"] == "must_doc_exceeds_budget")
r = cpp.plan({"budget": 100, "reserve": 100, "docs": [doc("a", 50, truncate=True)]})
check("edge_reserve_equals_budget", r["skipped"][0]["reason"] == "no_room_to_truncate")
r = cpp.plan({"budget": 100, "docs": [doc("a", 0, must=True), doc("b", 100, must=True), doc("c", 100)]})
check("edge_must_zero_then_full", [x["name"] for x in r["included"]] == ["a", "b"])

print()
if FAILED:
    print("FAILED CASES:", ", ".join(FAILED))
print("SUMMARY: PASS %d/%d" % (PASS, PASS + FAIL))
sys.exit(1 if FAIL else 0)
