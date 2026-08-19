"""Gap detection for the local Measurement cache.

Given a date range and a station, determines which 10-minute
timestamps are missing from the local SQLite cache, grouped into
contiguous chunks, so the AEMET client only needs to fetch what is
genuinely missing.
"""

import datetime
import logging

from .models import Measurement

from .aemet_client import fetch_antarctica_observations

logger = logging.getLogger("weather")

GRANULARITY = datetime.timedelta(minutes=10)

AEMET_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

MAX_AEMET_RANGE_DAYS = 30



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


def _split_into_chunks(
    start: datetime.datetime, end: datetime.datetime, max_days: int = MAX_AEMET_RANGE_DAYS
) -> list[tuple[datetime.datetime, datetime.datetime]]:
    """Split a date range into sub-ranges no longer than max_days.

    AEMET's API rejects requests spanning more than ~1 month, so any
    gap larger than that must be fetched in multiple smaller requests.
    A gap already within the limit is returned unchanged, as a single
    chunk.
    """
    max_span = datetime.timedelta(days=max_days)
    chunks = []
    chunk_start = start

    while chunk_start <= end:
        chunk_end = min(chunk_start + max_span, end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + GRANULARITY

    return chunks


def _to_aemet_format(dt: datetime.datetime) -> str:
    """Format a UTC datetime the way AEMET's API expects it."""
    return dt.strftime(AEMET_DATETIME_FORMAT) + "UTC"


def _store_observations(station: str, raw_observations: list[dict]) -> None:
    """Upsert raw AEMET observations into the local cache.

    Entries with a "NaN" value for a numeric field are stored as None,
    since AEMET occasionally reports a broken sensor this way.
    """
    for obs in raw_observations:
        timestamp = datetime.datetime.strptime(obs["fhora"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )
        Measurement.objects.update_or_create(
            station=station,
            timestamp=timestamp,
            defaults={
                "temperature": _safe_float(obs.get("temp")),
                "pressure": _safe_float(obs.get("pres")),
                "speed": _safe_float(obs.get("vel")),
            },
        )


def _safe_float(value) -> float | None:
    """Convert an AEMET numeric field to float, treating "NaN" as missing."""
    if value is None or value == "NaN":
        return None
    return float(value)


def get_observations(
    station: str, start: datetime.datetime, end: datetime.datetime
) -> list[Measurement]:
    """Return all cached observations for a station and range, fetching gaps first.

    Any 10-minute timestamps missing from the local cache are fetched
    from AEMET (grouped into as few requests as possible, and split
    into sub-1-month chunks since AEMET rejects longer ranges) and
    stored before returning the combined result from the database.
    """
    gaps = find_missing_ranges(station, start, end)

    if not gaps:
        logger.info("Cache hit: station=%s, range=%s to %s (no gaps)", station, start, end)
    else:
        logger.info(
            "Cache miss: station=%s, range=%s to %s, %d gap(s) to fetch",
            station, start, end, len(gaps),
        )

    for gap_start, gap_end in gaps:
        for chunk_start, chunk_end in _split_into_chunks(gap_start, gap_end):
            raw_observations = fetch_antarctica_observations(
                fecha_ini=_to_aemet_format(chunk_start),
                fecha_fin=_to_aemet_format(chunk_end),
                estacion=station,
            )
            _store_observations(station, raw_observations)

    result = list(
        Measurement.objects.filter(station=station, timestamp__gte=start, timestamp__lte=end)
    )
    logger.info("Returning %d measurement(s) for station=%s", len(result), station)
    return result