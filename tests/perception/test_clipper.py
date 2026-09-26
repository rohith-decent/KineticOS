"""ffmpeg isn't assumed to be installed in every dev environment, so these
tests monkeypatch subprocess.run and check the *command* built is correct,
plus test the pure filename/timing logic directly (no subprocess at all)."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from perception.clipper import build_clip_filename, clip_set, clip_from_set_end


def test_build_clip_filename_matches_spec_example():
    assert build_clip_filename("back_squat", 3, 140, 8.5) == "Squat_Set3_140kg_RPE8.5.mp4"


def test_build_clip_filename_no_load_or_rpe():
    assert build_clip_filename("plank", 1) == "Plank_Set1.mp4"


def test_build_clip_filename_unknown_exercise_falls_back_to_title_case():
    assert build_clip_filename("bulgarian_split_squat", 2, 40) == "BulgarianSplitSquat_Set2_40kg.mp4"


def test_build_clip_filename_drops_trailing_zero():
    assert build_clip_filename("deadlift", 1, 100.0) == "Deadlift_Set1_100kg.mp4"


def _fake_run_ok(cmd, capture_output, text):
    return SimpleNamespace(returncode=0, stderr="")


def test_clip_set_computes_preroll_and_duration(tmp_path):
    out = tmp_path / "clip.mp4"
    with patch("perception.clipper.subprocess.run", side_effect=_fake_run_ok) as mock_run:
        clip_set("in.mp4", start_t=10.0, end_t=20.0, out_path=str(out),
                  pre_roll_s=1.0, post_roll_s=0.5)
        cmd = mock_run.call_args.args[0]
    assert "-ss" in cmd and cmd[cmd.index("-ss") + 1] == "9.000"     # 10 - 1 preroll
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "11.500"       # (20+0.5) - 9
    assert "-c" in cmd and "copy" in cmd                              # no watermark -> stream copy


def test_clip_set_preroll_never_goes_negative(tmp_path):
    out = tmp_path / "clip.mp4"
    with patch("perception.clipper.subprocess.run", side_effect=_fake_run_ok) as mock_run:
        clip_set("in.mp4", start_t=0.3, end_t=5.0, out_path=str(out), pre_roll_s=1.0)
        cmd = mock_run.call_args.args[0]
    assert cmd[cmd.index("-ss") + 1] == "0.000"


def test_clip_set_rejects_non_positive_duration(tmp_path):
    with pytest.raises(ValueError):
        clip_set("in.mp4", start_t=10.0, end_t=10.0, out_path=str(tmp_path / "c.mp4"),
                  pre_roll_s=0.0, post_roll_s=0.0)


def test_watermark_forces_reencode_and_adds_drawtext(tmp_path):
    out = tmp_path / "clip.mp4"
    with patch("perception.clipper.subprocess.run", side_effect=_fake_run_ok) as mock_run:
        clip_set("in.mp4", 0.0, 5.0, str(out), reencode=False, watermark_text="Set 3")
        cmd = mock_run.call_args.args[0]
    assert "libx264" in cmd                 # reencode was forced on
    assert any("drawtext" in c for c in cmd)
    assert "copy" not in cmd


def test_clip_set_raises_on_ffmpeg_failure(tmp_path):
    def _fail(cmd, capture_output, text):
        return SimpleNamespace(returncode=1, stderr="no such filter")
    with patch("perception.clipper.subprocess.run", side_effect=_fail):
        with pytest.raises(RuntimeError):
            clip_set("in.mp4", 0.0, 5.0, str(tmp_path / "c.mp4"))


def test_clip_from_set_end_builds_expected_path(tmp_path):
    with patch("perception.clipper.subprocess.run", side_effect=_fake_run_ok):
        out = clip_from_set_end("in.mp4", 10.0, 20.0, str(tmp_path),
                                 exercise="back_squat", set_number=3, load_kg=140, rpe=8.5)
    assert out.name == "Squat_Set3_140kg_RPE8.5.mp4"
    assert out.parent == tmp_path
