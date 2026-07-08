# =============================================================================
# BlueLock Crypto Tracking V1.4 - Configuration
# =============================================================================
# Central configuration file for all application settings.
# Edit this file to adjust app behavior.
# =============================================================================

import os

# ---------------------------------------------------------------------------
# Application Info
# ---------------------------------------------------------------------------
APP_NAME = "BlueLock Crypto Tracking"
APP_VERSION = "1.4"
APP_DESCRIPTION = "Open-source cryptocurrency price and portfolio tracker."
APP_DISCLAIMER = (
    "This application does not provide financial advice, custody services, "
    "wallet services, or transaction functionality."
)

# ---------------------------------------------------------------------------
# Server Settings
# ---------------------------------------------------------------------------
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Path to the SQLite database file (relative to project root).
# Overridable via BLUELOCK_DB_PATH so tests can point at an isolated,
# throwaway database instead of the person's real portfolio data.
DB_PATH = os.environ.get(
    "BLUELOCK_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "portfolio.db"),
)

# ---------------------------------------------------------------------------
# Price Cache
# ---------------------------------------------------------------------------
# How long (in seconds) to cache coin prices before re-fetching
CACHE_DURATION_SECONDS = 60

# ---------------------------------------------------------------------------
# CoinGecko API Settings
# ---------------------------------------------------------------------------
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
API_TIMEOUT_SECONDS = 10      # Max seconds to wait for API response
API_MAX_RETRIES = 2           # Number of retry attempts on failure
API_RETRY_DELAY_SECONDS = 2   # Seconds to wait between retries

# ---------------------------------------------------------------------------
# Supported Coins
# ---------------------------------------------------------------------------
# Maps ticker symbol -> CoinGecko coin ID
# To add a new coin, add it here and it will automatically be supported.
SUPPORTED_COINS = {
    # --- Privacy Coins ---
    "XMR":  "monero",
    "XNV":  "nerva",
    "WOW":  "wownero",
    "ZEC":  "zcash",

    # --- Major Coins ---
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "LTC":  "litecoin",

    # --- Stablecoins ---
    "USDT": "tether",
    "USDC": "usd-coin",
    "DAI":  "dai",
    "FDUSD": "first-digital-usd",
}

# Human-readable names for each coin (used in UI display)
COIN_NAMES = {
    "XMR":  "Monero",
    "XNV":  "Nerva",
    "WOW":  "Wownero",
    "ZEC":  "Zcash",
    "BTC":  "Bitcoin",
    "ETH":  "Ethereum",
    "LTC":  "Litecoin",
    "USDT": "Tether",
    "USDC": "USD Coin",
    "DAI":  "DAI",
    "FDUSD": "First Digital USD",
}

# Category labels for each coin (used for filtering in UI)
COIN_CATEGORIES = {
    "XMR":  "Privacy",
    "XNV":  "Privacy",
    "WOW":  "Privacy",
    "ZEC":  "Privacy",
    "BTC":  "Major",
    "ETH":  "Major",
    "LTC":  "Major",
    "USDT": "Stablecoin",
    "USDC": "Stablecoin",
    "DAI":  "Stablecoin",
    "FDUSD": "Stablecoin",
}

# ---------------------------------------------------------------------------
# Input Validation Limits
# ---------------------------------------------------------------------------
MAX_AMOUNT = 1_000_000_000   # Maximum coin amount allowed in portfolio/calculator
MAX_NOTE_LENGTH = 280        # Maximum length for free-text watchlist notes

# ---------------------------------------------------------------------------
# API Failure Backoff
# ---------------------------------------------------------------------------
# After the CoinGecko API fails, how long (seconds) to skip retrying and just
# serve the last known cache instead of hammering a down API on every request.
API_FAILURE_COOLDOWN_SECONDS = 15
