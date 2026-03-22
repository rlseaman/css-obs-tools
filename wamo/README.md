# wamo

Query the Minor Planet Center's WAMO service for the processing status
of CSS astrometric submissions.  Reads `.neos` or `.mpcd` designation
files from the nightly data directory and reports per-object status.

## Usage

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

## Example output

```
svy CEF3A92 has been queued to neo/new/incoming (new NEOCP or PCCP objects)
svy CEF4A62 is not a minor planet
s+f C1D0Q15 is on the NEOCP
    Scout: Imp 0 NEO 76% PHA 14%
           12obs 1.57d arc V=23.1 H=21.4 moid=0.1au rate=1.2"/hr
fup C1CX3P5 was published in MPEC 2026-F101 as 2026 FH2 [also 2026 03 18]
```

## Key features

- Handles all known MPC response formats (obs80, trkSub, explicit)
- Batch queries via MPC JSON API (default, ~12x faster than sequential)
- JPL Scout alerts for NEOCP objects (impact, PHA, close approach)
- Survey/follow-up annotation (`svy`, `fup`, `s+f`) from CSS filenames
- Multi-date annotation when MPC response includes prior-night observations
- Silent JSONL logging to `~/.wamo/` for post-hoc analysis
- Auto-detects tonight's data directory if not run from one

## Testing

```bash
tclsh wamo-test.tcl            # 22 offline tests, no network required
```

## Documentation

See [wamo-status.md](wamo-status.md) for complete documentation
including all MPC response formats, processing queues, field test
results, and architecture details.
