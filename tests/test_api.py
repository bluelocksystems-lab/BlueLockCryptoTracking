# =============================================================================
# BlueLock Crypto Tracking — API Tests: Watchlist & Delete Holdings
# =============================================================================
# Covers the two feature sets shipped in 1.4 update 1 that had zero test
# coverage: the Watchlist endpoints and the Delete Holdings (single +
# delete-all-for-symbol) endpoints.
#
# Each test gets its own throwaway SQLite file (via monkeypatch on
# database.DB_PATH) and a mocked price cache (no real network calls), so the
# suite is fast, deterministic, and safe to run in CI with no internet
# access to CoinGecko.
#
# Run with: pytest tests/ -v
# =============================================================================

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

import database
import prices
import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Spin up the FastAPI app against an isolated, empty SQLite database, with
    the CoinGecko price fetch replaced by a deterministic fake so tests never
    touch the network and never flake on live market data.
    """
    db_path = str(tmp_path / "test_portfolio.db")
    monkeypatch.setattr(database, "DB_PATH", db_path)

    def fake_refresh(force: bool = False) -> bool:
        prices._price_cache = {
            symbol: {
                "symbol": symbol,
                "name": prices.COIN_NAMES.get(symbol, symbol),
                "category": prices.COIN_CATEGORIES.get(symbol, "Other"),
                "gecko_id": gecko_id,
                "price_usd": 100.0,
                "last_updated": "2026-01-01 00:00 UTC",
            }
            for symbol, gecko_id in prices.SUPPORTED_COINS.items()
        }
        prices._cache_timestamp = time.time()
        prices._api_status = "ONLINE"
        return True

    monkeypatch.setattr(prices, "refresh_prices", fake_refresh)

    with TestClient(main.app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Watchlist endpoints
# ---------------------------------------------------------------------------
class TestWatchlistEndpoints:

    def test_empty_watchlist(self, client):
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        body = resp.json()
        assert body["watchlist"] == []
        assert "is_stale" in body

    def test_add_and_get(self, client):
        resp = client.post("/api/watchlist", json={"symbol": "xmr", "notes": "buy dip"})
        assert resp.status_code == 200
        assert resp.json()["symbol"] == "XMR"

        resp = client.get("/api/watchlist")
        items = resp.json()["watchlist"]
        assert len(items) == 1
        assert items[0]["symbol"] == "XMR"
        assert items[0]["notes"] == "buy dip"
        assert items[0]["price_usd"] == 100.0

    def test_note_is_trimmed_and_sanitized(self, client):
        resp = client.post("/api/watchlist", json={"symbol": "btc", "notes": "  hello\x07world  "})
        assert resp.status_code == 200
        assert resp.json()["notes"] == "helloworld"

    def test_note_too_long_rejected(self, client):
        resp = client.post("/api/watchlist", json={"symbol": "eth", "notes": "x" * 281})
        assert resp.status_code == 422

    def test_unsupported_symbol_rejected(self, client):
        resp = client.post("/api/watchlist", json={"symbol": "DOGE", "notes": ""})
        assert resp.status_code == 422

    def test_update_note(self, client):
        client.post("/api/watchlist", json={"symbol": "ltc", "notes": "old note"})
        resp = client.put("/api/watchlist/LTC", json={"notes": "new note"})
        assert resp.status_code == 200
        assert resp.json()["notes"] == "new note"

        items = client.get("/api/watchlist").json()["watchlist"]
        assert items[0]["notes"] == "new note"

    def test_update_note_unknown_symbol_404(self, client):
        resp = client.put("/api/watchlist/ZEC", json={"notes": "n/a"})
        assert resp.status_code == 404

    def test_remove_from_watchlist(self, client):
        client.post("/api/watchlist", json={"symbol": "zec", "notes": ""})
        resp = client.delete("/api/watchlist/ZEC")
        assert resp.status_code == 200
        assert client.get("/api/watchlist").json()["watchlist"] == []

    def test_remove_twice_returns_404(self, client):
        client.post("/api/watchlist", json={"symbol": "wow", "notes": ""})
        client.delete("/api/watchlist/WOW")
        resp = client.delete("/api/watchlist/WOW")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete Holdings endpoints
# ---------------------------------------------------------------------------
class TestDeleteHoldingsEndpoints:

    def _add_entry(self, client, symbol="XMR", amount=10.0, price=50.0):
        resp = client.post("/api/portfolio", json={
            "symbol": symbol,
            "amount": amount,
            "purchase_price": price,
            "purchase_date": "2026-01-01",
        })
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_delete_single_entry(self, client):
        entry_id = self._add_entry(client)
        resp = client.delete(f"/api/portfolio/{entry_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Deleting the same ID again should 404, not silently succeed
        resp = client.delete(f"/api/portfolio/{entry_id}")
        assert resp.status_code == 404

    def test_delete_all_entries_for_symbol(self, client):
        self._add_entry(client, symbol="XMR", amount=5.0)
        self._add_entry(client, symbol="XMR", amount=7.0)

        detail = client.get("/api/portfolio/XMR")
        assert detail.status_code == 200
        assert detail.json()["entry_count"] == 2

        resp = client.delete("/api/portfolio/symbol/XMR")
        assert resp.status_code == 200
        body = resp.json()
        assert body["symbol"] == "XMR"
        assert body["deleted_count"] == 2

        # Coin should now be entirely gone from the portfolio
        resp = client.get("/api/portfolio/XMR")
        assert resp.status_code == 404

    def test_delete_all_for_symbol_with_no_holdings_404s(self, client):
        resp = client.delete("/api/portfolio/symbol/BTC")
        assert resp.status_code == 404

    def test_bulk_delete_is_independent_per_symbol(self, client):
        """
        The frontend's multi-select bulk delete loops this same endpoint
        per selected symbol - confirm deleting one symbol's holdings never
        touches another symbol's entries.
        """
        self._add_entry(client, symbol="XMR", amount=1.0)
        self._add_entry(client, symbol="ETH", amount=2.0)

        client.delete("/api/portfolio/symbol/XMR")

        assert client.get("/api/portfolio/XMR").status_code == 404
        assert client.get("/api/portfolio/ETH").status_code == 200
