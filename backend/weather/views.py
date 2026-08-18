"""API views for the weather app."""

from rest_framework.response import Response
from rest_framework.views import APIView

from .aemet_client import AemetApiError, fetch_antarctica_observations


class AntarcticaDataView(APIView):
    """Returns raw AEMET observations for an Antarctic station and date range.

    This is a minimal, non-aggregated version: it forwards the request
    to AEMET and returns the raw 10-minute observations as-is.
    Filtering by variable, aggregation, and timezone conversion to
    Europe/Madrid are handled in a later iteration.
    """

    def get(self, request, fecha_ini_str, fecha_fin_str, identificacion):
        try:
            observations = fetch_antarctica_observations(
                fecha_ini=fecha_ini_str,
                fecha_fin=fecha_fin_str,
                estacion=identificacion,
            )
        except AemetApiError as error:
            return Response({"error": str(error)}, status=502)

        return Response(observations)