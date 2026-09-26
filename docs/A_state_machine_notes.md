# A4 - Set State Machine Notes

## How it works
Drives off hip vertical velocity only (no bar data needed yet), normalized by
torso length (shoulder-to-hip distance) so the thresholds don't depend on how
far the lifter is from the camera. Three phases: TOP -> DESCENDING -> ASCENDING
-> TOP. A rep closes when the lifter is "settled" (near-zero velocity) for
`settle_hold_s`. A set closes when settled at TOP for `stand_still_s` (default
3.0 s, matching the concept's "stands up for >3 seconds").

## Why pose-only first
A3 (bar tracker) isn't trained yet. This lets A4, A5 (clipper) and B's
kinematics code all be developed and tested now, on synthetic data, without
waiting. Once A3 has real weights, bar-y velocity should be added as a second
signal (see the NOTE at the bottom of `state_machine.py`) -- pose alone will
likely be too noisy on your own real footage (loose clothing, occlusion at the
bottom of a squat).

## Defaults to tune once you have real video
| Param | Default | What to watch for |
|---|---|---|
| `v_thresh` | 0.15 body-lengths/s | too low = triggers on fidgeting/setup; too high = misses slow grinding reps |
| `v_settle` | 0.05 | should be clearly below `v_thresh` (hysteresis gap avoids flicker) |
| `settle_hold_s` | 0.15 s | too short = a rep can close mid-descent on a pause squat |
| `stand_still_s` | 3.0 s | from the concept spec; shorten for testing so you're not standing still 3 s every take |
| `min_rep_gap_s` | 0.3 s | guards against velocity noise re-triggering DESCENDING right after a rep closes |

## What to test once you have real clips
1. Run `state_machine.py` frame-by-frame on your `perception.export` output (pose only, ignore bar fields for now) and print events.
2. Check: does Set_Start fire on the actual unrack, not on setup/walk-in? Does each rep get one RepEvent? Does Set_End fire once you re-rack, not early during a paused top?
3. Note false positives/negatives and the threshold you changed to fix them, here.
4. Pause squats and bar walkouts before unracking are the likely failure cases -- call them out if you see them.

## Known limitations (say these plainly in the report)
- No bar signal yet, so a lifter shuffling/adjusting stance mid-set could be misread as rep boundaries.
- Doesn't yet distinguish exercise type (squat vs deadlift vs isometric) -- assumes a repeated down/up motion, so this version isn't meant for planks/holds (that's A6).
- `finalize()` must be called at video end or an in-progress set at the very last frame is silently dropped.
