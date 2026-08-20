# Caching strategy

This describes how the local SQLite cache works: what gets fetched from AEMET vs. served locally, how large date ranges are handled, and the data-integrity decisions around it.

## Gap detection, not all-or-nothing

A simpler design would be: "if any part of the requested range is missing, re-fetch the whole range from AEMET." This was considered and rejected, because Part 2 of the brief specifically describes a scenario where traders poll frequently, often re-requesting ranges that mostly overlap with what they already asked for — all-or-nothing re-fetching would defeat the purpose of caching in exactly that common case.

Instead, `find_missing_ranges()` in `cache.py`:

1. Builds the theoretical list of every expected 10-minute timestamp in the requested range.
2. Checks which of those are already in SQLite.
3. Groups the missing ones into the fewest possible contiguous chunks.

Only those chunks (not the whole range) are requested from AEMET. This was verified with real timing data using `scripts/smoke_test_live_aemet.py`: a repeated identical request went from ~0.7s (real AEMET call) to ~0.01s (cache hit, no AEMET call at all) — see [`testing.md`](testing.md).

## Splitting large gaps for AEMET's own range limit

AEMET's API itself rejects date ranges longer than roughly one month (`"El rango de fechas no puede ser superior a 1 mes"`) — this was discovered empirically while testing wide date ranges, not documented anywhere in AEMET's official API docs (a third-party R package, `meteospain`, independently reports a similar undocumented range limit — 15 days — on a different AEMET endpoint, suggesting this is a general pattern with AEMET's API rather than something specific to the Antarctica endpoint). See [`known-limitations.md`](known-limitations.md) for how this was found and confirmed for this specific endpoint.

Once found, `_split_into_chunks()` divides any gap larger than 30 days into consecutive sub-ranges before each is fetched individually:

```python
for gap_start, gap_end in gaps:
    for chunk_start, chunk_end in _split_into_chunks(gap_start, gap_end):
        raw_observations = fetch_antarctica_observations(...)
        _store_observations(station, raw_observations)
```

For gaps already within the limit, this function is a no-op — it returns the original range as a single chunk, so there's no behavior change or extra requests for the common case of small ranges.

## Upserting, not inserting

`Measurement` has a `UniqueConstraint` on `(station, timestamp)`. Storing fetched data uses `update_or_create()` rather than `create()`, so re-fetching a range that partially overlaps with already-cached data (which can happen at chunk boundaries, or if a request race occurred) never raises an integrity error — it simply overwrites with the same (or corrected) values.

## Handling AEMET's "NaN" sensor values

AEMET occasionally reports a broken sensor as the string `"NaN"` rather than omitting the field or using `null`. `_safe_float()` treats both `None` and the literal string `"NaN"` as missing data, storing `None` in the database rather than attempting `float("NaN")` (which would silently produce an actual NaN float — a value that behaves unpredictably in comparisons and JSON serialization).

## Why SQLite alone, with no separate cache layer

There is no separate in-memory cache (Redis, LRU, etc.) sitting in front of SQLite — SQLite **is** the cache. Weather observations are historical facts that never change once recorded: a temperature reading at 00:00 on a given day is fixed forever. There's no expiry, no invalidation, no "stale data" concept to manage, so an append-only cache is the correct and simplest model for this kind of data — adding another caching layer on top would be unjustified complexity for the scope of this challenge.