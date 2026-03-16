# css-obs-tools

Command-line tools for working with Catalina Sky Survey observing data.

## Tools

### logdigest

Distill CSS `control.tcl` nightly logs into structured summaries.

A typical CSS control log is 400K+ lines of multiplexed output from the
TCS, camera, calibration, pipeline, and follow-up subsystems. `logdigest`
classifies each line and produces concise summaries of the night's
observing activity.

```bash
logdigest control.20260312.1.log              # human-readable summary
logdigest control.20260312.1.log --json        # structured JSON
logdigest control.20260312.1.log --timeline    # chronological events
logdigest control.20260312.1.log --filter tcs  # TCS commands only
logdigest control.20260312.1.log --filter error # errors and warnings
logdigest control.20260312.1.log --verbose     # show unclassified samples
logdigest control.20260312.1.log --stats       # detailed subcategory counts
```

**Design principles:**
- Pattern-based line classification (regex, first match wins)
- Tolerant of format evolution — unknown lines are counted, not errors
- No dependencies beyond Python 3 standard library
- New patterns can be added to `EVENT_PATTERNS` without changing logic
- Works on any CSS site's control logs (703, G96, I52, V06, KP21M, etc.)

**Example output:**
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

### rteldigest

Parse KP 2.1m TCS `rtel` server logs (BAIT protocol) into structured
event streams. Extracts slew performance, pointing residuals, tracking
state, offsets, errors, and runaway detections from the timestamped
command-response transcripts.

```bash
rteldigest rtel.2025-04-05T10:33:41Z              # human summary
rteldigest rtel.2025-04-05T10:33:41Z --jsonl       # JSON Lines events
rteldigest rtel.2025-04-05T10:33:41Z --csv         # CSV (point events)
rteldigest rtel.*.Z --jsonl                        # batch all logs
rteldigest --batch-dir /path/to/Data/ --jsonl      # all logs in directory
```

**Example output:**
```
Slew performance
----------------------------------------
  Total slews:      111
  Move distance:    0.000 — 141.499 deg  (median 35.393)
  Elapsed time:     0 — 255 s  (median 68)
  Slew rate:        0.002 — 0.845 deg/s  (median 0.511)
  Pointing resid:   0.4 — 29.9 arcsec  (median 5.0)
  Single-pass:      89
  Multi-pass:       14
  Small (<1°) slews: 32, median overhead 9.0s
  Large (>10°) slews: 78, median rate 0.549 deg/s
```

**Output formats:**
- Human summary (default) — per-session and combined statistics
- JSON Lines (`--jsonl`) — one JSON object per event, self-describing.
  Different event types coexist; load with `pd.read_json(lines=True)`
- CSV (`--csv --type point`) — flat table for a single event type

## Installation

No installation needed — these are standalone scripts requiring only
Python 3.6+.

```bash
# Option 1: run directly
python3 logdigest.py <logfile>

# Option 2: symlink into PATH
ln -s $(pwd)/logdigest.py ~/bin/logdigest
```

## Adding new classification patterns

Patterns are defined at the top of each tool as `_p(category, subcategory, regex)`
calls. To recognize a new line format:

```python
_p("pipeline", "new_tool", r"new_tool_output_pattern")
```

Order matters — first match wins. Place specific patterns before general ones.

## Sites

| Code | Telescope | Location |
|------|-----------|----------|
| 703 | Catalina Schmidt 0.7m | Mt. Bigelow |
| G96 | Mt. Lemmon 1.5m | Mt. Lemmon |
| I52 | Steward/Bok 2.3m | Kitt Peak |
| V06 | Kuiper 1.54m | Mt. Bigelow |
| KP21M | KPNO 2.1m | Kitt Peak |
