# KP 2.1m Nighttime Observing Sessions — Validated Inventory

Date: 2026-03-17
Source: rtel server logs from `/archive2/scratch/Sells/tcs/Data/`
Tool: `rteldigest.py` + custom analysis

## Context

The KP 2.1m rtel archive contains 452 log files spanning 2020–2025.
During this entire period, the Sells team was commissioning the SEDM
and SEDM_v2 instruments. The slew patterns, target counts, and
observing cadence reflect that instrument program, not CSS survey
operations.

## Session selection

To identify genuine nighttime observing sessions (as distinct from
daytime engineering, dome-closed testing, or brief checkouts), the
following filters were applied:

- `span_hours > 4` — at least 4 hours of telescope activity
- `real_slews > 20` — at least 20 real slews (pass > 0)
- `n_dome_azimuths > 15` — dome tracked to at least 15 distinct
  azimuth positions (evidence the dome was open and following the
  telescope across the sky)
- UT time window 01:00–13:00 — local ~6pm–6am at Kitt Peak

Note: nighttime engineering sessions (pointing model runs, etc.)
may still be included; this filter identifies dome-open nighttime
activity, not necessarily science observing.

Note: the `nodome` flag in a point command does not necessarily
indicate the dome is closed. It may mean the calling software
determined the telescope was already within the dome slit boundaries,
so no dome rotation was needed. This is normal for small dithers.

## Result: 40 validated nighttime sessions

2,028 point events across 40 UT dates from 2021–2025.

```
Date         Slews DmAz  Span Multi%  Med"  Mean"  <5" >20"  <.1 .1-1 1-10  >10 MdRate MdElp      UT range
----------------------------------------------------------------------------------------------------------------------
2021-01-28      22   22 12.5h   9.1%   4.3   6.4   15    3    6    0    1   21  0.578   72s   01:14-13:46
2021-06-10      28   16  9.6h  10.7%   3.2   4.0   35    0   24    0    3   24  0.535   12s   01:58-11:35
2021-06-16      29   16  9.7h  10.3%   4.1   6.0   32    3   23    0    0   29  0.504   34s   02:01-11:40
2021-06-18      21   21  9.6h  14.3%   3.2   6.1   20    2   12    0    0   21  0.530   56s   02:01-11:35
2021-06-20      21   21  9.6h   4.8%   3.1   4.2   29    1   15    0    4   17  0.511   28s   02:02-11:35
2021-07-09      22   20  9.7h   9.1%   4.3   9.0   19    9   12    0    4   18  0.518   35s   02:01-11:43
2021-08-23      22   21 10.9h   9.1%   5.0   4.7   16    0   36    0    2   20  0.509    0s   01:23-12:16
2022-12-22      62   31 11.6h  24.2%   4.3   8.7   50   14   40    0    9   36  0.338   23s   01:32-13:07
2023-03-18      27   22 11.5h   7.4%   4.9   8.4   16    4    8    0    2   22  0.556   60s   01:08-12:35
2023-03-25      35   19 11.4h   0.0%   4.3   7.4   27    4   24    1    1   24  0.537   25s   01:19-12:45
2023-04-06      32   22 11.3h   0.0%   4.0   6.0   29    2   23    2    1   21  0.485   11s   01:08-12:29
2023-04-07      32   22 10.4h   6.2%   4.1   8.0   21    4    8    8    9   11  0.165   14s   01:23-11:47
2023-04-15      30   28 11.0h  13.3%   4.7   8.7   17    5    2    3    3   24  0.577   70s   01:16-12:18
2023-04-16      32   24 10.6h  15.6%   3.6   3.9   22    0    3    2    4   26  0.541   71s   01:15-11:48
2023-04-17      81   28 11.0h   3.7%   4.7   8.0   45   10    3   23    8   50  0.462   50s   01:13-12:15
2023-04-18      37   20  7.5h   8.1%   4.3   5.7   24    1    3    3    2   32  0.614   80s   01:13-08:46
2023-04-19      62   20 10.9h  12.9%   4.0   6.3   37    2    2   10   11   41  0.499   49s   01:17-12:13
2023-04-21      37   20 10.9h   8.1%   4.9   7.2   20    4    3    4    1   32  0.564   72s   01:19-12:10
2023-05-06      41   23  6.3h  12.2%   5.4   9.1   22    7    6    0    4   37  0.567   54s   01:29-07:51
2023-05-21      25   20  8.7h  28.0%   3.6   7.1   18    3    5    0    4   21  0.542   68s   03:19-11:59
2023-05-23      31   21  9.9h  19.4%   5.0   7.7   16    3    4    0    4   27  0.540   80s   02:01-11:58
2023-05-25      23   28 10.3h  13.0%   4.0   6.5   15    2    4    2    3   17  0.483   41s   01:42-12:00
2023-05-26      45   20  4.8h  13.3%   3.2   6.4   36    6    6    9    3   31  0.374   35s   01:42-06:27
2023-05-27      23   22  9.9h   8.7%   4.3   6.0   14    3    3    1    3   19  0.494   43s   01:41-11:38
2023-05-31      25   24  7.5h  12.0%   4.0   7.9   19    4    7    2    5   18  0.540   40s   01:52-09:21
2023-06-01      23   22  9.8h  21.7%   4.3   8.1   15    4    4    2    3   18  0.537   47s   01:47-11:36
2023-06-07      25   16  9.8h   0.0%   5.6  11.0   13    8    7    5    6   14  0.279   19s   01:47-11:35
2023-06-12      22   29  9.8h   9.1%   3.6   5.5   19    1   11    2    3   11  0.226   20s   01:50-11:35
2023-06-13      44   27  9.9h   6.8%   3.2   5.6   37    3   20    0   15   18  0.201   16s   01:55-11:48
2023-06-18      29   37  9.7h  10.3%   4.0   7.4   28    3   35    1    2   12  0.026    4s   01:56-11:37
2023-06-19      30   32  5.7h  13.3%   6.5  10.2   24   12   26    2   15   12  0.193   11s   01:52-07:34
2023-06-23      32   26  9.7h   9.4%   3.2   4.4   29    0   10   13    5   14  0.147    8s   02:00-11:43
2023-06-24      32   22  9.7h  15.6%   4.0   6.3   24    3    4   11    4   17  0.309   22s   01:55-11:36
2023-06-25      26   16  5.7h  19.2%   3.4   6.8   17    3    4    5    3   18  0.387   42s   02:16-07:58
2023-06-29      37   20  9.7h  10.8%   6.7   9.7   14    8    5    2    5   30  0.514   46s   01:55-11:38
2023-06-30      38   16  9.7h  18.4%   3.8   6.4   27    3    2    1    4   33  0.499   62s   01:58-11:38
2023-07-01      66   30  9.5h   6.1%   8.3   9.8   28    2    6   32    5   28  0.105    7s   02:07-11:39
2024-04-25      89   39 11.7h   6.7%   3.2   6.4   80   10   31   16   16   57  0.465   29s   01:01-12:43
2024-04-28      99   50 10.9h   9.1%   5.8   9.3   60   16   50   38   10   51  0.253    6s   01:08-12:01
2025-04-05     159   22  7.7h  14.5%   5.0   7.8   85   16   18   30    3  121  0.518   70s   02:48-10:31
----------------------------------------------------------------------------------------------------------------------
COMBINED      1596             11.0%   4.3   7.3 1114  188
```

Column definitions:
- **Slews**: real slews (pass > 0, excluding pass=0 re-points)
- **DmAz**: distinct dome azimuth positions observed
- **Span**: duration from first to last point event (UT)
- **Multi%**: fraction of real slews requiring multiple convergence passes
- **Med"/Mean"**: median and mean pointing residual in arcseconds
- **<5"/>20"**: count of residuals below 5" and above 20"
- **<.1/.1-1/1-10/>10**: slew size bins in degrees (re-points, dithers, nearby, cross-sky)
- **MdRate**: median slew rate in deg/s (computed for slews with move > 1°)
- **MdElp**: median elapsed time in seconds

## Slew + settling time vs. distance

![Settling time vs distance](nighttime40_settling_vs_distance.png)

The T = D/0.55 + 8s reference line fits well across all years. Most
points cluster near or below the line. The 2025 data (purple) is
consistent with the historical envelope — no obvious degradation in
slew performance.

## Pointing residual distribution by slew distance

![Pointing residual by slew distance](nighttime40_residual_by_distance.png)

The residual histogram is color-coded by slew distance to reveal
which slews produce the pointing tail:

- **No slew (pass=0)** events (gray, n=432) have residuals spread
  broadly from 0–30" — these are re-points where the telescope was
  already "at target," so the residual reflects wherever it happened
  to be sitting, not pointing accuracy.

- **Short slews (<5 deg)** (blue, n=442) cluster tightly at 1–4" —
  the best pointing performance, as expected for small corrections.

- **Large slews (>20 deg)** (red, n=907) dominate the tail beyond
  5" and are responsible for nearly all the >20" outliers. The
  bimodal structure (primary peak at 2–3", secondary bump at 15–18"
  and 27–30") is almost entirely a large-slew phenomenon.

- **Medium slews (5–20 deg)** contribute proportionally to both the
  core and the tail.

Combined median: **4.3"**. The tail population is strongly correlated
with slew distance — consistent with the pointing model having larger
errors at certain sky positions reached by long slews, or with
backlash/settling effects that scale with move distance.

## Multi-pass convergence

Overall multi-pass rate across 40 nights: **11.0%** (175/1596).

The multi-pass phenomenon is concentrated in cross-sky slews (>10°).
Dithers (0.1–1°) almost never need multiple passes (~2%). This is
consistent with mechanical causes (backlash, settling) rather than
encoder or servo issues, which would affect all slew sizes equally.

No clear trend in multi-pass rate across years is visible in the
validated nighttime data. The dramatic rates previously reported for
April 2024 (41%) were from daytime engineering sessions, not
nighttime observing.
