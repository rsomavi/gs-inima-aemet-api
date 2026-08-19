"""Tests for field filtering and output formatting."""

import datetime

from django.test import TestCase

from ..models import Measurement
from ..serializers import parse_requested_fields, serialize_measurement


class ParseRequestedFieldsTests(TestCase):
    """Tests for parse_requested_fields."""

    def test_returns_all_fields_when_none(self):
        self.assertEqual(parse_requested_fields(None), ("temperature", "pressure", "speed"))

    def test_returns_all_fields_when_empty_string(self):
        self.assertEqual(parse_requested_fields(""), ("temperature", "pressure", "speed"))

    def test_returns_requested_subset(self):
        self.assertEqual(parse_requested_fields("temperature,speed"), ("temperature", "speed"))

    def test_strips_whitespace_around_fields(self):
        self.assertEqual(parse_requested_fields(" temperature , speed "), ("temperature", "speed"))

    def test_raises_value_error_for_invalid_field(self):
        with self.assertRaises(ValueError):
            parse_requested_fields("humidity")


class SerializeMeasurementTests(TestCase):
    """Tests for serialize_measurement."""

    def setUp(self):
        self.measurement = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
            temperature=2.2,
            pressure=983.3,
            speed=3.8,
        )

    def test_always_includes_station_and_datetime(self):
        result = serialize_measurement(self.measurement, ())

        self.assertEqual(result["Station"], "Meteo Station Gabriel de Castilla")
        self.assertIn("Datetime", result)

    def test_includes_only_requested_fields(self):
        result = serialize_measurement(self.measurement, ("temperature",))

        self.assertEqual(result["Temperature (ºC)"], 2.2)
        self.assertNotIn("Pressure (hpa)", result)
        self.assertNotIn("Speed (m/s)", result)

    def test_includes_all_fields_when_requested(self):
        result = serialize_measurement(self.measurement, ("temperature", "pressure", "speed"))

        self.assertEqual(result["Temperature (ºC)"], 2.2)
        self.assertEqual(result["Pressure (hpa)"], 983.3)
        self.assertEqual(result["Speed (m/s)"], 3.8)

class SerializeMeasurementTimezoneTests(TestCase):
    """Confirms Datetime output uses Europe/Madrid with the correct UTC offset,
    including around DST transitions (2026 spring/fall changes)."""

    def _measurement_at(self, utc_str):
        return Measurement(
            station="89070",
            timestamp=datetime.datetime.fromisoformat(utc_str),
            temperature=1.0,
            pressure=1.0,
            speed=1.0,
        )

    def test_winter_uses_cet_offset(self):
        measurement = self._measurement_at("2026-01-15T00:00:00+00:00")
        result = serialize_measurement(measurement, ())
        self.assertEqual(result["Datetime"], "2026-01-15T01:00:00+01:00")

    def test_summer_uses_cest_offset(self):
        measurement = self._measurement_at("2026-07-15T00:00:00+00:00")
        result = serialize_measurement(measurement, ())
        self.assertEqual(result["Datetime"], "2026-07-15T02:00:00+02:00")

    def test_just_before_spring_forward_is_cet(self):
        """01:00 UTC is the exact spring-forward instant; one minute before is still CET."""
        measurement = self._measurement_at("2026-03-29T00:59:00+00:00")
        result = serialize_measurement(measurement, ())
        self.assertEqual(result["Datetime"], "2026-03-29T01:59:00+01:00")

    def test_at_spring_forward_is_cest(self):
        """At 01:00 UTC, Madrid clocks jump from 02:00 to 03:00 (CEST begins)."""
        measurement = self._measurement_at("2026-03-29T01:00:00+00:00")
        result = serialize_measurement(measurement, ())
        self.assertEqual(result["Datetime"], "2026-03-29T03:00:00+02:00")

    def test_just_before_fall_back_is_cest(self):
        """One minute before the fall-back instant, Madrid is still on CEST."""
        measurement = self._measurement_at("2026-10-25T00:59:00+00:00")
        result = serialize_measurement(measurement, ())
        self.assertEqual(result["Datetime"], "2026-10-25T02:59:00+02:00")

    def test_at_fall_back_is_cet(self):
        """At 01:00 UTC, Madrid clocks fall back from 03:00 to 02:00 (CET begins)."""
        measurement = self._measurement_at("2026-10-25T01:00:00+00:00")
        result = serialize_measurement(measurement, ())
        self.assertEqual(result["Datetime"], "2026-10-25T02:00:00+01:00")