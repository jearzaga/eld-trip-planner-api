from hos.engine import _State


# A-12: a longer rest satisfies a shorter one, so a break is skipped once fuel already covers it
def test_break_is_skipped_when_fuel_is_also_due():
    s = _State()
    s.resolve({"fuel", "break"})
    assert [segment.note for segment in s.segments] == ["Fuel"]


# A-12: fuel is taken first, then the single longest rest (34h > 10h)
def test_fuel_taken_before_the_34_hour_restart():
    s = _State()
    s.resolve({"fuel", "70"})
    assert [segment.note for segment in s.segments] == ["Fuel", "34-hour restart"]


# A-12: the 34-hour restart is chosen over a 10-hour reset when both are due
def test_34_hour_restart_wins_over_10_hour_reset():
    s = _State()
    s.resolve({"11", "70"})
    assert [segment.note for segment in s.segments] == ["34-hour restart"]


# A-12: the 10-hour reset is chosen over a 30-minute break when both are due
def test_10_hour_reset_wins_over_30_minute_break():
    s = _State()
    s.resolve({"14", "break"})
    assert [segment.note for segment in s.segments] == ["10-hour reset"]


# A-12: never two back-to-back rests, even when three limits are hit at once
def test_only_one_rest_is_ever_applied_even_with_three_limits_hit():
    s = _State()
    s.resolve({"70", "11", "break"})
    assert [segment.note for segment in s.segments] == ["34-hour restart"]
