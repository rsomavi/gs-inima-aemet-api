"""Resolve the optional 'location' parameter into a timezone for input dates.

Per the spec, dates can be interpreted either against a named IANA
timezone (e.g. "Europe/Berlin") or a fixed UTC offset (e.g. "+02:00").
Defaults to UTC when the parameter is not provided.
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def resolve_input_timezone(location_param: str | None) -> datetime.tzinfo:
    """Resolve the 'location' query param into a tzinfo object.

    Raises:
        ValueError: if location_param is an offset with an invalid
            format, or a timezone name AEMET/IANA doesn't recognize.
    """
    if not location_param:
        return datetime.timezone.utc

    if location_param.startswith(("+", "-")):
        return _parse_offset(location_param)

    try:
        return ZoneInfo(location_param)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Unknown location: '{location_param}'.")


def _parse_offset(offset_str: str) -> datetime.timezone:
    """Parse a fixed UTC offset like '+02:00' or '-05:30'."""
    sign = 1 if offset_str[0] == "+" else -1
    try:
        hours_str, minutes_str = offset_str[1:].split(":")
        offset = datetime.timedelta(hours=int(hours_str), minutes=int(minutes_str))
    except (ValueError, IndexError):
        raise ValueError(
            f"Invalid offset '{offset_str}'. Expected format: +HH:MM or -HH:MM."
        )
    return datetime.timezone(sign * offset)