# Known limitations

This documents things that were intentionally left as-is, discovered along the way, or worth knowing about — rather than silently leaving gaps unexplained, per the brief's own guidance ("if you couldn't implement something due to time constraints, at least mention it in the README or in TODO comments").

## AEMET's ~1-month range limit

**What was found:** AEMET's own API rejects date ranges longer than roughly one month, returning `{"descripcion": "El rango de fechas no puede ser superior a 1 mes", "estado": 404}`. This is not documented anywhere in AEMET's official OpenData documentation — it was discovered empirically while testing a wide date range against the live API with `curl`:

```bash
curl -v "https://opendata.aemet.es/opendata/api/antartida/datos/fechaini/2026-01-01T00:00:00UTC/fechafin/2026-02-15T00:00:00UTC/estacion/89070?api_key=$AEMET_KEY"
# < aemet_mensaje: El rango de fechas no puede ser superior a 1 mes
# < aemet_estado: 404
```

A third-party R package, `meteospain`, independently documents a similar undocumented limit (15 days) on a different AEMET endpoint, suggesting this is a general pattern with AEMET's API rather than something specific to the Antarctica endpoint.

**How it was handled:** `_split_into_chunks()` in `cache.py` splits any gap larger than 30 days into consecutive sub-ranges before each is fetched from AEMET individually. This was verified end-to-end by requesting the exact range that previously failed (Jan 1 – Feb 15, 2026) through the API after the fix, which returned `200` with the full combined dataset. See [`caching-strategy.md`](caching-strategy.md) for the implementation.

## Station indicativos (89070 / 89064) aren't in AEMET's official station inventory

AEMET's OpenData API doesn't expose a dedicated station inventory endpoint for Antarctica (the general `climatologicos/inventarioestaciones` endpoint only covers the Peninsula/Balearic/Canary network). The WMO indicativos for the two Antarctic stations — Gabriel de Castilla (`89070`) and Juan Carlos I (`89064`) — were identified from AEMET's own technical publications and cross-checked against a peer-reviewed source, then independently verified by querying the live API directly (both return `HTTP 200` with real data for a known date range in the Antarctic summer season).

## `fields` query parameter has no length limit

An adversarial smoke test (`scripts/smoke_test_validation.py`) tried an extremely long `fields` value (hundreds of repeated entries). It didn't produce incorrect results — duplicate valid field names are simply processed redundantly — but there's no explicit length cap on the parameter. This is a low-priority gap: it doesn't affect correctness, only wastes some processing on abusive input. Left as a known gap rather than fixed, given the time constraints and low impact.

## No `Station` database table

Station metadata (the two valid indicativos and their display names) lives in a Python dict (`VALID_STATIONS` in `models.py`), not a database table with a foreign key from `Measurement`. This was a deliberate choice, not an oversight — see [`architecture.md`](architecture.md) for the reasoning. It would be worth revisiting if the scope grew to support AEMET's full station network, as Part 2's trader scenario hints at ("expand this service to include all available meteorological stations").

## Free-tier deployment limitations

Both the backend and frontend are deployed on Render's free tier for convenience, with two limitations worth knowing about if evaluating the live demo rather than the local setup:

- **The backend spins down after a period of inactivity.** The first request after idling can take up to ~50 seconds to respond while the instance restarts. Subsequent requests are fast.
- **The SQLite cache is not persistent across restarts/redeploys** on the free tier's ephemeral filesystem. Each time the backend service restarts, the cache starts empty and gets repopulated from AEMET on demand — the caching *logic* still works correctly within a given runtime, but doesn't survive a redeploy. A production deployment would use a persistent disk or a managed database (e.g. Postgres) instead.

Neither of these reflects a flaw in the caching design itself (see [`caching-strategy.md`](caching-strategy.md)) — they're artifacts of using a free hosting tier for a technical challenge rather than a production environment.
