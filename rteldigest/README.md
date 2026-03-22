# rteldigest

Parse KP 2.1m TCS `rtel` server logs (BAIT protocol) into structured
event streams.  Extracts slew performance, pointing residuals, tracking
state, offsets, errors, and runaway detections from the timestamped
command-response transcripts.

## Usage

```bash
rteldigest.py rtel.2025-04-05T10:33:41Z              # human summary
rteldigest.py rtel.2025-04-05T10:33:41Z --jsonl       # JSON Lines events
rteldigest.py rtel.2025-04-05T10:33:41Z --csv         # CSV (point events)
rteldigest.py rtel.*.Z --jsonl                        # batch all logs
rteldigest.py --batch-dir /path/to/Data/ --jsonl      # all logs in directory
```

## Example output

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

## Output formats

- **Human summary** (default) — per-session and combined statistics
- **JSON Lines** (`--jsonl`) — one JSON object per event, self-describing.
  Different event types coexist; load with `pd.read_json(lines=True)`
- **CSV** (`--csv --type point`) — flat table for a single event type

## tcsplot

`tcsplot.py` generates matplotlib visualizations from rteldigest JSONL
output.  Produces settling time curves, pointing residual distributions,
and stacked multi-epoch comparisons.

## Reports

Analysis plots from KP 2.1m rtel logs across multiple epochs:

- `apr2024_*.png` — April 2024 pointing residuals and settling times
- `jun2023_*.png` — June 2023 baseline measurements
- `oct2023_*.png` — October 2023 measurements
- `stacked_*.png` — Multi-epoch stacked comparisons
- `nighttime40_*.png` — 40-night validated nighttime analysis
