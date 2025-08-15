import datetime

import mcap_ros2idl_support.rostime as rostime


def test_is_time():
    assert not rostime.is_time(None)
    assert not rostime.is_time(True)
    assert not rostime.is_time({"sec": 1})
    assert not rostime.is_time({"nsec": 1})
    assert not rostime.is_time({"sec": 1, "nsec": 1, "other": 0})
    assert rostime.is_time({"sec": 0, "nsec": 0})
    assert rostime.is_time(rostime.Time(1, 0))


def test_rfc3339_roundtrip():
    t = rostime.Time(sec=1632939128, nsec=123456789)
    text = rostime.to_rfc3339_string(t)
    assert text == "2021-09-29T18:12:08.123456789Z"
    assert rostime.from_rfc3339_string(text) == t


def test_to_from_string():
    t = rostime.Time(10, 5)
    s = rostime.to_string(t)
    assert s == "10.000000005"
    assert rostime.from_string(s) == t


def test_conversions():
    t = rostime.Time(1, 500000000)
    assert rostime.to_sec(t) == 1.5
    assert rostime.from_sec(1.5) == t
    assert rostime.to_nanosec(t) == 1_500_000_000
    assert rostime.from_nanosec(1_500_000_000) == t
    assert rostime.to_millis(t) == 1500
    assert rostime.from_millis(1500) == t
    assert rostime.from_micros(1_500_000) == t


def test_clamp_and_compare():
    start = rostime.Time(0, 100)
    end = rostime.Time(100, 100)
    before = rostime.Time(0, 99)
    after = rostime.Time(100, 101)
    assert rostime.clamp_time(before, start, end) == start
    assert rostime.clamp_time(after, start, end) == end
    assert rostime.is_time_in_range_inclusive(start, start, end)
    assert not rostime.is_time_in_range_inclusive(before, start, end)
    assert rostime.compare(start, end) < 0
    assert rostime.is_less_than(start, end)
    assert rostime.is_greater_than(end, start)
    assert rostime.are_equal(start, rostime.Time(0, 100))


def test_percent_of_and_interpolate():
    start = rostime.Time(0, 0)
    end = rostime.Time(10, 0)
    middle = rostime.Time(5, 0)
    assert rostime.percent_of(start, end, middle) == 0.5
    assert rostime.interpolate(start, end, 0.5) == middle


def test_date_roundtrip():
    dt = datetime.datetime(2021, 9, 29, 18, 12, 8, 123000, tzinfo=datetime.timezone.utc)
    t = rostime.from_date(dt)
    assert rostime.to_date(t) == dt
