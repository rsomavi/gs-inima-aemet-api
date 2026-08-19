"""Transform Measurement objects into the challenge's output format.

Handles the field mapping requested by the challenge (nombre -> Station,
fhora -> Datetime, temp -> Temperature (ºC), etc.), the optional
filtering to 0-3 of the numeric variables (temperature, pressure, speed),
and the conversion of the output datetime to Europe/Madrid (CET/CEST),
with the UTC offset included, as required by the spec.
"""

from zoneinfo import ZoneInfo

from .models import VALID_STATIONS

MADRID_TZ = ZoneInfo("Europe/Madrid")

FIELD_TO_OUTPUT_NAME = {
    "temperature": "Temperature (ºC)",
    "pressure": "Pressure (hpa)",
    "speed": "Speed (m/s)",
}

ALL_FIELDS = tuple(FIELD_TO_OUTPUT_NAME)


def parse_requested_fields(fields_param: str | None) -> tuple[str, ...]:
    """Parse the 'fields' query param into a tuple of valid field names.

    Returns all fields if the param is missing or empty, per the
    challenge's "if zero, return all" rule.
    """
    if not fields_param:
        return ALL_FIELDS

    requested = tuple(f.strip() for f in fields_param.split(",") if f.strip())
    invalid = [f for f in requested if f not in FIELD_TO_OUTPUT_NAME]
    if invalid:
        raise ValueError(
            f"Invalid field(s): {', '.join(invalid)}. Valid options: {', '.join(ALL_FIELDS)}."
        )

    return requested


def _round(value: float | None, decimals: int = 2) -> float | None:
    """Round a numeric value for display, leaving None untouched."""
    if value is None:
        return None
    return round(value, decimals)


def serialize_measurement(measurement, fields: tuple[str, ...]) -> dict:
    """Build the output dict for one measurement, using only the requested fields."""
    madrid_datetime = measurement.timestamp.astimezone(MADRID_TZ)

    result = {
        "Station": VALID_STATIONS[measurement.station],
        "Datetime": madrid_datetime.isoformat(),
    }
    field_values = {
        "temperature": _round(measurement.temperature),
        "pressure": _round(measurement.pressure),
        "speed": _round(measurement.speed),
    }
    for field in fields:
        result[FIELD_TO_OUTPUT_NAME[field]] = field_values[field]
    return result