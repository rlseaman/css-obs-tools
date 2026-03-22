# css-obs-tools

General-purpose tools for Catalina Sky Survey observing operations.

## Project scope

This repo is a home for standalone CLI tools that parse, analyze, and
visualize CSS observing data. Tools should work across all CSS sites
(703, G96, I52, V00, V06) unless inherently site-specific.

## Current tools

- **logdigest.py** — Distill CSS control.tcl nightly logs into structured summaries
- **rteldigest.py** — Parse KP 2.1m rtel (BAIT protocol) logs into event streams
- **tcsplot.py** — Plot telescope performance from rteldigest JSONL output
- **wamo** — Query MPC WAMO for astrometry processing status, with JPL Scout integration
- **wamo-test.tcl** — Offline test suite for wamo parser (22 tests)

## Conventions

- Python 3.6+, standard library only (matplotlib allowed for plotting)
- Tcl for wamo (standard on RHEL 8.6, no package dependencies)
- Standalone scripts, no package installation required
- Pattern-based parsing: regex tables at top of file, first match wins
- Multiple output formats: human-readable (default), JSON/JSONL, CSV
- Tolerant of format evolution — unknown input is counted, not an error

## Directory layout

- `scratch/` — local working area, gitignored
- `reports/` — analysis output (plots, markdown); some gitignored
- `wamo-logs/` — captured wamo log files for analysis, gitignored
- `wamo-status.md` — detailed wamo documentation and field test results
- Top-level `*.py` — Python tools
- `wamo` — Tcl script, deployable to telescope computers
