# =============================================================================
# BlueLock Crypto Tracking V1 - Price Fetcher
# =============================================================================
# Fetches live prices from the CoinGecko public API.
# Features:
#   - 60-second in-memory cache to avoid hammering the API
#   - Timeout protection
#   - Retry logic on failure
#   - Graceful error handling (never crashes the server)
# =============================================================================

import time
import logging
import threading
import httpx
from datetime import datetime, timezone
from typing import Optional

from config import (
    SUPPORTED_COINS,
    COIN_NAMES,
    COIN_CATEGORIES,
    COINGECKO_API_BASE,
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY_SECONDS,
    CACHE_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------
# Stores the last successful price fetch so we don't hit the API every request.
_price_cache: dict = {}          # { symbol: { price, last_updated, ... } }
_cache_timestamp: float = 0.0    # Unix timestamp of last successful fetch
_api_status: str = "UNKNOWN"     # "ONLINE" | "OFFLINE" | "UNKNOWN"
_cache_lock = threading.Lock()   # Guards cache writes against concurrent requests


def _is_cache_valid() -> bool:
    """Return True if the cache is less than CACHE_DURATION_SECONDS old."""
    return (time.time() - _cache_timestamp) < CACHE_DURATION_SECONDS


def _fetch_from_coingecko() -> Optional[dict]:
    """
    Call CoinGecko's simple/price endpoint to get USD prices for all
    supported coins. Returns raw API response dict or None on failure.
    Retries up to API_MAX_RETRIES times before giving up.
    """
    global _api_status

    # Build comma-separated list of CoinGecko IDs
    coin_ids = ",".join(SUPPORTED_COINS.values())
    url = f"{COINGECKO_API_BASE}/simple/price"
    params = {
        "ids": coin_ids,
        "vs_currencies": "usd",
        "include_last_updated_at": "true",
    }

    for attempt in range(1, API_MAX_RETRIES + 2):  # +2 so we try (retries+1) times total
        try:
            logger.info("CoinGecko API request (attempt %d)...", attempt)
            with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                _api_status = "ONLINE"
                logger.info("CoinGecko API success.")
                return data

        except httpx.TimeoutException:
            logger.warning("CoinGecko API timeout on attempt %d.", attempt)
        except httpx.HTTPStatusError as e:
            logger.warning("CoinGecko API HTTP error %d on attempt %d.", e.response.status_code, attempt)
        except Exception as e:
            logger.warning("CoinGecko API unexpected error on attempt %d: %s", attempt, e)

        # Don't sleep after the last attempt
        if attempt <= API_MAX_RETRIES:
            time.sleep(API_RETRY_DELAY_SECONDS)

    _api_status = "OFFLINE"
    logger.error("CoinGecko API failed after %d attempts.", API_MAX_RETRIES + 1)
    return None


def _build_coin_data(symbol: str, gecko_data: dict) -> dict:
    """
    Build a standardized coin data dict from the raw CoinGecko response.
    Returns a dict with price=None if the coin wasn't in the response.
    """
    gecko_id = SUPPORTED_COINS[symbol]
    coin_info = gecko_data.get(gecko_id, {})

    price = coin_info.get("usd", None)
    last_updated_ts = coin_info.get("last_updated_at", None)

    # Convert Unix timestamp to human-readable UTC string
    if last_updated_ts:
        dt = datetime.fromtimestamp(last_updated_ts, tz=timezone.utc)
        last_updated_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    else:
        last_updated_str = "Unknown"

    return {
        "symbol": symbol,
        "name": COIN_NAMES.get(symbol, symbol),
        "category": COIN_CATEGORIES.get(symbol, "Other"),
        "gecko_id": gecko_id,
        "price_usd": price,
        "last_updated": last_updated_str,
    }


def refresh_prices(force: bool = False) -> bool:
    """
    Refresh the price cache if needed (or if force=True).
    Thread-safe: uses a lock to prevent duplicate concurrent fetches.
    Returns True if cache was successfully updated, False on API failure.
    """
    global _price_cache, _cache_timestamp

    # Fast path: check without lock first
    if not force and _is_cache_valid():
        logger.debug("Price cache still valid, skipping refresh.")
        return True

    with _cache_lock:
        # Re-check inside the lock in case another thread just refreshed
        if not force and _is_cache_valid():
            return True

        gecko_data = _fetch_from_coingecko()
        if gecko_data is None:
            return False  # API failed - keep existing cache data if available

        new_cache = {}
        for symbol in SUPPORTED_COINS:
            new_cache[symbol] = _build_coin_data(symbol, gecko_data)

        _price_cache = new_cache
        _cache_timestamp = time.time()
        return True


def get_all_prices() -> dict:
    """
    Return cached prices for all supported coins.
    Triggers a refresh if the cache is stale.
    Returns an empty dict if no data available at all.
    """
    refresh_prices()
    return _price_cache


def get_price(symbol: str) -> Optional[dict]:
    """
    Return cached price data for a single coin symbol.
    Returns None if symbol not found or cache is empty.
    """
    symbol = symbol.upper()
    if symbol not in SUPPORTED_COINS:
        return None

    refresh_prices()
    return _price_cache.get(symbol, None)


def get_api_status() -> str:
    """Return current API connectivity status string."""
    return _api_status


def get_cache_age_seconds() -> float:
    """Return how many seconds ago the cache was last successfully updated."""
    if _cache_timestamp == 0:
        return -1  # Never fetched
    return time.time() - _cache_timestamp
