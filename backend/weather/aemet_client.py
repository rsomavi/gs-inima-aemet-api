"""Client for the AEMET OpenData Antarctica endpoint.

AEMET's API uses a two-step pattern: the first request returns a
short-lived URL pointing to the actual data, which must be fetched
with a second request.
"""

import requests
from django.conf import settings


class AemetApiError(Exception):
    """Raised when AEMET's API returns an error or unexpected response."""


def fetch_antarctica_observations(fecha_ini: str, fecha_fin: str, estacion: str) -> list[dict]:
    """Fetch raw 10-minute observations for an Antarctic station from AEMET.

    Args:
        fecha_ini: Start datetime in AEMET's expected format
            (AAAA-MM-DDTHH:MM:SSUTC).
        fecha_fin: End datetime, same format.
        estacion: AEMET station indicativo (e.g. "89070").

    Returns:
        A list of raw observation dicts, as returned by AEMET
        (fields: identificacion, nombre, fhora, temp, pres, vel, ...).

    Raises:
        AemetApiError: if AEMET returns an error or no data for the
            given parameters.
    """
    request_url = (
        f"{settings.AEMET_BASE_URL}/antartida/datos/"
        f"fechaini/{fecha_ini}/fechafin/{fecha_fin}/estacion/{estacion}"
    )

    first_response = requests.get(
        request_url,
        params={"api_key": settings.AEMET_API_KEY},
        timeout=10,
    )
    first_payload = first_response.json()

    if first_payload.get("estado") != 200:
        raise AemetApiError(
            f"AEMET request failed: {first_payload.get('descripcion', 'unknown error')}"
        )

    data_url = first_payload["datos"]

    second_response = requests.get(data_url, timeout=10)
    second_response.raise_for_status()

    return second_response.json()
