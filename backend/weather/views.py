"""API views for the weather app."""

import datetime

from rest_framework.response import Response
from rest_framework.views import APIView

from .aemet_client import AemetApiError
from .cache import get_observations

AEMET_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SUTC"


class AntarcticaDataView(APIView):
    """Returns cached AEMET observations for an Antarctic station and date range.

    Missing data is fetched from AEMET on demand and stored locally.
    Filtering by variable, aggregation, and timezone conversion to
    Europe/Madrid are handled in a later iteration.
    """

    def get(self, request, fecha_ini_str, fecha_fin_str, identificacion):
        try:
            start = datetime.datetime.strptime(fecha_ini_str, AEMET_DATETIME_FORMAT).replace(
                tzinfo=datetime.timezone.utc
            )
            end = datetime.datetime.strptime(fecha_fin_str, AEMET_DATETIME_FORMAT).replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            return Response(
                {"error": "Dates must use the format AAAA-MM-DDTHH:MM:SSUTC."}, status=400
            )

        try:
            measurements = get_observations(identificacion, start, end)
        except AemetApiError as error:
            return Response({"error": str(error)}, status=502)

        data = [
            {
                "station": measurement.station,
                "fhora": measurement.timestamp.isoformat(),
                "temp": measurement.temperature,
                "pres": measurement.pressure,
                "vel": measurement.speed,
            }
            for measurement in measurements
        ]
        return Response(data)