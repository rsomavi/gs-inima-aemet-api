"""Tests for resolving the optional 'location' parameter."""

import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from ..timezones import resolve_input_timezone


class ResolveInputTimezoneTests(TestCase):
    """Tests for resolve_input_timezone."""

    def test_defaults_to_utc_when_missing(self):
        self.assertEqual(resolve_input_timezone(None), datetime.timezone.utc)

    def test_defaults_to_utc_when_empty_string(self):
        self.assertEqual(resolve_input_timezone(""), datetime.timezone.utc)

    def test_resolves_named_iana_timezone(self):
        self.assertEqual(resolve_input_timezone("Europe/Berlin"), ZoneInfo("Europe/Berlin"))

    def test_resolves_positive_offset(self):
        result = resolve_input_timezone("+02:00")

        self.assertEqual(result.utcoffset(None), datetime.timedelta(hours=2))

    def test_resolves_negative_offset(self):
        result = resolve_input_timezone("-05:30")

        self.assertEqual(result.utcoffset(None), datetime.timedelta(hours=-5, minutes=-30))

    def test_raises_value_error_for_unknown_timezone_name(self):
        with self.assertRaises(ValueError):
            resolve_input_timezone("Europe/Atlantida")

    def test_raises_value_error_for_malformed_offset(self):
        with self.assertRaises(ValueError):
            resolve_input_timezone("+2")