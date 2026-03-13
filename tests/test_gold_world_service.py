"""Tests for services/gold_world_service.py — pure function convert_usd_oz_to_vnd_chi."""
import pytest
from config import Config
from services.gold_world_service import convert_usd_oz_to_vnd_chi

# Constants for expected math: vnd_per_chi = usd_per_oz * rate * (CHI_GRAMS / TROY_OZ_GRAMS)
TROY_OZ = Config.TROY_OZ_GRAMS   # 31.1035
CHI = Config.CHI_GRAMS            # 3.75
RATIO = CHI / TROY_OZ             # ≈ 0.12055


class TestConvertUsdOzToVndChi:
    def test_zero_price_returns_zero(self):
        assert convert_usd_oz_to_vnd_chi(0, 25_000) == 0

    def test_zero_rate_returns_zero(self):
        assert convert_usd_oz_to_vnd_chi(2_000, 0) == 0

    def test_negative_price_returns_zero(self):
        assert convert_usd_oz_to_vnd_chi(-100, 25_000) == 0

    def test_negative_rate_returns_zero(self):
        assert convert_usd_oz_to_vnd_chi(2_000, -1_000) == 0

    def test_both_zero_returns_zero(self):
        assert convert_usd_oz_to_vnd_chi(0, 0) == 0

    def test_known_value_2000_usd_25000_rate(self):
        """2000 USD/oz × 25000 VND/USD × (3.75g / 31.1035g) ≈ 6,027,xxx VND/chỉ."""
        result = convert_usd_oz_to_vnd_chi(2_000, 25_000)
        expected = round(2_000 * 25_000 * RATIO)
        assert result == expected

    def test_known_value_3000_usd_26000_rate(self):
        """Typical 2025 scenario: XAUUSD ~3000, VCB rate ~26000."""
        result = convert_usd_oz_to_vnd_chi(3_000, 26_000)
        expected = round(3_000 * 26_000 * RATIO)
        assert result == expected

    def test_result_is_integer(self):
        result = convert_usd_oz_to_vnd_chi(2_500, 25_500)
        assert isinstance(result, int)

    def test_result_is_positive_for_valid_inputs(self):
        result = convert_usd_oz_to_vnd_chi(1_800, 23_000)
        assert result > 0

    def test_higher_price_gives_higher_vnd(self):
        low = convert_usd_oz_to_vnd_chi(1_000, 25_000)
        high = convert_usd_oz_to_vnd_chi(2_000, 25_000)
        assert high > low

    def test_higher_rate_gives_higher_vnd(self):
        low_rate = convert_usd_oz_to_vnd_chi(2_000, 24_000)
        high_rate = convert_usd_oz_to_vnd_chi(2_000, 26_000)
        assert high_rate > low_rate

    def test_proportional_scaling_with_price(self):
        """Doubling USD price should double VND/chỉ result."""
        base = convert_usd_oz_to_vnd_chi(1_000, 25_000)
        doubled = convert_usd_oz_to_vnd_chi(2_000, 25_000)
        # Allow ±1 for rounding
        assert abs(doubled - 2 * base) <= 1

    def test_proportional_scaling_with_rate(self):
        """Doubling exchange rate should double VND/chỉ result."""
        base = convert_usd_oz_to_vnd_chi(2_000, 12_500)
        doubled = convert_usd_oz_to_vnd_chi(2_000, 25_000)
        assert abs(doubled - 2 * base) <= 1
