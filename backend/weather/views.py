"""API views for the weather app."""

import datetime
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from .aemet_client import AemetApiError
from .aggregation import VALID_AGGREGATIONS, aggregate_measurements
from .cache import get_observations
from .models import VALID_STATIONS
from .serializers import parse_requested_fields, serialize_measurement
from .timezones import resolve_input_timezone

logger = logging.getLogger("weather")

INPUT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class AntarcticaDataView(APIView):
    """Returns cached AEMET observations for an Antarctic station and date range."""

    def get(self, request, fecha_ini_str, fecha_fin_str, identificacion):
        logger.info(
            "Request received: station=%s, fechaini=%s, fechafin=%s, params=%s",
            identificacion, fecha_ini_str, fecha_fin_str, dict(request.query_params),
        )

        if identificacion not in VALID_STATIONS:
            logger.warning("Rejected: invalid station '%s'", identificacion)
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
            logger.warning("Rejected: invalid fields param (%s)", error)
            return Response({"error": str(error)}, status=400)

        aggregation = request.query_params.get("aggregation", "none").lower()
        if aggregation not in VALID_AGGREGATIONS:
            logger.warning("Rejected: invalid aggregation '%s'", aggregation)
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
            input_tz = resolve_input_timezone(request.query_params.get("location"))
        except ValueError as error:
            logger.warning("Rejected: invalid location param (%s)", error)
            return Response({"error": str(error)}, status=400)

        try:
            start_naive = datetime.datetime.strptime(fecha_ini_str, INPUT_DATETIME_FORMAT)
            end_naive = datetime.datetime.strptime(fecha_fin_str, INPUT_DATETIME_FORMAT)
        except ValueError:
            logger.warning("Rejected: malformed date (fechaini=%s, fechafin=%s)", fecha_ini_str, fecha_fin_str)
            return Response(
                {"error": "Dates must use the format AAAA-MM-DDTHH:MM:SS."}, status=400
            )

        start = start_naive.replace(tzinfo=input_tz).astimezone(datetime.timezone.utc)
        end = end_naive.replace(tzinfo=input_tz).astimezone(datetime.timezone.utc)

        if start > end:
            logger.warning("Rejected: fechaini (%s) after fechafin (%s)", start, end)
            return Response(
                {"error": "fechaini must not be after fechafin."}, status=400
            )

        try:
            measurements = get_observations(identificacion, start, end)
        except AemetApiError as error:
            logger.error("AEMET fetch failed for station=%s: %s", identificacion, error)
            return Response({"error": str(error)}, status=502)

        aggregated = aggregate_measurements(measurements, aggregation)
        data = [serialize_measurement(m, fields) for m in aggregated]
        return Response(data)