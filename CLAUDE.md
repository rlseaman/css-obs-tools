# css-obs-tools

General-purpose tools for Catalina Sky Survey observing operations.

## Project scope

This repo is a home for standalone CLI tools that parse, analyze, and
visualize CSS observing data. Tools should work across all CSS sites
(703, G96, I52, V06, KP21M) unless inherently site-specific.

## Current tools

- **logdigest.py** — Distill CSS control.tcl nightly logs into structured summaries
- **rteldigest.py** — Parse KP 2.1m rtel (BAIT protocol) logs into event streams
- **tcsplot.py** — Plot telescope performance from rteldigest JSONL output

## Conventions

- Python 3.6+, standard library only (matplotlib allowed for plotting)
- Standalone scripts, no package installation required
- Pattern-based parsing: regex tables at top of file, first match wins
- Multiple output formats: human-readable (default), JSON/JSONL, CSV
- Tolerant of format evolution — unknown input is counted, not an error

## Directory layout

- `scratch/` — local working area, gitignored
- `reports/` — analysis output (plots, markdown); some gitignored
- Top-level `*.py` — the tools themselves
