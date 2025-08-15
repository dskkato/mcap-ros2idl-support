"""ROS Time and Duration utilities."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class Time:
    """Represents a ROS time with second and nanosecond fields."""

    sec: int
    nsec: int


Duration = Time


def is_time(obj: object | None) -> bool:
    """Return ``True`` if *obj* looks like a :class:`Time`."""

    if isinstance(obj, Time):
        return True
    if isinstance(obj, dict):
        return set(obj.keys()) == {"sec", "nsec"}
    return False


def to_string(stamp: Time, allow_negative: bool = False) -> str:
    if not allow_negative and (stamp.sec < 0 or stamp.nsec < 0):
        raise ValueError(
            f"Invalid negative time {{ sec: {stamp.sec}, nsec: {stamp.nsec} }}"
        )
    return f"{int(stamp.sec)}.{int(stamp.nsec):09d}"


def _parse_nanoseconds(digits: str) -> int:
    digits_short = 9 - len(digits)
    return round(int(digits, 10) * 10**digits_short)


def from_string(text: str) -> Optional[Time]:
    if re.fullmatch(r"\d+\.?", text):
        sec = int(text.rstrip("."))
        return Time(sec=sec, nsec=0)
    if not re.fullmatch(r"\d+\.\d+", text):
        return None
    whole, frac = text.split(".", 1)
    sec = int(whole)
    nsec = _parse_nanoseconds(frac)
    return fix_time(Time(sec=sec, nsec=nsec))


def to_rfc3339_string(stamp: Time) -> str:
    if stamp.sec < 0 or stamp.nsec < 0:
        raise ValueError(
            f"Invalid negative time {{ sec: {stamp.sec}, nsec: {stamp.nsec} }}"
        )
    if stamp.nsec >= 1_000_000_000:
        raise ValueError(f"Invalid nanosecond value {stamp.nsec}")
    date = datetime.fromtimestamp(stamp.sec, tz=timezone.utc)
    return date.strftime("%Y-%m-%dT%H:%M:%S") + f".{stamp.nsec:09d}Z"


_RFC3339_RE = re.compile(
    r"^(\d{4,})-(\d\d)-(\d\d)[Tt](\d\d):(\d\d):(\d\d)"
    r"(?:\.(\d+))?(?:[Zz]|([+-])(\d\d):(\d\d))$"
)


def from_rfc3339_string(text: str) -> Optional[Time]:
    m = _RFC3339_RE.fullmatch(text)
    if not m:
        return None
    year, month, day, hour, minute, second, frac, sign, off_h, off_m = m.groups()
    dt = datetime(
        int(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second),
        tzinfo=timezone.utc,
    )
    if sign:
        offset = timedelta(hours=int(off_h), minutes=int(off_m))
        if sign == "+":
            dt -= offset
        else:
            dt += offset
    sec = int(dt.timestamp())
    nsec = _parse_nanoseconds(frac) if frac else 0
    return fix_time(Time(sec=sec, nsec=nsec))


def to_date(stamp: Time) -> datetime:
    return datetime.fromtimestamp(stamp.sec + stamp.nsec / 1e9, tz=timezone.utc)


def from_date(date: datetime) -> Time:
    millis = int(date.timestamp() * 1000)
    sec = millis // 1000
    nsec = (millis % 1000) * 1_000_000
    return Time(sec=sec, nsec=nsec)


def percent_of(start: Time, end: Time, target: Time) -> float:
    total = subtract(end, start)
    part = subtract(target, start)
    return to_sec(part) / to_sec(total)


def interpolate(start: Time, end: Time, fraction: float) -> Time:
    duration = subtract(end, start)
    return add(start, from_sec(fraction * to_sec(duration)))


def fix_time(t: Time, allow_negative: bool = False) -> Time:
    secs_from_nanos = t.nsec // 1_000_000_000
    new_sec = t.sec + secs_from_nanos
    new_nsec = t.nsec % 1_000_000_000
    if new_nsec < 0:
        new_nsec += 1_000_000_000
        new_sec -= 1
    result = Time(sec=new_sec, nsec=new_nsec)
    if (not allow_negative and result.sec < 0) or result.nsec < 0:
        raise ValueError(f"Cannot normalize invalid time {to_string(result, True)}")
    return result


def add(a: Time, b: Time) -> Time:
    return fix_time(Time(sec=a.sec + b.sec, nsec=a.nsec + b.nsec))


def subtract(a: Time, b: Time) -> Time:
    return fix_time(Time(sec=a.sec - b.sec, nsec=a.nsec - b.nsec), allow_negative=True)


def to_nanosec(t: Time) -> int:
    return t.sec * 1_000_000_000 + t.nsec


def to_microsec(t: Time) -> float:
    return (t.sec * 1_000_000_000 + t.nsec) / 1000


def to_sec(t: Time) -> float:
    return t.sec + t.nsec * 1e-9


def from_sec(value: float) -> Time:
    sec = math.trunc(value)
    nsec = round((value - sec) * 1_000_000_000)
    sec += math.trunc(nsec / 1_000_000_000)
    nsec %= 1_000_000_000
    return Time(sec=sec, nsec=nsec)


def from_nanosec(nsec: int) -> Time:
    return Time(sec=nsec // 1_000_000_000, nsec=nsec % 1_000_000_000)


def to_millis(t: Time, round_up: bool = True) -> int:
    seconds_millis = t.sec * 1000
    nsec_millis = t.nsec / 1_000_000
    if round_up:
        return seconds_millis + math.ceil(nsec_millis)
    return seconds_millis + math.floor(nsec_millis)


def from_millis(value: int | float) -> Time:
    sec = math.trunc(value / 1000)
    nsec = round((value - sec * 1000) * 1_000_000)
    sec += math.trunc(nsec / 1_000_000_000)
    nsec %= 1_000_000_000
    return Time(sec=sec, nsec=nsec)


def from_micros(value: int | float) -> Time:
    sec = math.trunc(value / 1_000_000)
    nsec = round((value - sec * 1_000_000) * 1000)
    sec += math.trunc(nsec / 1_000_000_000)
    nsec %= 1_000_000_000
    return Time(sec=sec, nsec=nsec)


def clamp_time(time: Time, start: Time, end: Time) -> Time:
    if compare(start, time) > 0:
        return Time(sec=start.sec, nsec=start.nsec)
    if compare(end, time) < 0:
        return Time(sec=end.sec, nsec=end.nsec)
    return Time(sec=time.sec, nsec=time.nsec)


def is_time_in_range_inclusive(time: Time, start: Time, end: Time) -> bool:
    if compare(start, time) > 0 or compare(end, time) < 0:
        return False
    return True


def compare(left: Time, right: Time) -> int:
    sec_diff = left.sec - right.sec
    return sec_diff if sec_diff != 0 else left.nsec - right.nsec


def is_less_than(left: Time, right: Time) -> bool:
    return compare(left, right) < 0


def is_greater_than(left: Time, right: Time) -> bool:
    return compare(left, right) > 0


def are_equal(left: Time, right: Time) -> bool:
    return left.sec == right.sec and left.nsec == right.nsec


__all__ = [
    "Time",
    "Duration",
    "is_time",
    "to_string",
    "from_string",
    "to_rfc3339_string",
    "from_rfc3339_string",
    "to_date",
    "from_date",
    "percent_of",
    "interpolate",
    "fix_time",
    "add",
    "subtract",
    "to_nanosec",
    "to_microsec",
    "to_sec",
    "from_sec",
    "from_nanosec",
    "to_millis",
    "from_millis",
    "from_micros",
    "clamp_time",
    "is_time_in_range_inclusive",
    "compare",
    "is_less_than",
    "is_greater_than",
    "are_equal",
]
