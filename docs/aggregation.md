# Aggregation

## What gets aggregated, and how

When `aggregation` is `hourly`, `daily`, or `monthly`, `aggregate_measurements()` in `aggregation.py` groups the cached 10-minute `Measurement` records into buckets and replaces each group with a single synthetic record holding the **average** of `temperature`, `pressure`, and `speed` within that bucket.

The brief doesn't specify which statistic to use for aggregation — average was chosen as the standard, expected choice for climatological variables like these (temperature, pressure, wind speed), rather than min/max/sum, which wouldn't make physical sense as a single representative value for a time period.

When `aggregation` is `none` (or omitted), `aggregate_measurements()` is a no-op: it returns the input list unchanged.

## The `AggregatedMeasurement` shape

An aggregated bucket isn't a real `Measurement` from the database — it's a synthetic value computed on the fly, so it's represented by a separate lightweight `dataclass`:

```python
@dataclass
class AggregatedMeasurement:
    station: str
    timestamp: datetime.datetime
    temperature: float | None
    pressure: float | None
    speed: float | None
```

It deliberately has the exact same shape as `Measurement` (same attribute names, same types). This means `serialize_measurement()` in `serializers.py` can serialize either type without any special-casing — it only reads `.station`, `.timestamp`, `.temperature`, `.pressure`, `.speed`, and doesn't care whether the object came from the database or was just computed.

## Why aggregation isn't persisted

Aggregated results aren't stored anywhere — they're recomputed on every request from the cached raw `Measurement` records. This mirrors the reasoning in [`caching-strategy.md`](caching-strategy.md): a database table exists to persist real-world facts worth keeping (the raw AEMET readings); an aggregation is a derived view specific to one request's parameters (station, range, aggregation level), cheap to recompute, and not something other requests would reuse in the same shape. Persisting it would just be redundant storage with a staleness problem if the underlying data ever changed.

## Grouping key: UTC hour, but Madrid day/month

The brief explicitly warns that "daily and monthly aggregation requires considering the time zone location of the meteo station." `_bucket_key()` handles this by choosing the grouping key differently depending on the aggregation level:

```python
def _bucket_key(measurement, aggregation):
    if aggregation == "hourly":
        utc_time = measurement.timestamp
        return (utc_time.year, utc_time.month, utc_time.day, utc_time.hour)

    madrid_time = measurement.timestamp.astimezone(MADRID_TZ)
    if aggregation == "daily":
        return (madrid_time.year, madrid_time.month, madrid_time.day)
    if aggregation == "monthly":
        return (madrid_time.year, madrid_time.month)
```

- **Hourly** groups by the UTC hour directly — an hour has the same duration and boundaries regardless of timezone, so no conversion is needed.
- **Daily** and **monthly** convert to Europe/Madrid *before* computing the grouping key. Without this, a measurement at `23:30 UTC` would be grouped into the wrong day whenever Madrid's local date has already rolled over (e.g. in winter, CET is UTC+1, so `23:30 UTC` on Jan 14 is already `00:30` on Jan 15 in Madrid).

This is tested explicitly in `weather/tests/test_aggregation.py`, including a case where a late-UTC measurement correctly joins the *next* Madrid day's bucket, and one covering the 23-hour Madrid day caused by the March DST transition (see [`timezone-handling.md`](timezone-handling.md)).

## Bucket timestamp: the start of the period, in UTC

Each aggregated result needs a representative `Datetime` to report back. `_bucket_start_utc()` computes the *start* of the bucket (the top of the hour, midnight in Madrid, or the 1st of the month at midnight in Madrid) and converts it back to UTC, so the resulting `AggregatedMeasurement.timestamp` stays consistent with how raw `Measurement.timestamp` values are stored — the Madrid conversion for display still happens once, later, in `serialize_measurement()`.

## Handling missing values within a bucket

`_average()` ignores `None` values (from AEMET's occasional broken-sensor readings, see [`caching-strategy.md`](caching-strategy.md)) rather than treating them as zero, which would silently skew the average downward. If every value in a bucket is `None`, the aggregated result for that variable is also `None`, not a fabricated number.
