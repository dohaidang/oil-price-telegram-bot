"""Tests for config.py — gold configuration constants and structure."""
import pytest
from config import Config
from services.gold_vn_service import LUONG_TO_CHI


class TestGoldWorldConfig:
    def test_xauusd_in_tickers(self):
        assert "XAUUSD" in Config.GOLD_WORLD_TICKERS

    def test_xauusd_ticker_symbol(self):
        assert Config.GOLD_WORLD_TICKERS["XAUUSD"] == "XAUUSD=X"

    def test_world_names_match_tickers(self):
        for key in Config.GOLD_WORLD_TICKERS:
            assert key in Config.GOLD_WORLD_NAMES, f"Missing display name for {key}"

    def test_world_units_match_tickers(self):
        for key in Config.GOLD_WORLD_TICKERS:
            assert key in Config.GOLD_WORLD_UNITS, f"Missing unit for {key}"

    def test_xauusd_unit_is_usd_oz(self):
        assert Config.GOLD_WORLD_UNITS["XAUUSD"] == "USD/oz"


class TestGoldVnConfig:
    def test_vn_brands_not_empty(self):
        assert len(Config.GOLD_VN_BRANDS) > 0

    def test_sjc_in_brands(self):
        assert "SJC" in Config.GOLD_VN_BRANDS

    def test_doji_in_brands(self):
        assert "DOJI" in Config.GOLD_VN_BRANDS

    def test_pnj_in_brands(self):
        assert "PNJ" in Config.GOLD_VN_BRANDS

    def test_all_brands_have_source_url(self):
        for brand in Config.GOLD_VN_BRANDS:
            assert brand in Config.GOLD_VN_SOURCES, f"Missing source URL for {brand}"
            assert Config.GOLD_VN_SOURCES[brand].startswith("http"), \
                f"Source URL for {brand} must start with http"

    def test_snapshot_interval_positive(self):
        assert Config.GOLD_VN_SNAPSHOT_INTERVAL > 0


class TestConversionConstants:
    def test_troy_oz_grams_correct(self):
        """1 troy oz = 31.1035 g (LBMA standard)."""
        assert Config.TROY_OZ_GRAMS == pytest.approx(31.1035)

    def test_chi_grams_correct(self):
        """1 chỉ = 3.75 g (Vietnamese standard)."""
        assert Config.CHI_GRAMS == pytest.approx(3.75)

    def test_luong_to_chi_is_ten(self):
        """1 lượng = 10 chỉ."""
        assert LUONG_TO_CHI == 10

    def test_chi_to_troy_ratio_in_range(self):
        """3.75 / 31.1035 ≈ 0.1206 (sanity check)."""
        ratio = Config.CHI_GRAMS / Config.TROY_OZ_GRAMS
        assert 0.11 < ratio < 0.13

    def test_ten_chi_equals_one_luong_in_grams(self):
        """10 chỉ × 3.75g = 37.5g = 1 lượng."""
        luong_in_grams = LUONG_TO_CHI * Config.CHI_GRAMS
        assert luong_in_grams == pytest.approx(37.5)


class TestOilConfig:
    def test_oil_tickers_not_empty(self):
        assert len(Config.OIL_TICKERS) > 0

    def test_wti_ticker_symbol(self):
        assert Config.OIL_TICKERS.get("WTI") == "CL=F"

    def test_brent_ticker_symbol(self):
        assert Config.OIL_TICKERS.get("BRENT") == "BZ=F"

    def test_oil_names_match_tickers(self):
        for key in Config.OIL_TICKERS:
            assert key in Config.OIL_NAMES, f"Missing oil name for {key}"

    def test_update_interval_positive(self):
        assert Config.UPDATE_INTERVAL > 0
