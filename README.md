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

### wamo

Query the Minor Planet Center's WAMO service for the processing status
of CSS astrometric submissions.  Reads `.neos` or `.mpcd` designation
files from the nightly data directory and reports per-object status.

```bash
cd /data0/26Mar22
wamo                           # default: batch query, auto Scout alerts
wamo --scout                   # show JPL Scout data for all NEOCP objects
wamo --noscout                 # suppress Scout lookups
wamo --nobatch                 # sequential streaming output
wamo -m                        # sample from mpcd (incidental MBA) files
wamo -v                        # verbose: raw MPC responses
wamo -q                        # quiet: suppress stderr messages
```

**Key features:**
- Handles all known MPC response formats (obs80, trkSub, explicit)
- Batch queries via MPC JSON API (default, ~12x faster than sequential)
- JPL Scout alerts for NEOCP objects (impact, PHA, close approach)
- Survey/follow-up annotation (`svy`, `fup`, `s+f`) from CSS filenames
- Multi-date annotation when MPC response includes prior-night observations
- Silent JSONL logging to `~/.wamo/` for post-hoc analysis
- Auto-detects tonight's data directory if not run from one

**Example output:**
```
svy CEF3A92 has been queued to neo/new/incoming (new NEOCP or PCCP objects)
svy CEF4A62 is not a minor planet
s+f C1D0Q15 is on the NEOCP
    Scout: Imp 0 NEO 76% PHA 14%
           12obs 1.57d arc V=23.1 H=21.4 moid=0.1au rate=1.2"/hr
fup C1CX3P5 was published in MPEC 2026-F101 as 2026 FH2 [also 2026 03 18]
```

See `wamo-status.md` for complete documentation including all MPC
response formats, processing queues, and architecture details.

## Installation

No installation needed — these are standalone scripts.  `logdigest`,
`rteldigest`, and `tcsplot` require Python 3.6+.  `wamo` requires
`tclsh` and `curl` (standard on RHEL 8).

```bash
# Option 1: run directly
python3 logdigest.py <logfile>
tclsh wamo

# Option 2: symlink into PATH
ln -s $(pwd)/logdigest.py ~/bin/logdigest
ln -s $(pwd)/wamo ~/bin/wamo
```

## Testing

```bash
tclsh wamo-test.tcl            # offline test suite for wamo parser
```

## Adding new classification patterns

Patterns are defined at the top of each tool as `_p(category, subcategory, regex)`
calls. To recognize a new line format:

```python
_p("pipeline", "new_tool", r"new_tool_output_pattern")
```

Order matters — first match wins. Place specific patterns before general ones.

## Sites

| Code | Telescope | Role | Location |
|------|-----------|------|----------|
| 703 | Catalina Schmidt 0.7m | Survey | Mt. Bigelow |
| G96 | Mt. Lemmon 1.5m | Survey | Mt. Lemmon |
| V00 | Steward/Bok 2.3m | Survey | Kitt Peak |
| I52 | Mt. Lemmon 1.0m | Follow-up | Mt. Lemmon |
| V06 | Kuiper 1.54m | Follow-up | Mt. Bigelow |
| G84 | Schulman 0.8m | Follow-up | Mt. Lemmon |
| KP21M | KPNO 2.1m | — | Kitt Peak |
