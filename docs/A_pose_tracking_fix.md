# Real-footage finding: tracking jumped to a background person

## What happened
On `SideSquat_JJD.mp4`: the skeleton jumped onto a person standing far behind
the lifter, and joints weren't tracked well at the bottom of the squat.

## Root cause
`PoseEstimator` picked "whichever detected person has the biggest bounding
box" independently on every single frame. At the bottom of a squat the
lifter's own box compresses -- sometimes enough that a farther, steadier
background person's box briefly looks bigger, so the wrong person gets
selected. This likely explains both symptoms at once: the visible jump to the
background person, *and* the apparent tracking loss at the bottom (which was
probably really "briefly tracking the wrong person," not "losing the right
person's joints").

## Fix
Added `select_person_idx()` in `perception/pose.py`: instead of picking the
biggest box every frame, pick whichever detected person's hips are *closest to
where the lifter was in the previous frame* ("track continuity"). Only fall
back to biggest-box if nothing is close enough (meaning the track is
genuinely lost, e.g. right at the start, or after a hard cut) -- controlled by
`max_jump_frac` (default 0.20 = 20% of the frame diagonal).

Tested in isolation (`tests/perception/test_person_selection.py`) with the
literal scenario you hit: a closer person's box shrinking below a farther
person's box, confirming the fix stays locked onto the closer/continuous
track rather than the bigger one.

## Re-test on your real footage
```
python -m perception.demo --source data\raw\SideSquat_JJD.mp4 --out data\raw\SideSquat_JJD_v2.mp4
```
Check again: does it stay locked on you now, including at the bottom of the
squat? If the background jump is gone but bottom-of-squat tracking is still
shaky, that's a separate, harder problem (occlusion/extreme joint angles
confusing the pose model itself, not person-selection) -- worth noting as a
known limitation either way, and something to mention plainly in the report:
2D pose models are least reliable at extreme flexion and when limbs occlude
each other, which is exactly the bottom of a squat.

## If it's still not enough
- Try `--weights yolo11s-pose.pt` (bigger, slower, more accurate model)
- Lower `max_jump_frac` if the background person is close in the frame to
  where you are (less room to distinguish by distance alone)
- As a last resort, a manual region-of-interest crop (ignore anything outside
  a box around where the lifter should be) is the blunt-but-reliable fix
