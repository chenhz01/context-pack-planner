# Changelog

## v0.1.1 — 2026-10-11

Round-2 revision after a line-by-line self-review of v0.1.0:

- Self-test suite expanded from 33 to 57 cases (+73%): added exception-path
  coverage (13 invalid-manifest variants: bool/negative/string budget,
  duplicate names, negative tokens) and extreme-edge coverage (300-doc
  packing, Unicode names incl. Greek/CJK/emoji, 5000-char names,
  reserve == budget, must-doc failure interaction with the rest).
- Tightened validation: `reserve` greater than `budget` is now a
  `ValueError` ("'reserve' must not exceed 'budget'") instead of producing a
  plan with used > budget.
- Fixed a helper bug in the self-test (a doc without a `tokens` key now
  exercises the default-tokens-0 path).
- All tests re-run green: `SUMMARY: PASS 57/57` (measured 2026-10-11).

## v0.1.0 — 2026-10-11

Initial release: manifest validation, must-include reserve pass, greedy
priority packing with deterministic tie-breaks, truncate/partial fitting,
structured skip reasons, SHA-256 plan_hash, argparse CLI with --manifest /
--out / stdin. 33 self-test cases.
