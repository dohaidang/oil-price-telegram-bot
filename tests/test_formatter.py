"""Tests for utils/formatter.py — pure functions, no mocking needed."""
import pytest
from utils.formatter import (
    format_price,
    format_change,
    build_alert_message,
)


class TestFormatPrice:
    def test_typical_oil_price(self):
        assert format_price(80.50) == "$80.50"

    def test_large_price_with_comma(self):
        assert format_price(1234.56) == "$1,234.56"

    def test_zero(self):
        assert format_price(0) == "$0.00"

    def test_negative_price(self):
        assert format_price(-10.0) == "$-10.00"

    def test_rounds_to_two_decimals(self):
        assert format_price(80.999) == "$81.00"

    def test_small_decimal(self):
        assert format_price(0.05) == "$0.05"


class TestFormatChange:
    def test_positive_change_has_green_up_arrow(self):
        result = format_change(1.5, 2.0)
        assert "🟢" in result
        assert "▲" in result

    def test_positive_change_shows_plus_sign(self):
        result = format_change(1.5, 2.0)
        assert "+1.50" in result
        assert "+2.00%" in result

    def test_negative_change_has_red_down_arrow(self):
        result = format_change(-1.5, -2.0)
        assert "🔴" in result
        assert "▼" in result

    def test_negative_change_no_plus_sign(self):
        result = format_change(-1.5, -2.0)
        assert "-1.50" in result
        assert "-2.00%" in result

    def test_zero_treated_as_positive(self):
        result = format_change(0.0, 0.0)
        assert "🟢" in result
        assert "▲" in result

    def test_large_change_values(self):
        result = format_change(100.0, 5.0)
        assert "+100.00" in result
        assert "+5.00%" in result


class TestBuildAlertMessage:
    def test_above_condition_uses_rocket_emoji(self):
        msg = build_alert_message("WTI", "above", 80.0, 81.5, "WTI Crude")
        assert "🚀" in msg

    def test_above_condition_says_vuot_tren(self):
        msg = build_alert_message("WTI", "above", 80.0, 81.5, "WTI Crude")
        assert "VƯỢT TRÊN" in msg

    def test_above_shows_current_and_target_price(self):
        msg = build_alert_message("WTI", "above", 80.0, 81.5, "WTI Crude")
        assert "$81.50" in msg
        assert "$80.00" in msg

    def test_below_condition_uses_downtrend_emoji(self):
        msg = build_alert_message("BRENT", "below", 75.0, 74.0, "Brent Crude")
        assert "📉" in msg

    def test_below_condition_says_giam_duoi(self):
        msg = build_alert_message("BRENT", "below", 75.0, 74.0, "Brent Crude")
        assert "GIẢM DƯỚI" in msg

    def test_oil_name_appears_in_message(self):
        msg = build_alert_message("WTI", "above", 80.0, 85.0, "🛢️ WTI Crude")
        assert "WTI Crude" in msg

    def test_message_contains_html_bold_tag(self):
        msg = build_alert_message("WTI", "above", 80.0, 85.0, "WTI")
        assert "<b>" in msg
