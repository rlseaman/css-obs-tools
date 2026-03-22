#!/usr/bin/env python3
"""
rteldigest — Parse KP 2.1m TCS rtel logs into structured event streams.

Reads the timestamped command-response logs produced by the rtel server
(BAIT protocol) and extracts structured events: slews, tracking state,
offsets, encoder readings, errors, and runaway detections.

Designed for the rtel.YYYY-MM-DDTHH:MM:SSZ log files in the Sells
archive. Tolerant of format variations across the 2020-2025 operational
period.

Usage:
    rteldigest.py <logfile>                    # human-readable summary
    rteldigest.py <logfile> --jsonl             # JSON Lines event stream
    rteldigest.py <logfile> --csv               # CSV per event type
    rteldigest.py <logfile> --csv --type point  # CSV for point events only
    rteldigest.py *.log --batch --jsonl         # process multiple logs
    rteldigest.py --batch-dir /path/to/Data/ --jsonl  # all logs in directory
"""

import re
import sys
import json
import csv
import argparse
import os
from datetime import datetime, timedelta
from collections import Counter, OrderedDict
from pathlib import Path
from io import StringIO


# ---------------------------------------------------------------------------
# Log line parsing
# ---------------------------------------------------------------------------

# Timestamp pattern at start of line
TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\s+(.*)')

# PMAC parameter readback
PMAC_RE = re.compile(r'^pmac\s+([<>-]+)\s+(.*)')

# Point debug output
POINT_DEBUG_RE = re.compile(
    r'point:\s+dha=([-\d.]+)\s+ddec=([-\d.]+)\s+arc=([-\d.]+)\s+pass=(\d+)'
)
POINT_TARGET_RE = re.compile(r'point:\s+at target arc=([-\d.]+)\s+pass=(\d+)')
POINT_DIST_RE = re.compile(
    r'point:\s+dist=([-\d.]+)\s+dra=([-\d.]+)\s+ddec=([-\d.]+)'
)


def parse_timestamp(s):
    """Parse ISO 8601 timestamp (without Z)."""
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def parse_coordinates(token_str):
    """Extract RA/Dec or HA/Dec from a command string."""
    coords = {}
    # RA in sexagesimal
    m = re.search(r'ra=([+\-]?[\d:.]+)', token_str)
    if m:
        coords['ra'] = m.group(1)
    # Dec in sexagesimal or decimal
    m = re.search(r'dec=([+\-]?[\d:.]+)', token_str)
    if m:
        coords['dec'] = m.group(1)
    # HA
    m = re.search(r'ha=([+\-]?[\d.]+)', token_str)
    if m:
        coords['ha'] = float(m.group(1))
    # Equinox
    m = re.search(r'equinox=(\d+\.?\d*)', token_str)
    if m:
        coords['equinox'] = float(m.group(1))
    return coords


def parse_done_point(response):
    """Parse 'done point move=27.848 dist=0.0073 pass=1'."""
    result = {}
    m = re.search(r'move=([\d.]+)', response)
    if m:
        result['move_deg'] = float(m.group(1))
    m = re.search(r'dist=([\d.]+)', response)
    if m:
        result['residual_deg'] = float(m.group(1))
    m = re.search(r'pass=(\d+)', response)
    if m:
        result['passes'] = int(m.group(1))
    return result


def parse_done_where(response):
    """Parse 'done where ra=... dec=... ha=... alt=... az=...'."""
    result = {}
    for key in ('ra', 'dec', 'name', 'mode'):
        m = re.search(rf'{key}=([^\s]+)', response)
        if m:
            result[key] = m.group(1)
    # 'type=' in where response means encoder type (abs/inc), not event type
    m = re.search(r'type=([^\s]+)', response)
    if m:
        result['encoder_type'] = m.group(1)
    for key in ('ha', 'secz', 'alt', 'az'):
        m = re.search(rf'{key}=([-\d.]+)', response)
        if m:
            result[key] = float(m.group(1))
    return result


def parse_done_encoder(response):
    """Parse 'done encoder ha=... dec=... bar=... oat=... hum=...'."""
    result = {}
    for key in ('ha', 'dec', 'dha', 'ddec', 'bar', 'oat', 'hum', 'wave'):
        m = re.search(rf'{key}=([-\d.]+)', response)
        if m:
            result[key] = float(m.group(1))
    m = re.search(r'type=(\w+)', response)
    if m:
        result['encoder_type'] = m.group(1)
    return result


def parse_done_track(response):
    """Parse 'done track ha=15.0411 dec=0.0000'."""
    result = {}
    m = re.search(r'ha=([-\d.]+)', response)
    if m:
        result['ha_rate'] = float(m.group(1))
    m = re.search(r'dec=([-\d.]+)', response)
    if m:
        result['dec_rate'] = float(m.group(1))
    return result


def parse_done_state(response):
    """Parse 'done state awning=... motion=... ra=... dec=...'."""
    result = {}
    for key in ('awning', 'motion', 'mirror', 'panic', 'platform',
                'ptel', 'pdrive', 'pump', 'fanbld', 'fantel', 'fanwof',
                'preha', 'predec', 'diving'):
        m = re.search(rf'{key}=(\S+)', response)
        if m:
            result[key] = m.group(1)
    for key in ('domeaz', 'focus', 'trackha', 'trackdec',
                'ra', 'dec', 'ha', 'alt', 'az', 'equinox',
                'windspeed', 'humidity', 'oat', 'bar', 'cloud',
                'rain', 'dew', 'peak'):
        m = re.search(rf'{key}=([-\d.]+)', response)
        if m:
            result[key] = float(m.group(1))
    for key in ('limE', 'limW', 'limN', 'limS'):
        m = re.search(rf'{key}=(\S+)', response)
        if m:
            result[key] = m.group(1)
    return result


def parse_done_runaway(response):
    """Parse 'done runaway runaway=0 slewing=0'."""
    result = {}
    m = re.search(r'runaway=(\d+)', response)
    if m:
        result['runaway'] = int(m.group(1))
    m = re.search(r'slewing=(\d+)', response)
    if m:
        result['slewing'] = int(m.group(1))
    return result


# ---------------------------------------------------------------------------
# Event extraction
# ---------------------------------------------------------------------------

def extract_events(filepath):
    """Parse an rtel log file into a list of structured events."""
    events = []
    pending_point = None  # accumulate point sub-events
    pmac_params = {}      # PMAC parameter readbacks from startup

    session_start = None
    session_file = str(filepath)

    # Extract session date from filename
    fname = Path(filepath).name
    m = re.search(r'rtel\.(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z', fname)
    if m:
        session_start = parse_timestamp(m.group(1))
    elif re.search(r'rtel\.log', fname):
        session_start = None  # current log, no fixed start

    with open(filepath, 'r', errors='replace') as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip()

            # --- Timestamped lines ---
            ts_match = TS_RE.match(line)
            if ts_match:
                ts = parse_timestamp(ts_match.group(1))
                content = ts_match.group(2).strip()

                # Startup line
                if content.startswith('Welcome to port='):
                    events.append({
                        'type': 'startup',
                        'time': ts.isoformat() + 'Z',
                        'content': content,
                        'file': session_file,
                        'line': lineno,
                    })
                    continue

                # Point command
                if re.match(r'point\s', content):
                    coords = parse_coordinates(content)
                    pending_point = {
                        'type': 'point',
                        'time_start': ts.isoformat() + 'Z',
                        'command': content,
                        'file': session_file,
                        'line': lineno,
                    }
                    pending_point.update(coords)
                    continue

                # Done point
                if content.startswith('done point'):
                    result = parse_done_point(content)
                    if pending_point:
                        pending_point['time_end'] = ts.isoformat() + 'Z'
                        t0 = parse_timestamp(pending_point['time_start'][:-1])
                        if t0:
                            pending_point['elapsed_s'] = (ts - t0).total_seconds()
                        pending_point.update(result)
                        if result.get('move_deg') and pending_point.get('elapsed_s'):
                            e = pending_point['elapsed_s']
                            if e > 0:
                                pending_point['slew_rate_deg_s'] = round(
                                    result['move_deg'] / e, 3)
                        events.append(pending_point)
                        pending_point = None
                    else:
                        events.append({
                            'type': 'point',
                            'time_end': ts.isoformat() + 'Z',
                            'file': session_file,
                            'line': lineno,
                            **result,
                        })
                    continue

                # Error point (point failed)
                if content.startswith('ERROR point'):
                    ev = {
                        'type': 'error',
                        'subtype': 'point',
                        'time': ts.isoformat() + 'Z',
                        'message': content,
                        'file': session_file,
                        'line': lineno,
                    }
                    if pending_point:
                        ev['time_start'] = pending_point.get('time_start')
                        ev['command'] = pending_point.get('command')
                        pending_point = None
                    events.append(ev)
                    continue

                # Track command
                if re.match(r'track\s', content) or content == 'track':
                    events.append({
                        'type': 'track',
                        'time': ts.isoformat() + 'Z',
                        'command': content,
                        'file': session_file,
                        'line': lineno,
                    })
                    continue

                # Done track
                if content.startswith('done track'):
                    result = parse_done_track(content)
                    events.append({
                        'type': 'track_response',
                        'time': ts.isoformat() + 'Z',
                        'file': session_file,
                        'line': lineno,
                        **result,
                    })
                    continue

                # Offset command
                if re.match(r'offset\s', content):
                    events.append({
                        'type': 'offset',
                        'time': ts.isoformat() + 'Z',
                        'command': content,
                        'file': session_file,
                        'line': lineno,
                    })
                    continue

                # Done offset
                if content.startswith('done offset'):
                    events.append({
                        'type': 'offset_done',
                        'time': ts.isoformat() + 'Z',
                        'file': session_file,
                        'line': lineno,
                    })
                    continue

                # Where command and response
                if content.startswith('where'):
                    events.append({
                        'type': 'where',
                        'time': ts.isoformat() + 'Z',
                        'command': content,
                        'file': session_file,
                        'line': lineno,
                    })
                    continue

                if content.startswith('done where'):
                    result = parse_done_where(content)
                    events.append({
                        'type': 'where_response',
                        'time': ts.isoformat() + 'Z',
                        'file': session_file,
                        'line': lineno,
                        **result,
                    })
                    continue

                # Encoder
                if content.startswith('encoder') or content.startswith('done encoder'):
                    if content.startswith('done encoder'):
                        result = parse_done_encoder(content)
                        events.append({
                            'type': 'encoder',
                            'time': ts.isoformat() + 'Z',
                            'file': session_file,
                            'line': lineno,
                            **result,
                        })
                    continue

                # State
                if content.startswith('done state'):
                    result = parse_done_state(content)
                    events.append({
                        'type': 'state',
                        'time': ts.isoformat() + 'Z',
                        'file': session_file,
                        'line': lineno,
                        **result,
                    })
                    continue

                # Runaway
                if 'runaway' in content.lower():
                    if content.startswith('done runaway'):
                        result = parse_done_runaway(content)
                        events.append({
                            'type': 'runaway',
                            'time': ts.isoformat() + 'Z',
                            'file': session_file,
                            'line': lineno,
                            **result,
                        })
                    elif 'ERROR' in content:
                        events.append({
                            'type': 'error',
                            'subtype': 'runaway',
                            'time': ts.isoformat() + 'Z',
                            'message': content,
                            'file': session_file,
                            'line': lineno,
                        })
                    continue

                # Dome
                if content.startswith('done dome') or content.startswith('dome '):
                    events.append({
                        'type': 'dome',
                        'time': ts.isoformat() + 'Z',
                        'content': content,
                        'file': session_file,
                        'line': lineno,
                    })
                    continue

                # Power/preload/pump
                for cmd in ('power', 'preload', 'pump'):
                    if content.startswith(cmd) or content.startswith(f'done {cmd}'):
                        events.append({
                            'type': 'power',
                            'time': ts.isoformat() + 'Z',
                            'content': content,
                            'file': session_file,
                            'line': lineno,
                        })
                        break
                else:
                    # Any ERROR
                    if content.startswith('ERROR'):
                        events.append({
                            'type': 'error',
                            'subtype': 'general',
                            'time': ts.isoformat() + 'Z',
                            'message': content,
                            'file': session_file,
                            'line': lineno,
                        })
                continue

            # --- Non-timestamped lines ---

            # Startup parameters
            if line.startswith('Create debug='):
                m = re.search(r'debug=(\S+)\s+wallace=(\S+)\s+noabs=(\d+)', line)
                if m:
                    events.append({
                        'type': 'config',
                        'time': session_start.isoformat() + 'Z' if session_start else None,
                        'debug': m.group(1),
                        'wallace': m.group(2),
                        'noabs': int(m.group(3)),
                        'file': session_file,
                        'line': lineno,
                    })
                continue

            # PMAC parameters
            pmac_m = PMAC_RE.match(line)
            if pmac_m:
                direction = pmac_m.group(1)
                value = pmac_m.group(2)
                if '-->' in direction:
                    pmac_params['_last_query'] = value
                elif '<--' in direction and '_last_query' in pmac_params:
                    pmac_params[pmac_params['_last_query']] = value
                continue

            # Axis scale factors
            m = re.match(r'(ha|dec|az)\s+ppdeg=([\d.]+)', line)
            if m:
                events.append({
                    'type': 'config',
                    'time': session_start.isoformat() + 'Z' if session_start else None,
                    'axis': m.group(1),
                    'ppdeg': float(m.group(2)),
                    'file': session_file,
                    'line': lineno,
                })
                continue

    # Add PMAC config as a single event if we got any
    clean_pmac = {k: v for k, v in pmac_params.items() if k != '_last_query'}
    if clean_pmac:
        events.append({
            'type': 'pmac_config',
            'time': session_start.isoformat() + 'Z' if session_start else None,
            'params': clean_pmac,
            'file': session_file,
            'line': 0,
        })

    return events


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

def summarize(events, filepath):
    """Produce a human-readable summary of a session."""
    summary = OrderedDict()
    summary['file'] = str(filepath)

    type_counts = Counter(e['type'] for e in events)
    summary['event_counts'] = dict(type_counts.most_common())
    summary['total_events'] = len(events)

    # Time window
    times = [e.get('time') or e.get('time_start') for e in events if e.get('time') or e.get('time_start')]
    if times:
        summary['first_event'] = min(times)
        summary['last_event'] = max(times)

    # Point events
    points = [e for e in events if e['type'] == 'point' and 'move_deg' in e]
    if points:
        moves = [p['move_deg'] for p in points]
        elapsed = [p['elapsed_s'] for p in points if 'elapsed_s' in p]
        residuals = [p['residual_deg'] for p in points if 'residual_deg' in p]
        passes_list = [p['passes'] for p in points if 'passes' in p]
        rates = [p['slew_rate_deg_s'] for p in points if 'slew_rate_deg_s' in p]

        summary['slews'] = {
            'count': len(points),
            'move_deg': {
                'min': round(min(moves), 3),
                'max': round(max(moves), 3),
                'median': round(sorted(moves)[len(moves)//2], 3),
            },
            'elapsed_s': {
                'min': min(elapsed) if elapsed else None,
                'max': max(elapsed) if elapsed else None,
                'median': sorted(elapsed)[len(elapsed)//2] if elapsed else None,
            },
            'residual_arcsec': {
                'min': round(min(residuals) * 3600, 1) if residuals else None,
                'max': round(max(residuals) * 3600, 1) if residuals else None,
                'median': round(sorted(residuals)[len(residuals)//2] * 3600, 1) if residuals else None,
            },
            'slew_rate_deg_s': {
                'min': round(min(rates), 3) if rates else None,
                'max': round(max(rates), 3) if rates else None,
                'median': round(sorted(rates)[len(rates)//2], 3) if rates else None,
            },
            'multi_pass': sum(1 for p in passes_list if p > 1),
            'single_pass': sum(1 for p in passes_list if p == 1),
        }

        # Small vs large slew statistics
        small = [p for p in points if p['move_deg'] < 1.0]
        large = [p for p in points if p['move_deg'] >= 10.0]
        if small:
            small_elapsed = [p['elapsed_s'] for p in small if 'elapsed_s' in p]
            summary['slews']['small_slew_overhead_s'] = {
                'count': len(small),
                'median_time': round(sorted(small_elapsed)[len(small_elapsed)//2], 1) if small_elapsed else None,
            }
        if large:
            large_rates = [p['slew_rate_deg_s'] for p in large if 'slew_rate_deg_s' in p]
            summary['slews']['large_slew_rate'] = {
                'count': len(large),
                'median_rate': round(sorted(large_rates)[len(large_rates)//2], 3) if large_rates else None,
            }

    # Offsets
    offsets = [e for e in events if e['type'] == 'offset']
    if offsets:
        summary['offsets'] = {'count': len(offsets)}

    # Errors
    errors = [e for e in events if e['type'] == 'error']
    if errors:
        summary['errors'] = {
            'count': len(errors),
            'messages': [e['message'][:120] for e in errors[:10]],
        }

    # Runaway events
    runaways = [e for e in events if e['type'] == 'runaway']
    active = [r for r in runaways if r.get('runaway') == 1]
    if runaways:
        summary['runaways'] = {
            'queries': len(runaways),
            'active_detections': len(active),
        }

    # Config
    configs = [e for e in events if e['type'] == 'config']
    for c in configs:
        if 'wallace' in c:
            summary['pointing_model'] = c['wallace']
        if 'debug' in c:
            summary['debug_level'] = c['debug']

    return summary


def format_human(summary):
    """Format summary as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("rtel Session Summary")
    lines.append("=" * 60)
    lines.append(f"  File:  {summary['file']}")
    if 'first_event' in summary:
        lines.append(f"  From:  {summary['first_event']}")
        lines.append(f"  To:    {summary['last_event']}")
    lines.append(f"  Events: {summary['total_events']}")
    if 'pointing_model' in summary:
        lines.append(f"  Model: {summary['pointing_model']}")
    lines.append("")

    ec = summary.get('event_counts', {})
    lines.append("Event counts")
    lines.append("-" * 40)
    for etype, count in sorted(ec.items(), key=lambda x: -x[1]):
        lines.append(f"  {etype:20s}  {count:5d}")
    lines.append("")

    slews = summary.get('slews')
    if slews:
        lines.append("Slew performance")
        lines.append("-" * 40)
        lines.append(f"  Total slews:      {slews['count']}")
        md = slews['move_deg']
        lines.append(f"  Move distance:    {md['min']:.3f} — {md['max']:.3f} deg  (median {md['median']:.3f})")
        el = slews['elapsed_s']
        if el['min'] is not None:
            lines.append(f"  Elapsed time:     {el['min']:.0f} — {el['max']:.0f} s  (median {el['median']:.0f})")
        sr = slews['slew_rate_deg_s']
        if sr['min'] is not None:
            lines.append(f"  Slew rate:        {sr['min']:.3f} — {sr['max']:.3f} deg/s  (median {sr['median']:.3f})")
        ra = slews['residual_arcsec']
        if ra['min'] is not None:
            lines.append(f"  Pointing resid:   {ra['min']:.1f} — {ra['max']:.1f} arcsec  (median {ra['median']:.1f})")
        lines.append(f"  Single-pass:      {slews['single_pass']}")
        lines.append(f"  Multi-pass:       {slews['multi_pass']}")
        so = slews.get('small_slew_overhead_s')
        if so:
            lines.append(f"  Small (<1°) slews: {so['count']}, median overhead {so['median_time']}s")
        lr = slews.get('large_slew_rate')
        if lr:
            lines.append(f"  Large (>10°) slews: {lr['count']}, median rate {lr['median_rate']} deg/s")
        lines.append("")

    offsets = summary.get('offsets')
    if offsets:
        lines.append(f"Offsets: {offsets['count']}")
        lines.append("")

    errors = summary.get('errors')
    if errors:
        lines.append(f"Errors ({errors['count']})")
        lines.append("-" * 40)
        for msg in errors['messages']:
            lines.append(f"  {msg}")
        lines.append("")

    runaways = summary.get('runaways')
    if runaways:
        lines.append(f"Runaway checks: {runaways['queries']}  active: {runaways['active_detections']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def events_to_csv(events, event_type, outfile=None):
    """Export events of a given type as CSV."""
    filtered = [e for e in events if e['type'] == event_type]
    if not filtered:
        return ""

    # Collect all keys across events of this type
    all_keys = OrderedDict()
    for e in filtered:
        for k in e:
            if k not in all_keys:
                all_keys[k] = True

    output = StringIO() if outfile is None else outfile
    writer = csv.DictWriter(output, fieldnames=list(all_keys.keys()),
                            extrasaction='ignore')
    writer.writeheader()
    for e in filtered:
        # Flatten any nested dicts for CSV
        flat = {}
        for k, v in e.items():
            if isinstance(v, dict):
                flat[k] = json.dumps(v)
            else:
                flat[k] = v
        writer.writerow(flat)

    if outfile is None:
        return output.getvalue()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse KP 2.1m TCS rtel logs into structured events.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("logfiles", nargs='*', help="rtel log file(s)")
    parser.add_argument("--batch-dir", help="Process all rtel.* files in directory")
    parser.add_argument("--jsonl", action="store_true", help="Output as JSON Lines")
    parser.add_argument("--csv", action="store_true", help="Output as CSV")
    parser.add_argument("--type", default="point",
                        help="Event type for CSV export (default: point)")
    parser.add_argument("--json-summary", action="store_true",
                        help="Output summary as JSON")

    args = parser.parse_args()

    # Collect input files
    files = list(args.logfiles)
    if args.batch_dir:
        dirpath = Path(args.batch_dir)
        files.extend(sorted(str(f) for f in dirpath.glob("rtel.*")
                           if f.stat().st_size > 0))

    if not files:
        parser.print_help()
        sys.exit(1)

    all_events = []
    for filepath in files:
        p = Path(filepath)
        if not p.exists():
            print(f"Warning: {filepath} not found, skipping", file=sys.stderr)
            continue
        if p.stat().st_size == 0:
            continue

        print(f"Parsing {p.name} ({p.stat().st_size:,} bytes) ...",
              file=sys.stderr)
        events = extract_events(filepath)
        print(f"  {len(events)} events extracted.", file=sys.stderr)
        all_events.extend(events)

    if not all_events:
        print("No events extracted.", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.jsonl:
        for e in all_events:
            print(json.dumps(e))
    elif args.csv:
        print(events_to_csv(all_events, args.type), end='')
    elif args.json_summary:
        for filepath in files:
            file_events = [e for e in all_events if e.get('file') == filepath]
            if file_events:
                summary = summarize(file_events, filepath)
                print(json.dumps(summary, indent=2))
    else:
        # Human summary — one per file, or combined if batch
        if len(files) == 1:
            summary = summarize(all_events, files[0])
            print(format_human(summary))
        else:
            # Per-file summaries
            for filepath in files:
                file_events = [e for e in all_events
                              if e.get('file') == filepath]
                if file_events:
                    summary = summarize(file_events, filepath)
                    print(format_human(summary))
            # Combined summary
            print("=" * 60)
            print(f"COMBINED: {len(files)} sessions, {len(all_events)} events")
            print("=" * 60)
            combined = summarize(all_events, f"{len(files)} files")
            print(format_human(combined))


if __name__ == "__main__":
    main()
