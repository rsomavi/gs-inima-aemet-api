"""Gap detection for the local Measurement cache.

Given a date range and a station, determines which 10-minute
timestamps are missing from the local SQLite cache, grouped into
contiguous chunks, so the AEMET client only needs to fetch what is
genuinely missing.
"""

import datetime

from .models import Measurement

GRANULARITY = datetime.timedelta(minutes=10)


def _expected_timestamps(start: datetime.datetime, end: datetime.datetime) -> list[datetime.datetime]:
    """Return every 10-minute timestamp expected between start and end (inclusive)."""
    timestamps = []
    current = start
    while current <= end:
        timestamps.append(current)
        current += GRANULARITY
    return timestamps


def find_missing_ranges(
    station: str, start: datetime.datetime, end: datetime.datetime
) -> list[tuple[datetime.datetime, datetime.datetime]]:
    """Find contiguous sub-ranges within [start, end] not yet cached for a station.

    Args:
        station: AEMET station indicativo.
        start: Range start, timezone-aware, in UTC.
        end: Range end, timezone-aware, in UTC.

    Returns:
        A list of (chunk_start, chunk_end) tuples describing contiguous
        gaps that need to be fetched from AEMET. Empty if the whole
        range is already cached.
    """
    expected = _expected_timestamps(start, end)

    cached_timestamps = set(
        Measurement.objects.filter(
            station=station, timestamp__gte=start, timestamp__lte=end
        ).values_list("timestamp", flat=True)
    )

    missing = [ts for ts in expected if ts not in cached_timestamps]

    if not missing:
        return []

    gaps = []
    chunk_start = missing[0]
    previous = missing[0]

    for ts in missing[1:]:
        if ts - previous == GRANULARITY:
            previous = ts
        else:
            gaps.append((chunk_start, previous))
            chunk_start = ts
            previous = ts

    gaps.append((chunk_start, previous))
    return gaps