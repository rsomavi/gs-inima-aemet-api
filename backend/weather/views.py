"""API views for the weather app."""

import datetime

from rest_framework.response import Response
from rest_framework.views import APIView

from .aemet_client import AemetApiError
from .aggregation import VALID_AGGREGATIONS, aggregate_measurements
from .cache import get_observations
from .models import VALID_STATIONS
from .serializers import parse_requested_fields, serialize_measurement

AEMET_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SUTC"


class AntarcticaDataView(APIView):
    """Returns cached AEMET observations for an Antarctic station and date range.

    The location/offset parameter for interpreting input dates is
    handled in a later iteration.
    """

    def get(self, request, fecha_ini_str, fecha_fin_str, identificacion):
        if identificacion not in VALID_STATIONS:
            return Response(
                {
                    "error": (
                        f"Invalid station '{identificacion}'. "
                        f"Valid options: {', '.join(VALID_STATIONS)}."
                    )
                },
                status=400,
            )

        try:
            fields = parse_requested_fields(request.query_params.get("fields"))
        except ValueError as error:
            return Response({"error": str(error)}, status=400)

        aggregation = request.query_params.get("aggregation", "none").lower()
        if aggregation not in VALID_AGGREGATIONS:
            return Response(
                {
                    "error": (
                        f"Invalid aggregation '{aggregation}'. "
                        f"Valid options: {', '.join(VALID_AGGREGATIONS)}."
                    )
                },
                status=400,
            )

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

        aggregated = aggregate_measurements(measurements, aggregation)
        data = [serialize_measurement(m, fields) for m in aggregated]
        return Response(data)