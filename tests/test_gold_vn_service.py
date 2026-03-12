"""Tests for services/gold_vn_service.py — pure functions _parse_price and _normalize_to_chi."""
import pytest
from services.gold_vn_service import _parse_price, _normalize_to_chi, LUONG_TO_CHI


class TestParsePrice:
    # ── Normal formats ──────────────────────────────────────────

    def test_dot_thousands_separator(self):
        """Vietnamese web format: '8.250' = 8250."""
        assert _parse_price("8.250") == 8250

    def test_comma_thousands_separator(self):
        """Alternate format: '8,250' = 8250."""
        assert _parse_price("8,250") == 8250

    def test_plain_integer(self):
        assert _parse_price("8250") == 8250

    def test_large_price_multi_separator(self):
        """'82.500.000' = 82500000 (VND/lượng typical)."""
        assert _parse_price("82.500.000") == 82500000

    def test_large_price_comma_multi(self):
        assert _parse_price("82,500,000") == 82500000

    # ── Currency symbols stripped ────────────────────────────────

    def test_strips_dong_lowercase(self):
        assert _parse_price("8.250đ") == 8250

    def test_strips_dong_unicode(self):
        assert _parse_price("8.250₫") == 8250

    def test_strips_vnd_label(self):
        assert _parse_price("8.250 VNĐ") == 8250

    def test_strips_leading_trailing_spaces(self):
        assert _parse_price("  8.250  ") == 8250

    # ── Edge / error cases ──────────────────────────────────────

    def test_empty_string_returns_zero(self):
        assert _parse_price("") == 0

    def test_invalid_text_returns_zero(self):
        assert _parse_price("N/A") == 0

    def test_dash_returns_zero(self):
        assert _parse_price("-") == 0

    def test_text_with_no_digits_returns_zero(self):
        assert _parse_price("Đang cập nhật") == 0


class TestNormalizeToChi:
    # ── Zero / negative guard ────────────────────────────────────

    def test_zero_returns_zero(self):
        assert _normalize_to_chi(0) == 0

    def test_negative_returns_zero(self):
        assert _normalize_to_chi(-100) == 0

    # ── Unit hint "chỉ" → pass-through ─────────────────────────

    def test_chi_hint_returns_as_is(self):
        """If unit explicitly says chỉ, return price unchanged."""
        assert _normalize_to_chi(8_250_000, "VND/chỉ") == 8_250_000

    def test_chi_hint_lowercase(self):
        assert _normalize_to_chi(5_000_000, "chỉ") == 5_000_000

    # ── Prices in thousands (< 100,000) → × 1000 ÷ 10 ──────────

    def test_price_in_thousands_sjc_typical(self):
        """
        SJC table sometimes shows '8250' meaning 8,250,000 VND/lượng.
        8250 * 1000 = 8,250,000 per lượng → / 10 = 825,000 per chỉ.
        """
        result = _normalize_to_chi(8_250)
        assert result == 825_000

    # ── Prices in ten-thousands (< 1,000,000) → × 1000 ÷ 10 ────

    def test_price_in_tens_of_thousands(self):
        """
        82500 * 1000 = 82,500,000 per lượng → / 10 = 8,250,000 per chỉ.
        """
        result = _normalize_to_chi(82_500)
        assert result == 8_250_000

    # ── Prices already in VND/lượng (≥ 1,000,000) → ÷ 10 ───────

    def test_price_per_luong_full(self):
        """82,500,000 VND/lượng → / 10 = 8,250,000 VND/chỉ."""
        result = _normalize_to_chi(82_500_000)
        assert result == 8_250_000

    def test_price_per_luong_sjc_realistic(self):
        """Realistic SJC price ~120,000,000 VND/lượng → / 10 = 12,000,000/chỉ."""
        result = _normalize_to_chi(120_000_000)
        assert result == 12_000_000

    # ── LUONG_TO_CHI constant ────────────────────────────────────

    def test_luong_to_chi_is_ten(self):
        """1 lượng = 10 chỉ."""
        assert LUONG_TO_CHI == 10
