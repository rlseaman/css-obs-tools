#!/usr/bin/env python3
"""
tcsplot — Plot telescope performance from rteldigest JSONL event streams.

Reads JSONL output from rteldigest.py and produces matplotlib figures
characterizing telescope performance: slew rates, pointing residuals,
settling times, position-dependent behavior, and temporal evolution.

Usage:
    tcsplot.py events.jsonl                     # all standard plots
    tcsplot.py events.jsonl --plot slew_rate     # specific plot
    tcsplot.py events.jsonl --outdir ./plots/    # save to directory
    tcsplot.py events.jsonl --show               # display interactively
    tcsplot.py events.jsonl --list               # list available plots
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('Agg')  # non-interactive by default
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.colors import Normalize
    from matplotlib import cm
except ImportError:
    print("Error: matplotlib is required. Install with: pip install matplotlib",
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_events(filepath):
    """Load JSONL events, parse timestamps."""
    events = []
    with open(filepath) as f:
        for line in f:
            e = json.loads(line)
            events.append(e)
    return events


def get_points(events):
    """Extract completed point events with full data."""
    points = []
    for e in events:
        if e.get('type') == 'point' and 'move_deg' in e and 'elapsed_s' in e:
            p = dict(e)
            # Parse timestamps
            for tfield in ('time_start', 'time_end'):
                if tfield in p and isinstance(p[tfield], str):
                    try:
                        p[tfield + '_dt'] = datetime.fromisoformat(
                            p[tfield].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
            # Session date from filename
            if 'file' in p:
                import re
                m = re.search(r'rtel\.(\d{4}-\d{2}-\d{2})', p['file'])
                if m:
                    p['session_date'] = m.group(1)
            points.append(p)
    return points


def get_where_responses(events):
    """Extract where responses with position data."""
    return [e for e in events if e.get('type') == 'where_response'
            and 'alt' in e and 'az' in e]


def get_errors(events):
    """Extract error events."""
    return [e for e in events if e.get('type') == 'error']


def get_encoder_readings(events):
    """Extract encoder readings with position data."""
    return [e for e in events if e.get('type') == 'encoder'
            and 'ha' in e and 'dec' in e]


# ---------------------------------------------------------------------------
# Plot functions
# ---------------------------------------------------------------------------

def apply_limits(ax, xlim=None, ylim=None):
    """Apply optional axis limits."""
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)


def plot_slew_rate(points, outdir, show=False, xlim=None, ylim=None):
    """Slew rate vs distance, color-coded by session date."""
    if not points:
        return

    moves = [p['move_deg'] for p in points]
    rates = [p.get('slew_rate_deg_s', 0) for p in points]

    # Color by session date
    dates = sorted(set(p.get('session_date', '') for p in points))
    date_idx = {d: i for i, d in enumerate(dates)}
    colors = [date_idx.get(p.get('session_date', ''), 0) for p in points]

    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(moves, rates, c=colors, cmap='viridis', alpha=0.6, s=15,
                    vmin=0, vmax=max(1, len(dates)-1))
    ax.set_xlabel('Slew Distance (degrees)')
    ax.set_ylabel('Effective Slew Rate (deg/s)')
    ax.set_title('KP 2.1m Slew Rate vs Distance')
    ax.set_xlim(0, None)
    ax.set_ylim(0, None)
    ax.grid(True, alpha=0.3)

    if len(dates) > 1:
        cbar = plt.colorbar(sc, ax=ax)
        # Label colorbar with date range
        cbar.set_label(f'Session ({dates[0]} to {dates[-1]})')

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'slew_rate_vs_distance.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  slew_rate_vs_distance.png ({len(points)} points)")


def plot_settling_time(points, outdir, show=False, xlim=None, ylim=None):
    """Settling time vs slew distance — the overhead budget."""
    if not points:
        return

    moves = [p['move_deg'] for p in points]
    elapsed = [p['elapsed_s'] for p in points]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(moves, elapsed, alpha=0.5, s=12, c='steelblue')
    ax.set_xlabel('Slew Distance (degrees)')
    ax.set_ylabel('Total Time (seconds)')
    ax.set_title('KP 2.1m Slew + Settle Time vs Distance')
    ax.set_xlim(0, None)
    ax.set_ylim(0, None)
    ax.grid(True, alpha=0.3)

    # Add a reference line for constant-rate slewing
    import numpy as np
    x = np.linspace(0.1, max(moves), 100)
    ax.plot(x, x / 0.55 + 8, '--', color='gray', alpha=0.5,
            label='0.55 deg/s + 8s overhead')
    ax.legend()

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'settling_time.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  settling_time.png ({len(points)} points)")


def plot_pointing_residual(points, outdir, show=False, xlim=None, ylim=None):
    """Pointing residual histogram."""
    if not points:
        return

    residuals = [p['residual_deg'] * 3600 for p in points
                 if 'residual_deg' in p and p['residual_deg'] < 0.1]
    if not residuals:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(residuals, bins=50, color='steelblue', edgecolor='white', alpha=0.8)
    ax.axvline(x=sum(residuals)/len(residuals), color='red', linestyle='--',
               label=f'Mean: {sum(residuals)/len(residuals):.1f}"')
    median = sorted(residuals)[len(residuals)//2]
    ax.axvline(x=median, color='orange', linestyle='--',
               label=f'Median: {median:.1f}"')
    ax.set_xlabel('Pointing Residual (arcseconds)')
    ax.set_ylabel('Count')
    ax.set_title('KP 2.1m Pointing Residual Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'pointing_residual.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  pointing_residual.png ({len(residuals)} points)")


def plot_convergence_passes(points, outdir, show=False, xlim=None, ylim=None):
    """Multi-pass convergence: passes required vs slew distance."""
    if not points:
        return

    moves = [p['move_deg'] for p in points if 'passes' in p]
    passes = [p['passes'] for p in points if 'passes' in p]
    if not moves:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    # Jitter passes slightly for visibility
    import numpy as np
    jitter = np.random.normal(0, 0.05, len(passes))
    colors = ['steelblue' if p == 1 else 'orange' if p == 2 else 'red'
              for p in passes]
    ax.scatter(moves, [p + j for p, j in zip(passes, jitter)],
               alpha=0.5, s=12, c=colors)
    ax.set_xlabel('Slew Distance (degrees)')
    ax.set_ylabel('Convergence Passes')
    ax.set_title('KP 2.1m Pointing Convergence Passes')
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_xlim(0, None)
    ax.grid(True, alpha=0.3)

    n_single = sum(1 for p in passes if p == 1)
    n_multi = sum(1 for p in passes if p > 1)
    ax.text(0.98, 0.95, f'Single-pass: {n_single} ({100*n_single/len(passes):.0f}%)\n'
            f'Multi-pass: {n_multi} ({100*n_multi/len(passes):.0f}%)',
            transform=ax.transAxes, ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'convergence_passes.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  convergence_passes.png ({len(moves)} points)")


def plot_error_timeline(events, outdir, show=False, xlim=None, ylim=None):
    """Error events over time."""
    errors = get_errors(events)
    if not errors:
        return

    times = []
    labels = []
    for e in errors:
        t = e.get('time')
        if t:
            try:
                times.append(datetime.fromisoformat(t.replace('Z', '+00:00')))
                msg = e.get('message', '')[:60]
                labels.append(msg)
            except (ValueError, TypeError):
                pass

    if not times:
        return

    # Categorize errors
    categories = defaultdict(list)
    for t, label in zip(times, labels):
        if 'dropout' in label.lower():
            categories['dropout'].append(t)
        elif 'runaway' in label.lower():
            categories['runaway'].append(t)
        elif 'homed' in label.lower():
            categories['not homed'].append(t)
        elif 'dist=' in label:
            categories['pointing'].append(t)
        elif 'encoder' in label.lower() or 'curl' in label.lower():
            categories['encoder'].append(t)
        else:
            categories['other'].append(t)

    fig, ax = plt.subplots(figsize=(12, 5))
    colors_map = {
        'dropout': 'orange', 'runaway': 'red', 'not homed': 'purple',
        'pointing': 'blue', 'encoder': 'green', 'other': 'gray'
    }
    for i, (cat, cat_times) in enumerate(sorted(categories.items())):
        ax.scatter(cat_times, [i] * len(cat_times), alpha=0.6, s=20,
                   c=colors_map.get(cat, 'gray'), label=f'{cat} ({len(cat_times)})')
    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(sorted(categories.keys()))
    ax.set_xlabel('Date')
    ax.set_title(f'KP 2.1m Error Timeline ({len(errors)} events)')
    ax.legend(loc='upper right', fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'error_timeline.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  error_timeline.png ({len(errors)} events)")


def plot_session_throughput(points, outdir, show=False, xlim=None, ylim=None):
    """Slews per session and targets per session over time."""
    if not points:
        return

    sessions = defaultdict(list)
    for p in points:
        sd = p.get('session_date', 'unknown')
        sessions[sd].append(p)

    dates = sorted(d for d in sessions.keys() if d != 'unknown')
    if not dates:
        return

    slew_counts = [len(sessions[d]) for d in dates]
    dt_dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(dt_dates, slew_counts, width=1.5, color='steelblue', alpha=0.8)
    ax.set_xlabel('Session Date')
    ax.set_ylabel('Slews')
    ax.set_title('KP 2.1m Slews per Session')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3, axis='y')

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'session_throughput.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  session_throughput.png ({len(dates)} sessions)")


def sex_to_deg(s):
    """Convert sexagesimal string (DD:MM:SS or HH:MM:SS) to degrees."""
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        return None
    try:
        return float(s)
    except ValueError:
        pass
    try:
        s = s.strip()
        sign = -1 if s.startswith('-') else 1
        s = s.lstrip('+-')
        parts = s.split(':')
        if len(parts) == 3:
            return sign * (float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600)
        elif len(parts) == 2:
            return sign * (float(parts[0]) + float(parts[1])/60)
        return None
    except (ValueError, IndexError):
        return None


def plot_position_residuals(points, where_responses, outdir, show=False, xlim=None, ylim=None):
    """Pointing residual as a function of position (HA/Dec or Alt/Az)."""
    pts_with_pos = []
    for p in points:
        if 'residual_deg' not in p:
            continue
        dec_val = None
        ha_val = None
        if 'ha' in p and p['ha'] is not None:
            ha_val = sex_to_deg(p['ha'])
        if 'dec' in p and p['dec'] is not None:
            dec_val = sex_to_deg(p['dec'])
        if dec_val is not None:
            entry = {'dec': dec_val, 'residual': p['residual_deg'] * 3600}
            if ha_val is not None:
                entry['ha'] = ha_val
            pts_with_pos.append(entry)

    if len(pts_with_pos) < 5:
        return

    # Plot residual vs Dec (most commonly available)
    decs = [p['dec'] for p in pts_with_pos if 'dec' in p]
    resids = [p['residual'] for p in pts_with_pos if 'dec' in p]

    if not decs:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(decs, resids, alpha=0.4, s=12, c='steelblue')
    ax.set_xlabel('Declination (degrees)')
    ax.set_ylabel('Pointing Residual (arcseconds)')
    ax.set_title('KP 2.1m Pointing Residual vs Declination')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, min(40, max(resids) * 1.1))

    apply_limits(ax, xlim, ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'residual_vs_dec.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  residual_vs_dec.png ({len(decs)} points)")


def plot_encoder_positions(encoder_events, outdir, show=False, xlim=None, ylim=None):
    """Encoder HA/Dec position over time — shows tracking behavior."""
    if len(encoder_events) < 10:
        return

    times = []
    has = []
    decs = []
    for e in encoder_events:
        t = e.get('time')
        if t and 'ha' in e and 'dec' in e:
            try:
                times.append(datetime.fromisoformat(t.replace('Z', '+00:00')))
                has.append(e['ha'])
                decs.append(e['dec'])
            except (ValueError, TypeError):
                pass

    if len(times) < 10:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(times, has, '.', markersize=2, alpha=0.5, color='steelblue')
    ax1.set_ylabel('HA (degrees)')
    ax1.set_title('KP 2.1m Encoder Positions Over Time')
    ax1.grid(True, alpha=0.3)

    ax2.plot(times, decs, '.', markersize=2, alpha=0.5, color='coral')
    ax2.set_ylabel('Dec (degrees)')
    ax2.set_xlabel('Time (UT)')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    fig.autofmt_xdate()
    ax2.grid(True, alpha=0.3)

    if xlim:
        ax1.set_xlim(xlim)
        ax2.set_xlim(xlim)
    if ylim:
        ax1.set_ylim(ylim)
        ax2.set_ylim(ylim)
    fig.tight_layout()
    fig.savefig(outdir / 'encoder_positions.png', dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"  encoder_positions.png ({len(times)} readings)")


# ---------------------------------------------------------------------------
# Plot registry
# ---------------------------------------------------------------------------

PLOTS = {
    'slew_rate': ('Slew rate vs distance', plot_slew_rate, 'points'),
    'settling': ('Settling time vs distance', plot_settling_time, 'points'),
    'residual': ('Pointing residual distribution', plot_pointing_residual, 'points'),
    'convergence': ('Convergence passes vs distance', plot_convergence_passes, 'points'),
    'errors': ('Error timeline', plot_error_timeline, 'events'),
    'throughput': ('Session throughput', plot_session_throughput, 'points'),
    'position_residual': ('Residual vs position', plot_position_residuals, 'points+where'),
    'encoder': ('Encoder positions over time', plot_encoder_positions, 'encoder'),
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Plot telescope performance from rteldigest JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("jsonl_file", nargs='?', help="JSONL event file")
    parser.add_argument("--plot", help="Specific plot name (see --list)")
    parser.add_argument("--outdir", default="./plots",
                        help="Output directory (default: ./plots)")
    parser.add_argument("--show", action="store_true",
                        help="Display plots interactively (matplotlib toolbar: zoom, pan, save)")
    parser.add_argument("--xlim", help="X axis range as min,max (e.g. --xlim 0,10)")
    parser.add_argument("--ylim", help="Y axis range as min,max (e.g. --ylim 0,15)")
    parser.add_argument("--list", action="store_true",
                        help="List available plots")

    args = parser.parse_args()

    if args.list:
        print("Available plots:")
        for name, (desc, _, data) in sorted(PLOTS.items()):
            print(f"  {name:22s}  {desc}")
        return

    if not args.jsonl_file:
        parser.print_help()
        return

    # Parse axis limits
    def parse_lim(s):
        if not s:
            return None
        parts = s.split(',')
        if len(parts) != 2:
            print(f"Error: limits must be min,max (got '{s}')", file=sys.stderr)
            sys.exit(1)
        return (float(parts[0]), float(parts[1]))

    xlim = parse_lim(args.xlim)
    ylim = parse_lim(args.ylim)

    if args.show:
        matplotlib.use('TkAgg')

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.jsonl_file} ...", file=sys.stderr)
    events = load_events(args.jsonl_file)
    print(f"  {len(events)} events loaded.", file=sys.stderr)

    points = get_points(events)
    where_responses = get_where_responses(events)
    encoder_events = get_encoder_readings(events)
    print(f"  {len(points)} point events, {len(where_responses)} where responses, "
          f"{len(encoder_events)} encoder readings.", file=sys.stderr)

    plots_to_run = [args.plot] if args.plot else list(PLOTS.keys())

    print(f"\nGenerating plots in {outdir}/:")
    for name in plots_to_run:
        if name not in PLOTS:
            print(f"  Unknown plot: {name} (use --list)")
            continue
        desc, func, data_type = PLOTS[name]
        try:
            if data_type == 'points':
                func(points, outdir, show=args.show, xlim=xlim, ylim=ylim)
            elif data_type == 'events':
                func(events, outdir, show=args.show, xlim=xlim, ylim=ylim)
            elif data_type == 'points+where':
                func(points, where_responses, outdir, show=args.show, xlim=xlim, ylim=ylim)
            elif data_type == 'encoder':
                func(encoder_events, outdir, show=args.show, xlim=xlim, ylim=ylim)
        except Exception as e:
            print(f"  {name}: ERROR — {e}", file=sys.stderr)

    print(f"\nDone. Plots saved to {outdir}/")


if __name__ == "__main__":
    main()
