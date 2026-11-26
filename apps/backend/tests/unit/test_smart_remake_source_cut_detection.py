from viraldy.modules.smart_remake.engine.source_shot_detector import _normalize_cut_times


def test_measured_source_cuts_are_not_truncated_after_twelve_shots():
    cut_times = [float(index) for index in range(1, 25)]
    assert _normalize_cut_times(cut_times, duration=30) == cut_times


def test_cut_normalization_still_filters_too_close_and_out_of_range_boundaries():
    assert _normalize_cut_times([0.1, 1, 1.1, 2, 9.9], duration=10) == [1, 2]
