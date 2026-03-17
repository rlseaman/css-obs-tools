# KP 2.1m Slew and Pointing Performance — June 2023

Date: 2026-03-16
Source: rtel server logs from `/archive2/scratch/Sells/tcs/Data/`
Tool: `rteldigest.py` + custom matplotlib analysis

## Dataset

Three productive observing nights from June 2023 — the last month
with multiple full sessions before the telescope entered its decline
phase (Aug 2023: last runaways; Oct 2023: last consistent observing;
Apr 2024: runaway incident; then idle).

| Date | Slews | Notes |
|------|-------|-------|
| 2023-06-09 | 124 | Moderate session |
| 2023-06-20 | 291 | Heavy session |
| 2023-06-25 | 250 | Heavy session |
| **Total** | **665** | |

These sessions are representative of the telescope performing routine
observing under the previous team's operational procedures, with the
pointing model `180606.model` (June 2018) and the code version
corresponding to spare43 + 2 patches (track.C sign fix, rshutter.C
path fix).

## Slew + settle time vs. distance (0–90°)

![Settling time, 0-90 degrees](jun2023_settling_0_90deg.png)

**Key observations:**

- The relationship between slew distance and total time is well-fit
  by a linear model: **T ≈ D / 0.55 + 8 seconds**, where D is the
  move distance in degrees. The 0.55 deg/s represents the effective
  slew velocity (including acceleration and deceleration), and the
  ~8s fixed overhead represents settling and convergence time.

- Performance is consistent across all three nights — the three
  colors interleave without systematic separation, indicating
  night-to-night reproducibility.

- Most points lie near or below the reference line. Points above it
  typically involve dome moves (the dome must also slew to track the
  telescope, adding time when the dome move is the longer leg) or
  multi-pass convergence (the pointing loop needs 2-3 iterations to
  reach the target).

- **Throughput implication:** A typical CSS follow-up dither of ~1°
  takes ~10s. A large slew of 60° takes ~120s. For a night with
  50 targets at 30° average separation and 4 dithers each, the slew
  budget is roughly 50 × (65s + 4 × 10s) ≈ 87 minutes — about 18%
  of a 8-hour night.

## Small slew overhead (0–2°)

![Settling time, 0-2 degrees](jun2023_settling_0_2deg.png)

**Key observations:**

- Small slews (< 2°) show a quantized time structure due to the 1s
  timestamp resolution in the rtel logs. The minimum time for any
  move is effectively **3-5 seconds** for very small offsets (<0.1°).

- Moves of 0.5–1.2° consistently take **10-13 seconds**. This is the
  typical dither offset cadence — the time between exposures in a
  4-position dither pattern.

- The June 25 night (green) shows slightly faster small-slew
  performance than June 20 (red), possibly reflecting different
  target densities or sky positions.

- **CSS relevance:** The dither cadence of 10-13s per position means
  a 4-exposure dither set takes ~50s of slew time plus 4 × 5-10s
  exposure time = ~90-100s total per target visit. This matches
  the ~60s per NEXTPOS cycle observed in the CSS V06 control logs.

## Pointing residual distribution

![Pointing residual histogram](jun2023_pointing_residual.png)

**Key observations:**

- The distribution is **bimodal**: a tight primary peak at **1-4
  arcseconds** (most slews) and a secondary population extending
  from 10" to 30"+.

- Combined median: **3.6"**, mean: **6.5"**. The median is the
  operationally relevant number — most slews achieve good pointing.

- The three nights show different tail characteristics:
  - Jun 9 (blue): a distinct cluster at 26-28" — possibly a
    systematic offset at specific sky positions
  - Jun 20 (red): a broader tail extending to 30" with a bump
    at 14-16" — the busiest night, more diverse sky coverage
  - Jun 25 (green): tightest distribution, fewest outliers

- **The bimodal structure suggests a correctable systematic:**
  The secondary peak at ~27" is suspiciously close to the HA
  backlash (170" between gear tooth faces = 2.8 arcmin). If the
  approach direction relative to the worm gear backlash is not
  consistently controlled by the overshoot parameter in point.C,
  some fraction of slews will land on the wrong side of the
  backlash gap.

- **CSS relevance:** For astrometric follow-up, 4" median blind
  pointing is excellent — well within the field of view of any
  reasonable camera. The tail population (>10") would require the
  target to be within the field but offset from center, which the
  CSS pipeline handles via plate solving. A refreshed pointing
  model would likely reduce the tail significantly.

## Implications for CSS operations at KP 2.1m

1. **The telescope can sustain 250-290 slews per night** on
   productive sessions (Jun 20 and 25). This is adequate for the
   50-100 target follow-up mode anticipated for CSS.

2. **Slew overhead is predictable:** T ≈ D/0.55 + 8s. This enables
   accurate scheduling and observing plan optimization.

3. **Dither cadence is ~10-13s** for the 0.5-1.2° offsets typical
   of a 4-position pattern. Combined with 5-10s exposures, a
   complete dither set takes ~90-100s.

4. **Blind pointing of 3.6" median** is adequate for CSS cameras
   (typical field >5 arcmin). The bimodal residual distribution
   warrants investigation — a new pointing model and verification
   of the overshoot parameter may eliminate the 27" secondary peak.

5. **Night-to-night consistency is good.** The three June 2023
   sessions show reproducible performance, suggesting the drive
   system is mechanically stable when properly maintained.
