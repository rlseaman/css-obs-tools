# WAMO Script Status — 2026-03-22

## Overview

The `wamo` script queries the Minor Planet Center's "Where Are My
Observations?" (WAMO) service to check the processing status of
astrometry submitted by the Catalina Sky Survey.  It reads designation
files (`.neos` or `.mpcd`) from CSS nightly data directories and reports
per-object status from MPC's pipeline.  Optionally queries JPL Scout
for impact/PHA/close-approach alerts on NEOCP objects.

## Usage

```
wamo                          # default: batch query, auto Scout alerts
wamo --scout                  # show Scout data for all NEOCP objects
wamo --noscout                # suppress Scout lookups
wamo --nobatch                # sequential streaming (one query at a time)
wamo --timeout N              # curl timeout in seconds (default 15)
wamo --keepalive              # HTTP keepalive for sequential mode
wamo -m                       # sample 10 random mpcd designations
wamo -v                       # verbose (raw MPC responses)
wamo -q                       # quiet (suppress stderr messages)
wamo -s SITE -u "YYYY MM DD"  # explicit site and date
wamo -l <file>                # read designations from file
```

## Default Behavior

- **Batch mode**: all designations queried in one API call (~0.5s total
  vs ~0.5s per designation sequentially)
- **Auto Scout**: NEOCP objects are checked against JPL Scout; alerts
  shown only for non-zero impact rating, PHA=100%, or close approach
  < 7 Earth radii.  Use `--scout` to show all, `--noscout` to suppress.
- **Directory auto-detection**: if CWD lacks `.neos`/`.mpcd` files,
  tries `/data0/YYMmmDD` using tonight's UT date (rollover at 17:00 UT
  = 10:00 AM local for CSS, UTC-7)
- **Survey/follow-up prefix**: `svy`, `fup`, `s+f`, `s+s`, `f+f`
  derived from the field prefix in the CSS filename (N/S = survey,
  F/U = follow-up)
- **Deduplication**: each designation queried once regardless of how
  many `.neos` files contain it
- **Multi-date annotation**: `[also YYYY MM DD]` when MPC response
  includes observations from other nights

## Example Output

```
svy CEF3A92 has been queued to neo/new/incoming (new NEOCP or PCCP objects)
svy CEF4A62 is not a minor planet
svy CEF5M62 is on the NEOCP
s+f C1D0Q15 is on the NEOCP
    Scout: Imp 0 NEO 76% PHA 14%
           12obs 1.57d arc V=23.1 H=21.4 moid=0.1au rate=1.2"/hr
fup C1CX3P5 was published in MPEC 2026-F101 as 2026 FH2 [also 2026 03 18, 2026 03 19]
```

## Changes Made

### Bug fix: trkSub-format responses (critical)

MPC returns two response formats: obs80 (80-column + status) and trkSub
(`The trkSub 'XXX YYY' (obsid) status.`).  The script previously only
handled obs80 lines; trkSub lines were silently skipped by the date
filter, causing "not a minor planet", "deleted", and "artificial" to
all report as "has not been found."

**Fix**: trkSub lines are detected and parsed before the obs80 loop.

### Batch mode via JSON API

Batch queries use the new MPC API's JSON response mode, which returns
results keyed by the original query string.  This eliminates the
unreliable block-splitting required by the string-mode response, where
mid-block `*` markers and MPC-assigned designations differing from the
queried trkSub caused misalignment.

The `-m` (mpcd sampling) mode uses sequential queries because mpcd
objects are known/numbered asteroids whose batch responses are
particularly difficult to split reliably.

### Cross-date status visibility

The original script only extracted status keywords from obs80 lines
matching the target UT date.  When MPC's response contained observations
from prior nights (common for follow-up telescopes and objects that have
been identified with provisional designations), the status was invisible.

**Fix**: status keywords are now extracted from ALL obs80 lines in the
response.  The date filter is retained only for the `[also ...]`
annotation.  This means an observer at I52 querying a designation that
was published based on prior-night observations will see "was published"
instead of "no MPC response."

### Status priority: published > pending

When MPC's response includes both published (prior night) and pending
(tonight) observations of the same designation, `published` takes
priority.  The observer needs to know the object has been published —
that's the actionable information for deciding whether to continue
observing it.

### Three-way not-found distinction

| Output | Meaning |
|---|---|
| `was not found by MPC` | MPC explicitly responded "not found" |
| `is not a valid identifier` | MPC says the format is wrong |
| `no MPC response` | curl failure, timeout, or server down |

### JPL Scout integration (`--scout`)

For NEOCP objects, queries `ssd-api.jpl.nasa.gov/scout.api` (~0.15s
per lookup).  Two-line output:

```
    Scout: Imp 0 CA 7.4LD NEO 100% PHA 14%
           15obs 28.06d arc V=23.1 H=23.4 moid=0.09au rate=2.1"/hr
```

Line 1: impact rating, close approach (LD or ER if < 7 Earth radii),
NEO/PHA/GEO percentages.  Line 2: observational details.

**Auto mode** (default): Scout lines shown only when:
- Impact rating > 0
- PHA score = 100%
- Close approach < 7 Earth radii (displayed in ER)

### API endpoint fallback

Sequential queries try the old endpoint first, fall back to the new API:
- **Primary**: `https://minorplanetcenter.net//cgi-bin/cgipy/wamo2`
- **Fallback**: `https://data.minorplanetcenter.net/api/wamo`

Batch queries use the new API directly (JSON mode).

### Silent JSONL logging

Every query logged to `~/.wamo/wamo-SITE-YYYYMMDD.log`.  Records
include timestamp, designation, site, UT date, working directory,
parsed status, matched flag, active flags (batch/timeout/keepalive/scout),
and the full raw MPC response.

- **`matched: false`** for unrecognized statuses and network failures
- Prior days' logs gzipped on startup; warns if `~/.wamo/` > 100 MB
- Override with `WAMO_LOG` env var (empty = disable)

### mpcd sampling improvements

- Designations deduplicated before sampling (no duplicate queries)
- Sampling without replacement (Fisher-Yates)
- If <= 10 unique designations, all are queried
- Sequential mode forced (batch bypassed for mpcd)

## Verified MPC Response Formats

Tested against full 2026 archive: 190 nights, 2,495 designations across
all five active CSS sites (703, G96, I52, V00, V06).

### Statuses handled

| Status | Format | Response text |
|---|---|---|
| NEOCP/PCCP | obs80 | `is on the NEOCP/PCCP.` |
| Published | obs80 | `has been identified as X and published in MPEC Y.` |
| Pending | obs80 | `has been identified as X, publication is pending.` |
| ITF | obs80 | `has been placed in the Isolated Tracklet File (ITF).` |
| Not minor planet | trkSub | `is not a minor planet.` |
| Deleted | trkSub | `has been deleted.` |
| Artificial | trkSub | `was suspected to be artificial.` |
| Near-duplicate | trkSub | `was flagged as a near-duplicate.` |
| Not processed | trkSub | `has not been processed.` |
| Queued | trkSub | `is in the 'X' processing queue.` |
| Not found | explicit | `"D S" was not found after attempting a search.` |
| Invalid | explicit | `"D S" was not identified as a valid observation identifier.` |

### Known processing queues

| Queue | Description | Documented? |
|---|---|---|
| `verified` | Mixed obs, to be split and assigned | yes |
| `neo/new/incoming` | New NEOCP or PCCP objects | yes |
| `neocp/incoming` | NEOCP or PCCP followup | yes |
| `neo/mopp` | Unnumbered NEOs | yes |
| `neo/num` | Numbered NEOs | yes |
| `neo/newid` | NEO (p)recoveries | yes |
| `mba/itf` | Unidentified tracklets → ITF | yes |
| `mba/mopp` | Unnumbered MBAs | yes |
| `mba/num` | Numbered MBAs | yes |
| `mba/new` | Possible new MBAs | yes |
| `newcode` | Awaiting program code | yes |
| `tno/unn` | Unnumbered one-opposition TNOs | yes |
| `tno/mopp` | Unnumbered multi-opposition TNOs | yes |
| `tno/num` | Numbered TNOs | yes |
| `tno/newid` | TNO (p)recoveries | yes |
| `tno/new` | Possible new TNOs | yes |
| `sat/unn` | Unnumbered natural satellites | yes |
| `sat/num` | Numbered natural satellites | yes |
| `sat/new` | Possible new natural satellites | yes |
| `cmt/cmt` | Unnumbered comets | yes |
| `cmt/pct` | Numbered comets | yes |
| `cmt/new` | Possible new comets | yes |
| `artsat` | Artsat processing | no |
| `sat/art` | Artificial satellite processing | no |
| `sat` | Natural satellite processing | no |
| `problems` | Flagged for manual review | no |

### Still untested

- Rejected (wired for obs80 and trkSub)
- Obscode/whatcode (awaiting observatory code)
- Queued in obs80 format (only trkSub-format queued observed)

## Archive Benchmark — 2026, All Sites

| Site | Role | Nights | Designations | Sequential | Batch |
|------|------|--------|-------------|-----------|-------|
| 703 | Survey | 42 | 309 | 2.5 min | ~5s |
| G96 | Survey | 45 | 310 | 2.5 min | ~5s |
| I52 | Follow-up | 47 | 1,438 | 16.1 min | ~22s |
| V00 | Survey | 18 | 220 | 1.8 min | ~3s |
| V06 | Follow-up | 26 | 218 | 1.8 min | ~3s |
| **Total** | | **178** | **2,495** | **24.7 min** | **~38s** |

Per-designation cost: ~0.49s sequential, ~0.03s batch.

## Field Test Results — 2026-03-21

All five active CSS telescopes tested during live observing:

- **703** (survey, 18 desigs): 8 NEOCP, 3 published, 7 `sat/art` queue
- **G96** (survey, 9 desigs): 5 NEOCP, 2 published, 1 `neo/new/incoming`, 1 not-minor-planet
- **V00** (survey, 16 desigs): 10 NEOCP, 1 pending, 1 published, 1 deleted, 1 ITF
- **I52** (follow-up, 32 desigs): 22 NEOCP, 4 published, 3 `neo/newid`, 1 near-duplicate
- **V06** (follow-up, 8 desigs): 3 NEOCP, 5 published

## Test Suite

`wamo-test.tcl` — 22 offline tests covering all observed MPC response
formats.  Extracts the `trackstat` proc from `wamo` and tests it in
isolation with captured raw MPC responses.  No network access required.

```bash
tclsh wamo-test.tcl
```

Test categories:
- trkSub statuses (12): not-minor-planet, deleted, artificial,
  near-duplicate, not-processed, 7 queue types
- obs80 statuses (5): NEOCP, published, pending, ITF, cross-date
- Priority/multi-date (2): published+pending, cross-date published
- Explicit MPC responses (2): not-found, invalid identifier
- Empty response (1): no MPC response

MPC's database status flags map to wamo output as:
- `P` (published) → "was published"
- `p` (pending) → "is pending publication"
- `I` (ITF) → "is in the ITF"

## Field Test Results — 2026-03-22 (Second Night)

Automated 10-minute polling at 703, G96, I52, V00.

Notable findings:
- **Pipeline transit captured**: `neo/new/incoming` → NEOCP in ~10 min
  (C463MW1 at 703, multiple objects at V00)
- **MBA reclassification**: `neo/new/incoming` → `mba/mopp` → pending
  → published (C1D2L35 at I52, C1DAXW5 at V00)
- **"received but not processed"**: first live capture of this
  transient state (CEFEQ52 at I52), resolved to NEOCP in 10 min
- **Comet recovery**: C463L41 at 703 showed "was not found by MPC"
  for 8 hours before being identified as a known numbered comet
  (`cmt/pct` queue)
- **Cross-date fix validated**: C1D0QJ5 at I52 now correctly shows
  "was published" for observations from prior nights
- **New queue `mba/newid`**: MBA precoveries (K22K29K at V00)

## Architecture

- **Language**: Tcl — standard on RHEL 8.6, no dependencies beyond
  `tclsh` and `curl`
- **Single script**: one file for deployment to production machines
- **Batch**: JSON-mode API, results keyed by query string (no
  block-splitting). Forced off for `-m` mpcd mode.
- **Sequential**: old API primary, new API fallback. Streaming output.
- **Timeouts**: `--timeout N` (default 15s connect, 30s max)
- **Sort order**: alphabetical by designation (`lsort -dictionary`)
- **Directory auto-detection**: if CWD lacks data files, tries
  `/data0/YYMmmDD` using tonight's UT date (rollover at 17:00 UT)

## CSS Context

- Survey fields: N (north), S (south of celestial equator)
- Follow-up fields: F (scheduled), U (user-directed)
- Survey telescopes: 703, G96, V00
- Follow-up telescopes: I52, V06, G84
- Archive path: `/archive/TEL/YYYY/YYMmmDD/`
- Production data path: `/data0/YYMmmDD/`
- File naming: `TEL_YYYYMMDD_BIN_Xnnnnn_REP_SEQ.ext`

## MPC Context

The WAMO service had a protracted beta release with evolving return
formats.  CSS stopped trying to keep up, but MPC changes have slowed.
The logging system captures transient pipeline states (queued,
unprocessed, etc.) that typically vanish before morning review.

Two WAMO API endpoints exist:
- Old: `minorplanetcenter.net/cgi-bin/cgipy/wamo2` (string mode)
- New: `data.minorplanetcenter.net/api/wamo` (JSON and string modes)

Both return the same data.  The JSON mode provides structured
per-designation results that avoid the parsing ambiguities of the
string mode's concatenated output.
