# Timezone handling

## Storage vs. output

All timestamps are stored in the database in **UTC** (`Measurement.timestamp` is timezone-aware, `USE_TZ = True`). UTC is a fixed reference with no ambiguity and no daylight saving changes, so it's the correct choice for a value that needs to be compared, sorted, and grouped reliably.

The spec requires the **output** `Datetime` field to be in Europe/Madrid (CET/CEST), with the UTC offset included (e.g. `+02:00`). This conversion happens exactly once, at the last possible moment: in `serializers.py`, right before building the response dict.

```python
madrid_datetime = measurement.timestamp.astimezone(MADRID_TZ)
```

`MADRID_TZ = ZoneInfo("Europe/Madrid")` is a `zoneinfo` object carrying the IANA timezone database's rules for Madrid — including exactly when it switches between CET (UTC+1) and CEST (UTC+2) each year. `.astimezone()` looks up those rules for the specific date of the timestamp being converted and computes the correct offset automatically; the offset is never hardcoded.

## DST behavior

Spain switches to CEST on the last Sunday of March (clocks jump from 02:00 to 03:00 — the 02:00–02:59 hour never occurs that day) and back to CET on the last Sunday of October (clocks fall from 03:00 to 02:00 — that hour occurs twice, once in each timezone).

This was confirmed against the 2024/2025-adjacent real dates for 2026 (March 29 and October 25), and is tested explicitly in `weather/tests/test_serializers.py` (`SerializeMeasurementTimezoneTests`) with 6 cases:

- Plain winter and summer offsets (`+01:00` / `+02:00`)
- The instant just before the spring-forward jump, and the instant of the jump itself (confirming the missing hour)
- The instant just before the fall-back, and the instant of the fall-back itself (confirming the repeated hour is disambiguated correctly by its offset)

Because storage is always in UTC — an unambiguous, single timeline — there's no risk of the classic "which occurrence of 02:30 did you mean" problem on the storage side. The ambiguity only exists when *displaying* Madrid local time, and the required UTC offset in the output resolves it.

## Aggregation and the Madrid calendar day

The spec explicitly calls out that daily/monthly aggregation "requires considering the time zone location of the meteo station." A UTC calendar day does not align with a Madrid calendar day — e.g. `23:30 UTC` on Jan 14 is already `00:30` on Jan 15 in Madrid (CET, +1h).

`aggregation.py` handles this by converting to Madrid time *before* computing the grouping key for daily/monthly aggregation (but not for hourly, since an hour has the same duration regardless of timezone):

```python
madrid_time = measurement.timestamp.astimezone(MADRID_TZ)
if aggregation == "daily":
    return (madrid_time.year, madrid_time.month, madrid_time.day)
```

This is tested explicitly in `weather/tests/test_aggregation.py`, including a case where a late-UTC measurement correctly joins the *next* Madrid day's bucket, and a case covering the 23-hour Madrid day caused by the March DST transition.

## The `location` parameter

The optional `location` query parameter lets the caller specify what timezone the `fechaini`/`fechafin` path parameters are written in, per the spec ("e.g., Europe/Berlin... Alternatively, ...the time zone shift, e.g., +02:00"). Two formats are accepted:

- A named IANA timezone (e.g. `Europe/Berlin`) — resolved via `ZoneInfo`, which carries that timezone's own DST rules.
- A fixed UTC offset (e.g. `+02:00` or `-05:30`) — parsed manually and wrapped in `datetime.timezone`.

If omitted, input dates are interpreted as UTC (this preserves the original behavior from before `location` was added, and matches the format AEMET itself expects).

```python
input_tz = resolve_input_timezone(request.query_params.get("location"))
start = start_naive.replace(tzinfo=input_tz).astimezone(datetime.timezone.utc)
```

This only affects how *input* dates are interpreted; the output `Datetime` is always Europe/Madrid regardless of what `location` was used for the request, per the spec.