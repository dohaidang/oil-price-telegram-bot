"""Tests for services/gold_alert_service.py — message formatting, price resolution, symbol map."""
import pytest
from services.gold_alert_service import (
    _format_gold_alert_message,
    _resolve_price,
    VN_SYMBOL_MAP,
)


class TestVnSymbolMap:
    def test_all_brands_have_buy_key(self):
        for brand in ("SJC", "DOJI", "PNJ"):
            assert f"{brand}_BUY" in VN_SYMBOL_MAP

    def test_all_brands_have_sell_key(self):
        for brand in ("SJC", "DOJI", "PNJ"):
            assert f"{brand}_SELL" in VN_SYMBOL_MAP

    def test_map_value_structure(self):
        """Each value should be a (brand, price_type_lowercase) tuple."""
        brand, ptype = VN_SYMBOL_MAP["SJC_BUY"]
        assert brand == "SJC"
        assert ptype == "buy"

    def test_sell_maps_to_sell_lowercase(self):
        brand, ptype = VN_SYMBOL_MAP["DOJI_SELL"]
        assert brand == "DOJI"
        assert ptype == "sell"

    def test_pnj_both_directions(self):
        assert VN_SYMBOL_MAP["PNJ_BUY"] == ("PNJ", "buy")
        assert VN_SYMBOL_MAP["PNJ_SELL"] == ("PNJ", "sell")

    def test_total_entries(self):
        """3 brands × 2 types = 6 entries."""
        assert len(VN_SYMBOL_MAP) == 6


class TestFormatGoldAlertMessage:
    # ── XAUUSD (world price) ─────────────────────────────────────

    def test_xauusd_above_has_rocket(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        assert "🚀" in msg

    def test_xauusd_above_text(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        assert "VƯỢT TRÊN" in msg

    def test_xauusd_above_shows_current_price_in_usd(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        assert "$2,050.00/oz" in msg

    def test_xauusd_above_shows_target_price_in_usd(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        assert "$2,000.00/oz" in msg

    def test_xauusd_below_has_downtrend(self):
        msg = _format_gold_alert_message("XAUUSD", "below", 1_900.0, 1_850.0)
        assert "📉" in msg

    def test_xauusd_below_text(self):
        msg = _format_gold_alert_message("XAUUSD", "below", 1_900.0, 1_850.0)
        assert "GIẢM DƯỚI" in msg

    def test_xauusd_label_in_message(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        assert "XAUUSD" in msg

    # ── VN brand (SJC / DOJI / PNJ) ─────────────────────────────

    def test_vn_brand_above_uses_vnd_chi_unit(self):
        msg = _format_gold_alert_message("SJC_SELL", "above", 8_000_000, 8_100_000)
        assert "đ/chỉ" in msg

    def test_vn_brand_shows_brand_in_label(self):
        msg = _format_gold_alert_message("SJC_SELL", "above", 8_000_000, 8_100_000)
        assert "SJC" in msg

    def test_vn_brand_below_has_downtrend(self):
        msg = _format_gold_alert_message("DOJI_BUY", "below", 7_500_000, 7_400_000)
        assert "📉" in msg

    def test_vn_brand_does_not_show_usd(self):
        msg = _format_gold_alert_message("PNJ_SELL", "above", 8_000_000, 8_200_000)
        assert "$/oz" not in msg

    # ── HTML formatting ──────────────────────────────────────────

    def test_message_has_html_bold(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        assert "<b>" in msg and "</b>" in msg

    def test_message_has_timestamp(self):
        msg = _format_gold_alert_message("XAUUSD", "above", 2_000.0, 2_050.0)
        # Timestamp format: dd/mm/yyyy hh:mm
        import re
        assert re.search(r"\d{2}/\d{2}/\d{4}", msg)


class TestResolvePrice:
    # ── XAUUSD world price ───────────────────────────────────────

    async def test_xauusd_returns_world_price(self):
        world = {"XAUUSD": {"price": 2_000.5}}
        result = await _resolve_price("XAUUSD", world, {})
        assert result == 2_000.5

    async def test_xauusd_missing_price_key_returns_zero(self):
        world = {"XAUUSD": {}}
        result = await _resolve_price("XAUUSD", world, {})
        assert result == 0

    async def test_xauusd_not_in_world_dict_returns_zero(self):
        result = await _resolve_price("XAUUSD", {}, {})
        assert result == 0

    # ── VN brand prices ──────────────────────────────────────────

    async def test_sjc_sell_returns_correct_price(self):
        vn = {"SJC": {"sell": 8_250_000, "buy": 8_150_000}}
        result = await _resolve_price("SJC_SELL", {}, vn)
        assert result == 8_250_000

    async def test_sjc_buy_returns_correct_price(self):
        vn = {"SJC": {"sell": 8_250_000, "buy": 8_150_000}}
        result = await _resolve_price("SJC_BUY", {}, vn)
        assert result == 8_150_000

    async def test_doji_sell_returns_correct_price(self):
        vn = {"DOJI": {"sell": 8_200_000, "buy": 8_100_000}}
        result = await _resolve_price("DOJI_SELL", {}, vn)
        assert result == 8_200_000

    async def test_pnj_sell_returns_correct_price(self):
        vn = {"PNJ": {"sell": 8_300_000, "buy": 8_200_000}}
        result = await _resolve_price("PNJ_SELL", {}, vn)
        assert result == 8_300_000

    async def test_vn_brand_missing_from_vn_dict_returns_zero(self):
        result = await _resolve_price("SJC_BUY", {}, {})
        assert result == 0

    async def test_vn_brand_price_key_missing_returns_zero(self):
        vn = {"SJC": {}}
        result = await _resolve_price("SJC_BUY", {}, vn)
        assert result == 0

    # ── Unknown symbol ───────────────────────────────────────────

    async def test_unknown_symbol_returns_zero(self):
        world = {"XAUUSD": {"price": 2_000}}
        vn = {"SJC": {"sell": 8_000_000}}
        result = await _resolve_price("UNKNOWN_TICKER", world, vn)
        assert result == 0
