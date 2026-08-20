# Testing strategy

## Three layers, three purposes

This project uses three distinct kinds of tests, each answering a different question:

1. **Unit tests** (backend, 60 tests; frontend, 5 tests) — "does this specific piece of logic behave correctly, in isolation?" Run via `python manage.py test weather` and `npm run test:unit`, fast (well under a second for the whole backend suite), no network calls.
2. **Adversarial smoke test, local** (`scripts/smoke_test_validation.py`, 25 cases) — "does the live server reject bad input correctly?" Hits the running Django dev server with edge cases designed to break it, not confirm it works.
3. **Adversarial smoke test, live AEMET** (`scripts/smoke_test_live_aemet.py`, 11 cases) — "does the full system work end-to-end against the real external API, including caching performance?"

None of these are redundant with each other: unit tests verify logic in isolation with mocks, and can't catch integration or configuration mistakes; the smoke scripts verify the real running system, but are too slow and coarse-grained to pin down exactly *why* something failed the way a unit test can.

## Backend unit tests, organized by module

`weather/tests/` mirrors the module structure of `weather/`, one test file per module:

- `test_aemet_client.py` — the two-step AEMET request pattern, mocking `requests.get`
- `test_cache.py` — gap detection (`find_missing_ranges`), chunk splitting (`_split_into_chunks`), and the caching orchestration (`get_observations`), mocking `fetch_antarctica_observations`
- `test_serializers.py` — field filtering, output field renaming, and the six timezone/DST cases described in [`timezone-handling.md`](timezone-handling.md)
- `test_aggregation.py` — hourly/daily/monthly grouping, average calculation with missing values, and the Madrid-calendar-day cases described in [`aggregation.md`](aggregation.md)
- `test_views.py` — the full request/response cycle for the endpoint, mocking `get_observations`

Each layer is mocked at the boundary of the layer below it — `test_views.py` mocks `get_observations`, not `requests.get` — so a test failure points precisely at the layer responsible, without needing to reason about the whole stack at once.

## Frontend unit tests

`frontend/src/api.spec.ts` and `frontend/src/components/QueryForm.spec.ts` cover the two pieces of the frontend with actual logic: URL construction and error handling in `api.ts`, and the form's emitted event shape in `QueryForm.vue`. `ResultsTable.vue` and `ResultsChart.vue` were left untested at the unit level, since they're mostly direct data-to-presentation mapping with little independent logic to verify — they were instead checked manually against real API responses in the browser during development.

## Why the adversarial smoke tests exist, and what they found

The unit test suite alone confirms that the code does what its author expected it to do — it doesn't actively try to find cases the author *didn't* think of. `scripts/smoke_test_validation.py` was written specifically to attack the API with edge cases (reversed date ranges, malformed dates, SQL-injection-like input, oversized query params, case sensitivity edge cases, etc.) rather than to confirm the happy path.

This found a real bug: **a reversed date range (`fechaini` after `fechafin`) returned `200` with an empty list instead of an error**, because `find_missing_ranges` silently produced zero expected timestamps for an inverted range rather than signaling anything was wrong. This was fixed by adding an explicit `start > end` check in the view (see the corresponding commit and test in `weather/tests/test_views.py`), and is a concrete example of a defect that unit tests alone — which only test cases the author already anticipated — would not have caught.

Two other flagged cases turned out to be incorrect assumptions in the test script itself rather than real bugs (Python's `strptime` tolerating non-zero-padded months/days; an AEMET request for a sub-10-minute range correctly failing since it doesn't align with AEMET's own granularity), and the script's expectations were corrected accordingly rather than "fixing" correct behavior.

`scripts/smoke_test_live_aemet.py` complements this by verifying claims made in [`caching-strategy.md`](caching-strategy.md) with real timing data rather than just asserting them: repeating an identical request went from ~0.7s (real AEMET call) to ~0.01s (cache hit), a partial-overlap request completed in ~0.01s (confirming only the missing gap was fetched, not the whole range), and both Antarctic stations returned real data.

## Running the tests

```bash
# Backend unit tests
cd backend && python manage.py test weather

# Frontend unit tests
cd frontend && npm run test:unit

# Adversarial smoke tests (server must be running)
python scripts/smoke_test_validation.py
python scripts/smoke_test_live_aemet.py   # hits real AEMET — uses API quota
```
