# css-obs-tools

Command-line tools for working with Catalina Sky Survey observing data.

Each tool lives in its own directory with a dedicated README.  Tools are
standalone scripts with no package installation required — symlink into
`PATH` or run directly.

## Tools

| Directory | Language | Description |
|-----------|----------|-------------|
| [logdigest/](logdigest/) | Python | Distill CSS `control.tcl` nightly logs into structured summaries |
| [rteldigest/](rteldigest/) | Python | Parse KP 2.1m rtel logs and plot telescope performance |
| [wamo/](wamo/) | Tcl | Query MPC WAMO for astrometry processing status |

## Requirements

- **Python tools** (`logdigest`, `rteldigest`, `tcsplot`): Python 3.6+,
  standard library only (matplotlib for plotting)
- **Tcl tools** (`wamo`): `tclsh` and `curl` (standard on RHEL 8)

## Installation

```bash
# Run directly from tool directories
python3 logdigest/logdigest.py <logfile>
tclsh wamo/wamo

# Or symlink into PATH
ln -s $(pwd)/logdigest/logdigest.py ~/bin/logdigest
ln -s $(pwd)/wamo/wamo ~/bin/wamo
```

## Testing

```bash
tclsh wamo/wamo-test.tcl       # 22 offline tests for wamo parser
```

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

## Conventions

- Standalone scripts, no package installation required
- Pattern-based parsing: regex tables at top of file, first match wins
- Multiple output formats: human-readable (default), JSON/JSONL, CSV
- Tolerant of format evolution — unknown input is counted, not an error
