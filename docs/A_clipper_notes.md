# A5 - Auto-Clipper Notes

## What it does
Cuts raw footage down to just the working set using A4's Set_Start/Set_End
timestamps, and names the file per the concept's convention:
`Squat_Set3_140kg_RPE8.5.mp4`.

## Requires ffmpeg installed and on PATH
This module shells out to the real `ffmpeg` binary -- it isn't a Python
library. Check it's available:
```
ffmpeg -version
```
If that fails on Windows, install it (e.g. `winget install ffmpeg` or download
from ffmpeg.org and add it to PATH), then reopen your terminal.

## Two cut modes -- pick deliberately
- `reencode=False` (default): fast, lossless "stream copy". ffmpeg can only cut
  exactly on a keyframe, so your actual clip start can drift by up to ~1-2s
  depending on your phone's keyframe interval. Fine for a quick check.
- `reencode=True`: frame-accurate, but slower (re-encodes the video). **Always
  forced on automatically when you pass `watermark_text`**, since burning text
  into frames requires decoding + re-encoding anyway.

For the real "one clip per set, ready to review" feature, use `reencode=True`
(or test both and see if the keyframe drift actually matters on your footage).

## Pre-roll / post-roll
`pre_roll_s=1.0` (default) exists because A4 only fires Set_Start a few frames
*after* velocity crosses the threshold -- without a pre-roll, the very start of
rep 1 gets clipped off. Tune this once you see real clips; you may want less
pre-roll if it's cutting too far back into the walkout.

## Wiring it to A4 (once you have real video)
```python
from perception.state_machine import SetStateMachine, SetEndEvent
from perception.clipper import clip_from_set_end

sm = SetStateMachine()
set_number = 0
set_start_t = None
for t, kp in frames:                       # from your pose pipeline
    for event in sm.step(t, kp):
        if isinstance(event, SetStartEvent):
            set_start_t = event.t
        elif isinstance(event, SetEndEvent):
            set_number += 1
            clip_from_set_end(
                source_path="data/raw/squat_side_01.mp4",
                start_t=set_start_t, end_t=event.t,
                out_dir="data/clips",
                exercise="back_squat", set_number=set_number, load_kg=140,
            )
```
`load_kg` and `rpe` aren't detectable from video yet -- they're user-entered
(the app UI, once B6 exists, will ask "what weight?" before/after a set).

## What to test once you have real clips
1. Does the clip actually start at the unrack, not mid-walkout or a half-second late?
2. Does the tail include the re-rack, or cut off just before it?
3. Compare `reencode=False` vs `True` timing accuracy on your own footage/keyframe interval.
4. If watermarking, check the text is legible against your gym's lighting/background.
