# =============================================================================
# BlueLock Crypto Tracking — Unit Tests: Portfolio Calculation Engine
# =============================================================================
# Run with: pytest tests/ -v
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from portfolio import (
    calculate_coin_stats,
    calculate_portfolio_summary,
    find_top_gainer,
    find_top_loser,
)


# ---------------------------------------------------------------------------
# calculate_coin_stats
# ---------------------------------------------------------------------------

class TestCalculateCoinStats:

    def test_single_entry_profit(self):
        entries = [{"amount": 10.0, "purchase_price": 100.0}]
        result = calculate_coin_stats(entries, current_price=150.0)
        assert result["total_amount"] == 10.0
        assert result["total_cost"] == 1000.0
        assert result["average_cost"] == 100.0
        assert result["current_value"] == 1500.0
        assert result["profit_loss"] == 500.0
        assert result["roi_percent"] == 50.0

    def test_single_entry_loss(self):
        entries = [{"amount": 5.0, "purchase_price": 200.0}]
        result = calculate_coin_stats(entries, current_price=100.0)
        assert result["profit_loss"] == -500.0
        assert result["roi_percent"] == -50.0

    def test_dca_weighted_average(self):
        entries = [
            {"amount": 10.0, "purchase_price": 100.0},
            {"amount": 10.0, "purchase_price": 200.0},
        ]
        result = calculate_coin_stats(entries, current_price=150.0)
        assert result["total_amount"] == 20.0
        assert result["total_cost"] == 3000.0
        assert result["average_cost"] == 150.0
        assert result["profit_loss"] == 0.0

    def test_dca_unequal_amounts(self):
        entries = [
            {"amount": 1.0,  "purchase_price": 100.0},
            {"amount": 9.0,  "purchase_price": 200.0},
        ]
        result = calculate_coin_stats(entries, current_price=200.0)
        assert result["total_cost"] == 1900.0
        assert result["average_cost"] == 190.0

    def test_no_price_available(self):
        entries = [{"amount": 5.0, "purchase_price": 50.0}]
        result = calculate_coin_stats(entries, current_price=None)
        assert result["current_value"] is None
        assert result["profit_loss"] is None
        assert result["roi_percent"] is None
        assert result["total_cost"] == 250.0
        assert result["total_amount"] == 5.0

    def test_empty_entries(self):
        result = calculate_coin_stats([], current_price=100.0)
        assert result["total_amount"] == 0.0
        assert result["total_cost"] == 0.0
        assert result["current_value"] is None
        assert result["profit_loss"] is None
        assert result["roi_percent"] is None

    def test_zero_roi_at_cost_price(self):
        entries = [{"amount": 10.0, "purchase_price": 50.0}]
        result = calculate_coin_stats(entries, current_price=50.0)
        assert result["profit_loss"] == 0.0
        assert result["roi_percent"] == 0.0

    def test_micro_coin_precision(self):
        """Small coin amounts should not lose precision."""
        entries = [{"amount": 0.00000001, "purchase_price": 0.000001}]
        result = calculate_coin_stats(entries, current_price=0.000002)
        assert result["total_amount"] == 0.00000001
        assert result["profit_loss"] is not None

    def test_large_amounts(self):
        entries = [{"amount": 1_000_000.0, "purchase_price": 0.001}]
        result = calculate_coin_stats(entries, current_price=0.002)
        assert result["total_cost"] == 1000.0
        assert result["current_value"] == 2000.0
        assert result["roi_percent"] == 100.0


# ---------------------------------------------------------------------------
# calculate_portfolio_summary
# ---------------------------------------------------------------------------

class TestCalculatePortfolioSummary:

    def _make_coin(self, symbol, total_cost, current_value, profit_loss, roi):
        return {
            "symbol": symbol,
            "total_cost": total_cost,
            "current_value": current_value,
            "profit_loss": profit_loss,
            "roi_percent": roi,
        }

    def test_basic_summary(self):
        coins = [
            self._make_coin("BTC", 1000.0, 1500.0, 500.0, 50.0),
            self._make_coin("ETH", 500.0,  400.0, -100.0, -20.0),
        ]
        result = calculate_portfolio_summary(coins)
        assert result["total_value"] == 1900.0
        assert result["total_cost"] == 1500.0
        assert result["total_profit_loss"] == 400.0
        assert abs(result["overall_roi"] - 26.6667) < 0.01

    def test_empty_portfolio(self):
        result = calculate_portfolio_summary([])
        assert result["total_value"] == 0.0
        assert result["total_cost"] == 0.0
        assert result["total_profit_loss"] is None
        assert result["overall_roi"] is None

    def test_all_prices_unavailable(self):
        coins = [
            {**self._make_coin("XNV", 100.0, None, None, None)},
        ]
        result = calculate_portfolio_summary(coins)
        assert result["total_profit_loss"] is None
        assert result["overall_roi"] is None


# ---------------------------------------------------------------------------
# find_top_gainer / find_top_loser
# ---------------------------------------------------------------------------

class TestTopGainerLoser:

    def _coins(self):
        return [
            {"symbol": "BTC", "roi_percent": 50.0},
            {"symbol": "ETH", "roi_percent": -20.0},
            {"symbol": "XMR", "roi_percent": 120.0},
        ]

    def test_top_gainer(self):
        result = find_top_gainer(self._coins())
        assert result["symbol"] == "XMR"

    def test_top_loser(self):
        result = find_top_loser(self._coins())
        assert result["symbol"] == "ETH"

    def test_empty_list(self):
        assert find_top_gainer([]) is None
        assert find_top_loser([]) is None

    def test_no_roi_data(self):
        coins = [{"symbol": "XNV", "roi_percent": None}]
        assert find_top_gainer(coins) is None
        assert find_top_loser(coins) is None
