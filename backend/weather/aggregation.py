"""Aggregates cached measurements into hourly, daily, or monthly buckets.

Hourly aggregation groups by the UTC hour (an hour has the same
duration regardless of timezone). Daily and monthly aggregation group
by the calendar day/month in Europe/Madrid, per the spec, since a
"day" in Madrid does not align with a "day" in UTC.
"""

import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")

VALID_AGGREGATIONS = ("none", "hourly", "daily", "monthly")


@dataclass
class AggregatedMeasurement:
    """A synthetic measurement representing the average over a time bucket."""

    station: str
    timestamp: datetime.datetime
    temperature: float | None
    pressure: float | None
    speed: float | None


def _bucket_key(measurement, aggregation: str):
    """Return the grouping key for a measurement, given the aggregation level."""
    if aggregation == "hourly":
        utc_time = measurement.timestamp
        return (utc_time.year, utc_time.month, utc_time.day, utc_time.hour)

    madrid_time = measurement.timestamp.astimezone(MADRID_TZ)
    if aggregation == "daily":
        return (madrid_time.year, madrid_time.month, madrid_time.day)
    if aggregation == "monthly":
        return (madrid_time.year, madrid_time.month)

    raise ValueError(f"Unknown aggregation level: {aggregation}")


def _bucket_start_utc(measurement, aggregation: str) -> datetime.datetime:
    """Return the UTC timestamp representing the start of a measurement's bucket."""
    if aggregation == "hourly":
        utc_time = measurement.timestamp
        return utc_time.replace(minute=0, second=0, microsecond=0)

    madrid_time = measurement.timestamp.astimezone(MADRID_TZ)
    if aggregation == "daily":
        bucket_start_madrid = madrid_time.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        bucket_start_madrid = madrid_time.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return bucket_start_madrid.astimezone(datetime.timezone.utc)


def _average(values: list[float | None]) -> float | None:
    """Return the average of the non-None values, or None if all are missing."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def aggregate_measurements(measurements, aggregation: str):
    """Group measurements into buckets and average each variable within them.

    Returns the measurements unchanged if aggregation is "none".
    """
    if aggregation == "none":
        return list(measurements)

    buckets: dict[tuple, list] = {}
    for measurement in measurements:
        key = _bucket_key(measurement, aggregation)
        buckets.setdefault(key, []).append(measurement)

    aggregated = []
    for bucket_measurements in buckets.values():
        first = bucket_measurements[0]
        aggregated.append(
            AggregatedMeasurement(
                station=first.station,
                timestamp=_bucket_start_utc(first, aggregation),
                temperature=_average([m.temperature for m in bucket_measurements]),
                pressure=_average([m.pressure for m in bucket_measurements]),
                speed=_average([m.speed for m in bucket_measurements]),
            )
        )

    aggregated.sort(key=lambda m: m.timestamp)
    return aggregated