# css-obs-tools

General-purpose tools for Catalina Sky Survey observing operations.

## Project scope

This repo is a home for standalone CLI tools that parse, analyze, and
visualize CSS observing data. Tools should work across all CSS sites
(703, G96, I52, V00, V06) unless inherently site-specific.

## Current tools

- **logdigest/** — Distill CSS control.tcl nightly logs into structured summaries
- **rteldigest/** — Parse KP 2.1m rtel logs and plot telescope performance (rteldigest, tcsplot)
- **wamo/** — Query MPC WAMO for astrometry processing status, with JPL Scout integration

## Conventions

- Python 3.6+, standard library only (matplotlib allowed for plotting)
- Tcl for wamo (standard on RHEL 8.6, no package dependencies)
- Standalone scripts, no package installation required
- Pattern-based parsing: regex tables at top of file, first match wins
- Multiple output formats: human-readable (default), JSON/JSONL, CSV
- Tolerant of format evolution — unknown input is counted, not an error

## Directory layout

- `logdigest/` — log digest tool and reports
- `rteldigest/` — rtel digest, tcsplot, and analysis plots
- `wamo/` — WAMO status checker, test suite, and docs
- `scratch/` — local working area, gitignored
