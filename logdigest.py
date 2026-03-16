#!/usr/bin/env python3
"""
logdigest — Distill CSS control.tcl logs into structured summaries.

Parses the multiplexed output of CSS nightly control logs (control.YYYYMMDD.*.log)
and produces concise summaries of observing activity, pipeline results, telescope
status, and errors.

Designed to be tolerant of format evolution across 20+ years of CSS operations.
Unknown line types are counted but not fatal. New patterns can be added to
EVENT_PATTERNS without changing parsing logic.

Usage:
    logdigest.py <logfile>                    # human-readable summary
    logdigest.py <logfile> --json             # structured JSON output
    logdigest.py <logfile> --timeline         # chronological event timeline
    logdigest.py <logfile> --filter tcs       # show only TCS-related lines
    logdigest.py <logfile> --verbose          # include unclassified line stats
"""

import re
import sys
import json
import argparse
from collections import Counter, OrderedDict
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Event classification patterns
#
# Each entry: (category, subcategory, compiled_regex)
# Order matters: first match wins. More specific patterns before general ones.
# Patterns are applied to each line; the first match classifies the line.
# ---------------------------------------------------------------------------

EVENT_PATTERNS = []

def _p(category, subcategory, pattern):
    """Register a classification pattern."""
    EVENT_PATTERNS.append((category, subcategory, re.compile(pattern)))

# --- TCS commands and responses ---
_p("tcs", "nextpos",    r"CommandTCS NEXTPOS\s+([\d:.+-]+)\s+([\d:.+-]+)")
_p("tcs", "movnext",    r"proc MoveTelescope sending MOVNEXT")
_p("tcs", "movradec",   r"CommandTCS MOVRADEC")
_p("tcs", "slew_done",  r"ListenToSlew.*telescope has STOPPED")
_p("tcs", "slew_start", r"ListenToSlew.*telescope.*MOVING|SLEWING")
_p("tcs", "track",      r"CommandTCS.*TRACK")
_p("tcs", "dome",       r"DOME PARAM|CommandTCS.*DOME")
_p("tcs", "focus",      r"CommandTCS.*FOCUS")
_p("tcs", "enable",     r"CommandTCS.*ENABLE|CommandTCS.*DISABLE")
_p("tcs", "response",   r"Result back from.*CommandTCS|Returned OK|Return from.*NEXTPOS|Return from.*MOVNEXT")
_p("tcs", "command",    r"CommandTCS\s+")

# --- Exposures and FITS metadata ---
_p("exposure", "mid_time",    r"DATE-MID\s*=\s*'(\d{4}-\d{2}-\d{2}T[\d:.]+)'")
_p("exposure", "duration",    r"EXP_MEAS\s*=\s*([\d.]+)")
_p("exposure", "mjd",         r"MJDMID\s*=")
_p("exposure", "fits_header", r"^[A-Z][A-Z0-9_]{1,7}=\s")
_p("exposure", "object",      r"OBJECT\s*=\s*'([^']+)'")

# --- CCD / detector telemetry ---
_p("telemetry", "ccd_temp",   r"ccdtemp\s*=\s*([\d.]+)")
_p("telemetry", "vacuum",     r"vacuum\s*=\s*([\d.]+)")
_p("telemetry", "backplate",  r"backplatetemp\s*=\s*([\d.]+)")
_p("telemetry", "cryo",       r"cryoreturn|cryosupply")
_p("telemetry", "driver",     r"driver_error\s*=")
_p("telemetry", "xirq",       r"xirq\s*=")
_p("telemetry", "exposure_ms",r"^exposure\s*=\s*\d+")

# --- Calibration ---
_p("calibration", "flat_score",  r"Noise,diff,fringe,median")
_p("calibration", "flat_cache",  r"Cached flat")
_p("calibration", "flat_load",   r"Loading master flat|Loading mask")
_p("calibration", "bias",        r"[Bb]ias\s+frame|master.*bias")
_p("calibration", "dark",        r"[Dd]ark\s+frame|master.*dark")
_p("calibration", "threshold",   r"Caching.*thresh|threshold")
_p("calibration", "hot_pixel",   r"hot pixel")
_p("calibration", "calibrate",   r"^calibrate\s+V[\d.]+")

# --- Pipeline: source extraction, astrometry, photometry ---
_p("pipeline", "sextractor", r"sex\s|sextract|SExtract|source.*extract")
_p("pipeline", "scamp",      r"scamp|scampfield|SCAMP")
_p("pipeline", "starmatch",  r"starmatch|60match")
_p("pipeline", "wcs",        r"imwcs|WCS|wcs.*solution|astrometric")
_p("pipeline", "photometry", r"vphot|vmag|magoffset|photometr")
_p("pipeline", "fwhm",       r"FWHM|fwhm|seeing")
_p("pipeline", "limitmag",   r"limitmag|limiting.*mag")
_p("pipeline", "digest2",    r"digest2")
_p("pipeline", "identify",   r"\bidentify\b")
_p("pipeline", "mtdlink",    r"mtdlink|mtdf2dets|ipmtd")
_p("pipeline", "ephem",      r"\bephem\b")
_p("pipeline", "postpipe",   r"postpipe")
_p("pipeline", "quicklook",  r"quicklook")
_p("pipeline", "ai_classify",r"ai_classify|ai_neural")

# --- Follow-up and queue ---
_p("followup", "flwp",       r"flwp|follow.up|FLWP")
_p("followup", "queue_pri",  r"QBASEPRI|queue.*prior")
_p("followup", "neocp",      r"NEOCP|neocp")
_p("followup", "submission", r"[Ss]ubmission|MPC80|submitted|MPC.*format")

# --- File management ---
_p("fileops", "copy",        r"CopyNetList|rsync|scp ")
_p("fileops", "archive",     r"archive|filexfer|checkpoint")
_p("fileops", "compress",    r"fcompress|hcomp|gzip|fitsbin|float216")
_p("fileops", "sethead",     r"sethead|gethead|delhead|copyheader")

# --- Configuration and startup ---
_p("config", "site_load",    r"Loading site config|site\..*\.json|Site config.*loaded")
_p("config", "proc_load",    r"Loading.*processing config|proc\..*\.json|Processing config.*loaded")
_p("config", "override",     r"Config override")
_p("config", "freecores",    r"freecores")
_p("config", "improcd",      r"improcd")

# --- Weather ---
_p("weather", "conditions",  r"windspeed|humidity|cloud|rain|dew|bar=|oat=|weather")
_p("weather", "seeing",      r"\bseeing\b")

# --- Errors and warnings ---
_p("error", "error",         r"ERROR|[Ee]rror|FATAL|fatal")
_p("error", "warning",       r"WARNING|[Ww]arning|WARN")
_p("error", "timeout",       r"[Tt]imeout|timed out")
_p("error", "failed",        r"[Ff]ailed|failure|FAIL")

# --- Startup and UI ---
_p("startup", "ds9",         r"ds9|SAOBlink|SAOImage")
_p("startup", "camera",      r"CamMode|mont4kserver|camera.*init|[Cc]ommunicat.*telescope")
_p("startup", "geometry",    r"wm geometry|wm state")
_p("startup", "control_tcl", r"control\.tcl:")
_p("startup", "ssh_cmd",     r"/usr/bin/ssh\s|ssh\s+-n")
_p("startup", "cp_cmd",      r"^cp\s+-p\s")
_p("startup", "calibrate_status", r"calibrate\s+(cache|done|preload)")

# --- Pipeline detail (numeric output, tables, etc.) ---
_p("pipeline_detail", "scamp_output",  r"^\s*[-+]?\d+\.\d+\s+[-+]?\d+\.\d+\s")
_p("pipeline_detail", "sex_catalog",   r"^\s*\d+\s+\d+\.\d+\s+\d+\.\d+\s")
_p("pipeline_detail", "numeric_line",  r"^\s*[-+]?\d+\.?\d*\s*$")
_p("pipeline_detail", "matrix",        r"^\s*[-+]?\d+\.\d+[eE][-+]?\d+")
_p("pipeline_detail", "data_table",    r"^\s*\d+\s+\d+\s+\d+")
_p("pipeline_detail", "pipe_path",     r"/data0/.*\.(fits|temp|sext|det|cat|head)")
_p("pipeline_detail", "pipe_status",   r"^\s*(OK|DONE|PASS|SKIP|ABORT|TRUE|FALSE)[,\s]")

# --- Blank and noise ---
_p("noise", "blank",         r"^\s*$")
_p("noise", "separator",     r"^[-=_]{3,}$")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class LogEvent:
    """A classified log line."""
    __slots__ = ("lineno", "category", "subcategory", "line", "match")

    def __init__(self, lineno, category, subcategory, line, match=None):
        self.lineno = lineno
        self.category = category
        self.subcategory = subcategory
        self.line = line
        self.match = match


def classify_line(line):
    """Return (category, subcategory, match) for a log line."""
    stripped = line.strip()
    if not stripped:
        return ("noise", "blank", None)
    for category, subcategory, regex in EVENT_PATTERNS:
        m = regex.search(stripped)
        if m:
            return (category, subcategory, m)
    return ("unclassified", "unknown", None)


def parse_log(filepath):
    """Parse a control log file into classified events."""
    events = []
    with open(filepath, "r", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            cat, subcat, match = classify_line(line)
            events.append(LogEvent(lineno, cat, subcat, line.rstrip(), match))
    return events


# ---------------------------------------------------------------------------
# Extractors — pull structured data from classified events
# ---------------------------------------------------------------------------

def extract_targets(events):
    """Extract unique target positions and designations."""
    targets = []
    for ev in events:
        if ev.category == "tcs" and ev.subcategory == "nextpos" and ev.match:
            ra, dec = ev.match.group(1), ev.match.group(2)
            targets.append((ra, dec, ev.lineno))
    return targets


def extract_designations(events):
    """Extract object designations from FITS filenames in the log.

    CSS filenames follow: SITE_DATE_CONFIG_DESIG_NN_NNNN pattern.
    The designation field is the 4th underscore-delimited component,
    after site code, date, and camera config. Tolerant of varying
    site codes (703, G96, I52, V06, V00, KP21M, etc.) and configs
    (1A, 2B, 4A, 1C, 2C, 2A, etc.).
    """
    # Match: SITE_YYYYMMDD_CONFIG_DESIGNATION_NN_NNNN
    desig_re = re.compile(
        r'(?:^|/)(?:[A-Z0-9]{2,5})_(\d{8})_([A-Za-z0-9]+)_([A-Za-z0-9]+)_(\d+)_(\d+)'
    )
    designations = Counter()
    for ev in events:
        m = desig_re.search(ev.line)
        if m:
            designations[m.group(3)] += 1
    return designations


def extract_exposures(events):
    """Extract exposure timestamps and durations."""
    exposures = []
    current = {}
    for ev in events:
        if ev.category == "exposure":
            if ev.subcategory == "mid_time" and ev.match:
                current["time"] = ev.match.group(1)
            elif ev.subcategory == "duration" and ev.match:
                current["duration"] = float(ev.match.group(1))
                if "time" in current:
                    exposures.append(dict(current))
                current = {}
    return exposures


def extract_telemetry(events):
    """Extract CCD temperature readings."""
    temps = []
    for ev in events:
        if ev.subcategory == "ccd_temp" and ev.match:
            try:
                temps.append(float(ev.match.group(1)))
            except (ValueError, IndexError):
                pass
    return temps


def extract_errors(events):
    """Extract error and warning messages."""
    errors = []
    for ev in events:
        if ev.category == "error":
            errors.append({
                "line": ev.lineno,
                "type": ev.subcategory,
                "text": ev.line.strip()[:200]
            })
    return errors


def extract_night_window(events):
    """Try to determine the UT time range of the night from exposure timestamps."""
    times = []
    date_re = re.compile(r"(\d{4}-\d{2}-\d{2}T[\d:.]+)")
    for ev in events:
        if ev.subcategory == "mid_time" and ev.match:
            try:
                t = datetime.strptime(ev.match.group(1)[:19], "%Y-%m-%dT%H:%M:%S")
                times.append(t)
            except ValueError:
                pass
    if times:
        return min(times), max(times)
    return None, None


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

def summarize(events, filepath):
    """Produce a structured summary of the night."""
    summary = OrderedDict()

    # Metadata
    summary["file"] = str(filepath)
    summary["total_lines"] = len(events)

    # Infer site and date from filename
    fname = Path(filepath).name
    m = re.search(r"control\.(\d{8})\.\d+\.log", fname)
    if m:
        summary["date"] = m.group(1)
    # Try to get site from path or filename
    site_m = re.search(r"/([A-Z]\d{2}|[A-Z]\d{2}[A-Z]?)/", str(filepath))
    if site_m:
        summary["site"] = site_m.group(1)

    # Category counts
    cat_counts = Counter()
    subcat_counts = Counter()
    for ev in events:
        cat_counts[ev.category] += 1
        subcat_counts[f"{ev.category}.{ev.subcategory}"] += 1
    summary["line_classification"] = dict(cat_counts.most_common())

    # Night window
    t_start, t_end = extract_night_window(events)
    if t_start and t_end:
        summary["night_start_ut"] = t_start.strftime("%H:%M:%S")
        summary["night_end_ut"] = t_end.strftime("%H:%M:%S")
        duration = (t_end - t_start).total_seconds() / 3600
        summary["night_duration_hours"] = round(duration, 2)

    # Targets
    targets = extract_targets(events)
    summary["total_slews"] = len(targets)
    ra_groups = Counter()
    for ra, dec, _ in targets:
        ra_groups[ra[:8]] += 1
    summary["unique_pointings"] = len(set((ra, dec) for ra, dec, _ in targets))
    summary["unique_fields"] = len(ra_groups)

    # Designations
    designations = extract_designations(events)
    summary["targets_observed"] = len(designations)
    summary["target_list"] = dict(designations.most_common())

    # Exposures
    exposures = extract_exposures(events)
    summary["total_exposures"] = len(exposures)
    if exposures:
        durations = [e["duration"] for e in exposures]
        summary["exposure_range_sec"] = [round(min(durations), 1), round(max(durations), 1)]
        dur_counts = Counter(round(d, 0) for d in durations)
        summary["exposure_time_distribution"] = {f"{int(k)}s": v for k, v in sorted(dur_counts.items())}

    # Telemetry
    temps = extract_telemetry(events)
    if temps:
        # CCD temps are often in raw ADU or 0.1°C units
        summary["ccd_temp_readings"] = len(temps)
        summary["ccd_temp_range"] = [min(temps), max(temps)]

    # Errors
    errors = extract_errors(events)
    summary["error_count"] = len(errors)
    if errors:
        summary["errors"] = errors[:20]  # cap at 20

    # Follow-up and submissions
    summary["followup_events"] = subcat_counts.get("followup.flwp", 0)
    summary["mpc_submissions"] = subcat_counts.get("followup.submission", 0)

    # Pipeline activity
    pipeline_total = cat_counts.get("pipeline", 0)
    summary["pipeline_events"] = pipeline_total

    return summary


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_human(summary):
    """Format summary as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("CSS Control Log Summary")
    lines.append("=" * 70)

    if "site" in summary:
        lines.append(f"  Site:       {summary['site']}")
    if "date" in summary:
        d = summary["date"]
        lines.append(f"  Date:       {d[:4]}-{d[4:6]}-{d[6:]}")
    if "night_start_ut" in summary:
        lines.append(f"  UT window:  {summary['night_start_ut']} — {summary['night_end_ut']}  ({summary.get('night_duration_hours', '?')} hrs)")
    lines.append(f"  Log lines:  {summary['total_lines']:,}")
    lines.append("")

    lines.append("Observing Activity")
    lines.append("-" * 40)
    lines.append(f"  Targets observed:   {summary.get('targets_observed', 0)}")
    lines.append(f"  Total slews:        {summary.get('total_slews', 0)}")
    lines.append(f"  Unique pointings:   {summary.get('unique_pointings', 0)}")
    lines.append(f"  Total exposures:    {summary.get('total_exposures', 0)}")
    if "exposure_range_sec" in summary:
        lo, hi = summary["exposure_range_sec"]
        lines.append(f"  Exposure range:     {lo}s — {hi}s")
    if "exposure_time_distribution" in summary:
        dist = summary["exposure_time_distribution"]
        lines.append(f"  Exp time dist:      {dist}")
    lines.append(f"  Follow-up events:   {summary.get('followup_events', 0)}")
    lines.append(f"  MPC submissions:    {summary.get('mpc_submissions', 0)}")
    lines.append("")

    targets = summary.get("target_list", {})
    if targets:
        lines.append("Targets (designation: log mentions)")
        lines.append("-" * 40)
        for name, count in sorted(targets.items(), key=lambda x: -x[1]):
            lines.append(f"  {name:12s}  {count:5d}")
        lines.append("")

    if summary.get("ccd_temp_readings"):
        lines.append("Detector")
        lines.append("-" * 40)
        lo, hi = summary["ccd_temp_range"]
        lines.append(f"  CCD temp range:  {lo} — {hi}  ({summary['ccd_temp_readings']} readings)")
        lines.append("")

    lines.append("Pipeline")
    lines.append("-" * 40)
    lines.append(f"  Pipeline events:  {summary.get('pipeline_events', 0)}")
    lines.append("")

    err_count = summary.get("error_count", 0)
    if err_count:
        lines.append(f"Errors ({err_count})")
        lines.append("-" * 40)
        for err in summary.get("errors", []):
            lines.append(f"  L{err['line']:>7d} [{err['type']}] {err['text'][:80]}")
        lines.append("")

    lines.append("Line Classification")
    lines.append("-" * 40)
    for cat, count in sorted(summary.get("line_classification", {}).items(), key=lambda x: -x[1]):
        pct = 100 * count / summary["total_lines"]
        bar = "#" * max(1, int(pct / 2))
        lines.append(f"  {cat:16s}  {count:7,d}  ({pct:5.1f}%)  {bar}")
    lines.append("")

    return "\n".join(lines)


def format_timeline(events):
    """Format a chronological timeline of high-level events."""
    lines = []
    lines.append(f"{'Line':>8s}  {'Category':12s}  {'Event':12s}  Details")
    lines.append("-" * 70)

    interesting = {"tcs", "exposure", "followup", "error", "weather"}
    skip_sub = {"fits_header", "response"}

    for ev in events:
        if ev.category in interesting and ev.subcategory not in skip_sub:
            detail = ev.line.strip()[:80]
            lines.append(f"{ev.lineno:8d}  {ev.category:12s}  {ev.subcategory:12s}  {detail}")

    return "\n".join(lines)


def format_filtered(events, filter_cat):
    """Show all lines matching a category prefix."""
    lines = []
    for ev in events:
        if ev.category.startswith(filter_cat) or ev.subcategory.startswith(filter_cat):
            lines.append(f"{ev.lineno:8d}  [{ev.category}.{ev.subcategory}]  {ev.line.rstrip()[:120]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Distill CSS control.tcl logs into structured summaries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("logfile", help="Path to control.YYYYMMDD.N.log file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--timeline", action="store_true", help="Chronological event timeline")
    parser.add_argument("--filter", metavar="CAT", help="Show lines matching category (e.g. tcs, error, pipeline)")
    parser.add_argument("--verbose", action="store_true", help="Include unclassified line samples")
    parser.add_argument("--stats", action="store_true", help="Show detailed subcategory counts")

    args = parser.parse_args()
    filepath = Path(args.logfile)

    if not filepath.exists():
        print(f"Error: {filepath} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing {filepath} ...", file=sys.stderr)
    events = parse_log(filepath)
    print(f"Classified {len(events):,} lines.", file=sys.stderr)

    if args.filter:
        print(format_filtered(events, args.filter))
        return

    if args.timeline:
        print(format_timeline(events))
        return

    summary = summarize(events, filepath)

    if args.verbose:
        # Sample unclassified lines
        unclassified = [ev for ev in events if ev.category == "unclassified"]
        if unclassified:
            samples = unclassified[:10]
            summary["unclassified_samples"] = [
                {"line": ev.lineno, "text": ev.line.strip()[:120]}
                for ev in samples
            ]
            summary["unclassified_total"] = len(unclassified)

    if args.stats:
        subcat_counts = Counter()
        for ev in events:
            subcat_counts[f"{ev.category}.{ev.subcategory}"] += 1
        summary["subcategory_counts"] = dict(subcat_counts.most_common())

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_human(summary))


if __name__ == "__main__":
    main()
