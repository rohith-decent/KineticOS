from typing import List
from contracts.models import IsometricSample, IsometricReport, ChronometerState

class TrueTimeChronometer:
    """
    True-Time Chronometer with hysteresis:
    - Pause if angle_error > 8.0 deg for >= 150 ms.
    - Resume if angle_error < 6.0 deg for >= 300 ms.
    - Amber state during boundary violations or while accumulating pause/resume hysteresis.
    """
    PAUSE_THRESHOLD_DEG = 8.0
    RESUME_THRESHOLD_DEG = 6.0
    PAUSE_HYSTERESIS_S = 0.150   # 150 ms
    RESUME_HYSTERESIS_S = 0.300  # 300 ms

    def __init__(self, exercise: str = "plank"):
        self.exercise = exercise
        self.state = ChronometerState.ACTIVE
        self.true_tut_s = 0.0
        self.paused_duration_s = 0.0
        self.pause_count = 0

        self._last_t: float | None = None
        self._error_high_since: float | None = None
        self._error_low_since: float | None = None

    def process_sample(self, sample: IsometricSample) -> ChronometerState:
        if not sample.valid:
            return self.state

        if self._last_t is None:
            self._last_t = sample.t
            return self.state

        dt = max(0.0, sample.t - self._last_t)
        self._last_t = sample.t

        # State transition logic with hysteresis
        if self.state in (ChronometerState.ACTIVE, ChronometerState.AMBER):
            if sample.angle_error_deg > self.PAUSE_THRESHOLD_DEG:
                if self._error_high_since is None:
                    self._error_high_since = sample.t
                
                # Check 150 ms hysteresis window
                if (sample.t - self._error_high_since) >= self.PAUSE_HYSTERESIS_S:
                    self.state = ChronometerState.PAUSED
                    self.pause_count += 1
                    self.paused_duration_s += dt
                    self._error_high_since = None
                else:
                    self.state = ChronometerState.AMBER
                    self.true_tut_s += dt
            else:
                self._error_high_since = None
                if sample.angle_error_deg >= self.RESUME_THRESHOLD_DEG:
                    self.state = ChronometerState.AMBER
                else:
                    self.state = ChronometerState.ACTIVE
                self.true_tut_s += dt

        elif self.state == ChronometerState.PAUSED:
            self.paused_duration_s += dt

            if sample.angle_error_deg < self.RESUME_THRESHOLD_DEG:
                if self._error_low_since is None:
                    self._error_low_since = sample.t

                # Check 300 ms hysteresis window
                if (sample.t - self._error_low_since) >= self.RESUME_HYSTERESIS_S:
                    self.state = ChronometerState.ACTIVE
                    self._error_low_since = None
                else:
                    self.state = ChronometerState.AMBER
            else:
                self._error_low_since = None
                self.state = ChronometerState.PAUSED

        return self.state

    def process_stream(self, samples: List[IsometricSample]) -> IsometricReport:
        for s in samples:
            self.process_sample(s)

        total_elapsed = self.true_tut_s + self.paused_duration_s
        adherence = (self.true_tut_s / total_elapsed * 100.0) if total_elapsed > 0 else 0.0

        return IsometricReport(
            exercise=self.exercise,
            total_elapsed_s=round(total_elapsed, 2),
            true_tut_s=round(self.true_tut_s, 2),
            paused_duration_s=round(self.paused_duration_s, 2),
            pause_count=self.pause_count,
            form_adherence_pct=round(adherence, 1),
            final_state=self.state,
        )