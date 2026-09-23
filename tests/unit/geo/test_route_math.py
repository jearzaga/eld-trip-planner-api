import pytest

from geo.route_math import cumulative_miles, point_at_fraction, point_at_mile

MILES_PER_DEGREE_LATITUDE = 69.1

MERIDIAN_LINE = [(-77.0, 0.0), (-77.0, 1.0), (-77.0, 2.0)]
SINGLE_VERTEX = [(-77.0, 37.5)]
DUPLICATE_VERTICES = [(-77.0, 37.5), (-77.0, 37.5)]


def test_cumulative_miles_starts_at_zero():
    assert cumulative_miles(MERIDIAN_LINE)[0] == 0.0


def test_cumulative_miles_matches_degrees_of_latitude_on_a_meridian():
    running = cumulative_miles(MERIDIAN_LINE)
    assert running[1] == pytest.approx(MILES_PER_DEGREE_LATITUDE, rel=1e-3)
    assert running[2] == pytest.approx(2 * MILES_PER_DEGREE_LATITUDE, rel=1e-3)


def test_cumulative_miles_of_single_vertex_is_zero():
    assert cumulative_miles(SINGLE_VERTEX) == [0.0]


@pytest.mark.parametrize(
    "mile,expected_lat",
    [
        (0.0, 0.0),
        (MILES_PER_DEGREE_LATITUDE / 2, 0.5),
        (MILES_PER_DEGREE_LATITUDE, 1.0),
        (1.5 * MILES_PER_DEGREE_LATITUDE, 1.5),
    ],
)
def test_point_at_mile_interpolates_along_the_meridian(mile, expected_lat):
    lat, lng = point_at_mile(MERIDIAN_LINE, mile)
    assert lat == pytest.approx(expected_lat, abs=1e-2)
    assert lng == pytest.approx(-77.0)


def test_point_at_mile_clamps_below_zero_to_first_vertex():
    assert point_at_mile(MERIDIAN_LINE, -10.0) == (0.0, -77.0)


def test_point_at_mile_clamps_past_the_end_to_last_vertex():
    assert point_at_mile(MERIDIAN_LINE, 999.0) == (2.0, -77.0)


def test_point_at_mile_on_single_vertex_geometry_returns_that_vertex():
    assert point_at_mile(SINGLE_VERTEX, 5.0) == (37.5, -77.0)


def test_point_at_mile_on_zero_length_geometry_does_not_raise():
    assert point_at_mile(DUPLICATE_VERTICES, 5.0) == (37.5, -77.0)


@pytest.mark.parametrize(
    "fraction,expected_lat",
    [
        (0.0, 0.0),
        (0.25, 0.5),
        (0.5, 1.0),
        (1.0, 2.0),
    ],
)
def test_point_at_fraction_interpolates_along_total_length(fraction, expected_lat):
    lat, lng = point_at_fraction(MERIDIAN_LINE, fraction)
    assert lat == pytest.approx(expected_lat, abs=1e-2)
    assert lng == pytest.approx(-77.0)


def test_point_at_fraction_clamps_outside_zero_to_one():
    assert point_at_fraction(MERIDIAN_LINE, -1.0) == point_at_fraction(MERIDIAN_LINE, 0.0)
    assert point_at_fraction(MERIDIAN_LINE, 5.0) == point_at_fraction(MERIDIAN_LINE, 1.0)


def test_point_at_fraction_on_zero_length_geometry_returns_first_vertex():
    assert point_at_fraction(DUPLICATE_VERTICES, 0.5) == (37.5, -77.0)
