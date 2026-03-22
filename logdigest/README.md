# logdigest

Distill CSS `control.tcl` nightly logs into structured summaries.

A typical CSS control log is 400K+ lines of multiplexed output from the
TCS, camera, calibration, pipeline, and follow-up subsystems. `logdigest`
classifies each line and produces concise summaries of the night's
observing activity.

## Usage

```bash
logdigest.py control.20260312.1.log              # human-readable summary
logdigest.py control.20260312.1.log --json        # structured JSON
logdigest.py control.20260312.1.log --timeline    # chronological events
logdigest.py control.20260312.1.log --filter tcs  # TCS commands only
logdigest.py control.20260312.1.log --filter error # errors and warnings
logdigest.py control.20260312.1.log --verbose     # show unclassified samples
logdigest.py control.20260312.1.log --stats       # detailed subcategory counts
```

## Example output

```
======================================================================
CSS Control Log Summary
======================================================================
  Site:       V06
  Date:       2026-03-12
  UT window:  01:29:20 — 07:36:57  (6.13 hrs)
  Log lines:  425,725

Observing Activity
----------------------------------------
  Targets observed:   20
  Total slews:        614
  Unique pointings:   79
  Total exposures:    55
  Follow-up events:   17
  MPC submissions:    17
```

## Design

- Pattern-based line classification (regex, first match wins)
- Tolerant of format evolution — unknown lines are counted, not errors
- No dependencies beyond Python 3.6+ standard library
- New patterns can be added to `EVENT_PATTERNS` without changing logic
- Works on any CSS site's control logs (703, G96, I52, V06, etc.)

## Adding patterns

Patterns are defined at the top of the script as
`_p(category, subcategory, regex)` calls.  Order matters — first match
wins.  Place specific patterns before general ones.

## Reports

- `reports/kp21m-nighttime-sessions.md` — Validated inventory of 40
  nighttime observing sessions, 2021-2025
