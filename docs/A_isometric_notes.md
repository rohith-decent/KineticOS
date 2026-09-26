# A6 - Isometric Alignment Detector Notes

## What's different about this module
A4 (state machine) assumes a repeated down/up motion -- it's built for
squats/deadlifts. A plank or wall-sit has no such cycle: the whole point is to
NOT move. So A6 doesn't detect events at all -- it just outputs one honest
number per frame: how many degrees the body has deviated from a straight
ankle-hip-shoulder line. 0 = perfect plank; bigger = hips sagging (common
fault) or piking up.

## Where the 8-degree threshold logic lives
On purpose, **not here**. This module only measures the angle error. Role B's
chronometer (B4) is what decides "8 degrees is too much, pause the timer" and
handles the pause/resume hysteresis (see docs/03_ARCHITECTURE_AND_CONTRACTS.md,
contract 4, and `analytics/chronometer.py` -- currently a B4 stub). Keeping
these separate means B can tune the threshold without touching your code, and
you can improve the angle measurement without touching theirs.

## Confidence handling
Uses whichever side (left or right) has better keypoint confidence, not an
average of both -- in a side-view plank the far side is often partly hidden
behind the near side, so averaging a good reading with a bad one makes things
worse, not better.

## What to test on real footage
- Film a plank from the side, including a moment where you deliberately let
  your hips sag, and a moment of good form.
- Run pose + `IsometricStream` frame by frame and plot `angle_error_deg` over
  time (similar to the debug CSV trick from A4) -- it should visibly spike
  during the sag and sit near 0 during good form.
- Check what happens when the camera angle isn't perfectly side-on -- some
  error is expected off-axis; note how much in your report.

## Known limitations to state plainly in the report
- Assumes a side-view camera; doesn't work for a front-view plank (no
  meaningful ankle-hip-shoulder line visible from the front).
- No smoothing applied here (deliberately) -- B4 receives the raw signal so it
  can apply its own hysteresis; if the raw signal looks too jumpy on real
  footage, that's a discussion to have with B, not necessarily an A6 fix.
- Doesn't distinguish "hips sagging" from "hips piking" -- both currently
  register as the same error magnitude. If that distinction matters for the
  final product, it's a small extension (check the sign of the deviation, not
  just its magnitude).
