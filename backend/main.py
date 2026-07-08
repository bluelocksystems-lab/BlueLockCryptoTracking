# =============================================================================
# BlueLock Crypto Tracking V1.4 - FastAPI Backend
# =============================================================================
# Entry point for the backend server.
# Serves the frontend static files AND provides the JSON API.
#
# Start with: python main.py
# (host/port come from config.SERVER_HOST / config.SERVER_PORT)
# =============================================================================

import csv
import io
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import config
import database
import prices
import portfolio as portfolio_calc
from models import PortfolioEntryCreate, PortfolioEntryUpdate, FavoriteEntry, CalculateRequest, WatchlistEntry, WatchlistNoteUpdate

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("  %s v%s starting up...", config.APP_NAME, config.APP_VERSION)
    logger.info("=" * 60)

    database.init_db()
    logger.info("Fetching initial coin prices from CoinGecko...")
    success = prices.refresh_prices(force=True)
    if success:
        logger.info("Initial price fetch successful.")
    else:
        logger.warning("Initial price fetch failed. Will retry on first API call.")

    logger.info("Server ready at http://%s:%d", config.SERVER_HOST, config.SERVER_PORT)
    yield
    # Shutdown: nothing to clean up for now


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description=config.APP_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Basic Rate Limiting (per-IP, in-memory)
# ---------------------------------------------------------------------------
_request_log: dict[str, list[float]] = {}
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW   = 60


def check_rate_limit(request: Request) -> None:
    """Raises 429 if a client sends too many requests."""
    client_ip   = request.client.host if request.client else "unknown"
    now         = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    _request_log[client_ip] = [
        t for t in _request_log.get(client_ip, []) if t > window_start
    ]

    if len(_request_log[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    _request_log[client_ip].append(now)

    # Cleanup: remove exhausted IP keys to prevent unbounded memory growth
    if not _request_log[client_ip]:
        del _request_log[client_ip]


# ---------------------------------------------------------------------------
# Serve Frontend Static Files
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve the main HTML frontend page."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_path))


# ---------------------------------------------------------------------------
# API: Health Check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Simple health check. Returns server and API status."""
    return {
        "status":             "ok",
        "app":                config.APP_NAME,
        "version":            config.APP_VERSION,
        "api_status":         prices.get_api_status(),
        "cache_age_seconds":  round(prices.get_cache_age_seconds(), 1),
        "is_stale":           prices.is_cache_stale(),
        "server_time_utc":    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ---------------------------------------------------------------------------
# API: Prices
# ---------------------------------------------------------------------------
@app.get("/api/prices")
def get_all_prices(request: Request):
    """Return current prices for all supported coins (60s cache)."""
    check_rate_limit(request)

    all_prices = prices.get_all_prices()
    favorites  = database.get_favorites()
    symbols_with_holdings = database.get_distinct_symbols()

    result = []
    for symbol, data in all_prices.items():
        entry = dict(data)
        entry["is_favorite"]       = symbol in favorites
        entry["has_holdings"]      = symbol in symbols_with_holdings
        result.append(entry)

    result.sort(key=lambda x: (not x["is_favorite"], x["symbol"]))

    return {
        "coins":              result,
        "api_status":         prices.get_api_status(),
        "cache_age_seconds":  round(prices.get_cache_age_seconds(), 1),
        "is_stale":           prices.is_cache_stale(),
        "last_updated":       datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


@app.get("/api/prices/{symbol}")
def get_single_price(symbol: str, request: Request):
    """Return price data for a single coin by symbol."""
    check_rate_limit(request)

    symbol = symbol.upper().strip()
    if symbol not in config.SUPPORTED_COINS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported symbol '{symbol}'. Supported: {', '.join(config.SUPPORTED_COINS.keys())}"
        )

    data = prices.get_price(symbol)
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Price data unavailable. The API may be temporarily down."
        )
    return data


# ---------------------------------------------------------------------------
# API: Price Calculator
# ---------------------------------------------------------------------------
@app.post("/api/calculate")
def calculate_value(req: CalculateRequest, request: Request):
    """Calculate total USD value of a given amount of a coin."""
    check_rate_limit(request)

    data = prices.get_price(req.symbol)
    if data is None or data.get("price_usd") is None:
        raise HTTPException(
            status_code=503,
            detail=f"Price for {req.symbol} is currently unavailable."
        )

    price = data["price_usd"]
    total = price * req.amount

    return {
        "symbol":       req.symbol,
        "name":         data["name"],
        "amount":       req.amount,
        "price_usd":    price,
        "total_usd":    round(total, 2),
        "last_updated": data["last_updated"],
    }


# ---------------------------------------------------------------------------
# Helper: Build full portfolio coin stats
# ---------------------------------------------------------------------------
def _build_portfolio_coin(symbol: str, entries: list[dict]) -> dict:
    """
    Build a complete stats dict for one coin, combining DB entries with live price.
    Used by multiple endpoints.
    """
    price_data    = prices.get_price(symbol)
    current_price = price_data["price_usd"] if price_data else None

    stats = portfolio_calc.calculate_coin_stats(entries, current_price)

    return {
        "symbol":        symbol,
        "name":          config.COIN_NAMES.get(symbol, symbol),
        "category":      config.COIN_CATEGORIES.get(symbol, "Other"),
        "current_price": stats["current_price"],
        "total_amount":  stats["total_amount"],
        "average_cost":  stats["average_cost"],
        "total_cost":    stats["total_cost"],
        "current_value": stats["current_value"],
        "profit_loss":   stats["profit_loss"],
        "roi_percent":   stats["roi_percent"],
        "entry_count":   len(entries),
    }


# ---------------------------------------------------------------------------
# API: Portfolio - Summary
# ---------------------------------------------------------------------------
@app.get("/api/portfolio")
def get_portfolio(request: Request):
    """
    Return all portfolio coins with calculated stats, plus a summary card.
    GET /api/portfolio
    """
    check_rate_limit(request)

    all_symbols = database.get_distinct_symbols()

    coin_list = []
    for symbol in all_symbols:
        entries = database.get_entries_for_symbol(symbol)
        if not entries:
            continue
        coin_data = _build_portfolio_coin(symbol, entries)
        coin_list.append(coin_data)

    summary = portfolio_calc.calculate_portfolio_summary(coin_list)
    top_gainer = portfolio_calc.find_top_gainer(coin_list)
    top_loser  = portfolio_calc.find_top_loser(coin_list)

    return {
        "coins":       coin_list,
        "summary":     summary,
        "top_gainer":  top_gainer,
        "top_loser":   top_loser,
        "api_status":  prices.get_api_status(),
        "is_stale":    prices.is_cache_stale(),
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ---------------------------------------------------------------------------
# API: Portfolio - Export CSV
# ---------------------------------------------------------------------------
@app.get("/api/portfolio/export/csv")
def export_portfolio_csv(request: Request):
    """
    Export the full portfolio as a CSV file download.
    GET /api/portfolio/export/csv
    """
    check_rate_limit(request)

    all_symbols = database.get_distinct_symbols()
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Symbol", "Name", "Amount", "Average Cost (USD)",
        "Current Price (USD)", "Cost Basis (USD)",
        "Current Value (USD)", "Profit/Loss (USD)", "ROI (%)"
    ])

    for symbol in all_symbols:
        entries = database.get_entries_for_symbol(symbol)
        if not entries:
            continue
        price_data    = prices.get_price(symbol)
        current_price = price_data["price_usd"] if price_data else None
        stats         = portfolio_calc.calculate_coin_stats(entries, current_price)
        name          = config.COIN_NAMES.get(symbol, symbol)

        writer.writerow([
            symbol,
            name,
            stats["total_amount"],
            stats["average_cost"]  if stats["average_cost"]  is not None else "N/A",
            stats["current_price"] if stats["current_price"] is not None else "N/A",
            stats["total_cost"]    if stats["total_cost"]    is not None else "N/A",
            stats["current_value"] if stats["current_value"] is not None else "N/A",
            stats["profit_loss"]   if stats["profit_loss"]   is not None else "N/A",
            f"{stats['roi_percent']:.4f}" if stats["roi_percent"] is not None else "N/A",
        ])

    output.seek(0)
    filename = f"bluelock_portfolio_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ---------------------------------------------------------------------------
# API: Portfolio - Single Coin Detail
# ---------------------------------------------------------------------------
@app.get("/api/portfolio/{symbol}")
def get_portfolio_coin(symbol: str, request: Request):
    """
    Return detailed stats + full purchase history for one coin.
    GET /api/portfolio/XNV
    """
    check_rate_limit(request)

    symbol = symbol.upper().strip()
    if symbol not in config.SUPPORTED_COINS:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")

    entries = database.get_entries_for_symbol(symbol)
    if not entries:
        raise HTTPException(status_code=404, detail=f"No portfolio entries found for {symbol}")

    coin_data = _build_portfolio_coin(symbol, entries)

    # Enrich entries with cost per entry for the purchase history table
    enriched_entries = []
    for e in entries:
        enriched_entries.append({
            "id":             e["id"],
            "amount":         e["amount"],
            "purchase_price": e["purchase_price"],
            "purchase_date":  e["purchase_date"],
            "cost":           round(e["amount"] * e["purchase_price"], 8),
            "created_at":     e["created_at"],
        })

    coin_data["purchase_history"] = enriched_entries
    return coin_data


# ---------------------------------------------------------------------------
# API: Portfolio - Add Entry
# ---------------------------------------------------------------------------
@app.post("/api/portfolio")
def add_portfolio_entry(entry: PortfolioEntryCreate, request: Request):
    """
    Add a new purchase entry for a coin.
    POST /api/portfolio
    Body: { "symbol": "XNV", "amount": 100, "purchase_price": 0.005, "purchase_date": "2026-01-01" }
    """
    check_rate_limit(request)

    new_id = database.add_portfolio_entry(
        entry.symbol,
        entry.amount,
        entry.purchase_price,
        entry.purchase_date or ""
    )

    return {
        "success":        True,
        "id":             new_id,
        "symbol":         entry.symbol,
        "amount":         entry.amount,
        "purchase_price": entry.purchase_price,
        "purchase_date":  entry.purchase_date,
    }


# ---------------------------------------------------------------------------
# API: Portfolio - Update Entry
# ---------------------------------------------------------------------------
@app.put("/api/portfolio/{entry_id}")
def update_portfolio_entry(entry_id: int, entry: PortfolioEntryUpdate, request: Request):
    """
    Update an existing purchase entry by its numeric ID.
    PUT /api/portfolio/3
    """
    check_rate_limit(request)

    updated = database.update_portfolio_entry(
        entry_id,
        entry.amount,
        entry.purchase_price,
        entry.purchase_date or ""
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Entry ID {entry_id} not found.")

    return {
        "success":        True,
        "id":             entry_id,
        "amount":         entry.amount,
        "purchase_price": entry.purchase_price,
        "purchase_date":  entry.purchase_date,
    }


# ---------------------------------------------------------------------------
# API: Portfolio - Delete Entry
# ---------------------------------------------------------------------------
@app.delete("/api/portfolio/{entry_id}")
def delete_portfolio_entry(entry_id: int, request: Request):
    """
    Delete a single purchase entry by its numeric ID.
    DELETE /api/portfolio/3
    """
    check_rate_limit(request)

    deleted = database.delete_portfolio_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Entry ID {entry_id} not found.")

    return {"success": True, "id": entry_id}


# ---------------------------------------------------------------------------
# API: Portfolio - Delete ALL entries for a coin (remove asset entirely)
# ---------------------------------------------------------------------------
@app.delete("/api/portfolio/symbol/{symbol}")
def delete_portfolio_symbol(symbol: str, request: Request):
    """
    Delete every purchase entry for a given coin symbol, effectively
    removing that asset from the portfolio.
    DELETE /api/portfolio/symbol/XMR
    """
    check_rate_limit(request)

    symbol = symbol.upper().strip()
    deleted_count = database.delete_all_entries_for_symbol(symbol)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No holdings found for {symbol}.")

    return {"success": True, "symbol": symbol, "deleted_count": deleted_count}



# ---------------------------------------------------------------------------
# API: Favorites
# ---------------------------------------------------------------------------
@app.get("/api/favorites")
def get_favorites(request: Request):
    """Return list of favorited coin symbols."""
    check_rate_limit(request)
    return {"favorites": database.get_favorites()}


@app.post("/api/favorites")
def add_favorite(entry: FavoriteEntry, request: Request):
    """Add a coin to favorites."""
    check_rate_limit(request)
    database.add_favorite(entry.symbol)
    return {"success": True, "symbol": entry.symbol}


@app.delete("/api/favorites/{symbol}")
def remove_favorite(symbol: str, request: Request):
    """Remove a coin from favorites."""
    check_rate_limit(request)
    symbol = symbol.upper().strip()
    if symbol not in config.SUPPORTED_COINS:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    removed = database.remove_favorite(symbol)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{symbol} is not in favorites.")
    return {"success": True, "symbol": symbol}


# ---------------------------------------------------------------------------
# API: Watchlist
# ---------------------------------------------------------------------------
@app.get("/api/watchlist")
def get_watchlist(request: Request):
    """
    Return all watched coins with live price data attached.
    GET /api/watchlist
    """
    check_rate_limit(request)

    entries = database.get_watchlist()
    result = []
    for entry in entries:
        symbol = entry["symbol"]
        price_data = prices.get_price(symbol)
        result.append({
            "symbol":       symbol,
            "name":         config.COIN_NAMES.get(symbol, symbol),
            "category":     config.COIN_CATEGORIES.get(symbol, "Other"),
            "notes":        entry["notes"],
            "added_at":     entry["added_at"],
            "price_usd":    price_data["price_usd"] if price_data else None,
            "last_updated": price_data["last_updated"] if price_data else None,
        })

    return {"watchlist": result, "is_stale": prices.is_cache_stale()}


@app.post("/api/watchlist")
def add_to_watchlist(entry: WatchlistEntry, request: Request):
    """Add a coin to the watchlist, with an optional note."""
    check_rate_limit(request)
    database.add_to_watchlist(entry.symbol, entry.notes)
    return {"success": True, "symbol": entry.symbol, "notes": entry.notes}


@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, request: Request):
    """Remove a coin from the watchlist."""
    check_rate_limit(request)
    symbol = symbol.upper().strip()
    if symbol not in config.SUPPORTED_COINS:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    removed = database.remove_from_watchlist(symbol)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{symbol} is not on the watchlist.")
    return {"success": True, "symbol": symbol}


@app.put("/api/watchlist/{symbol}")
def update_watchlist_note(symbol: str, update: WatchlistNoteUpdate, request: Request):
    """Update the note text for a watched coin."""
    check_rate_limit(request)
    symbol = symbol.upper().strip()
    if symbol not in config.SUPPORTED_COINS:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    updated = database.update_watchlist_note(symbol, update.notes)
    if not updated:
        raise HTTPException(status_code=404, detail=f"{symbol} is not on the watchlist.")
    return {"success": True, "symbol": symbol, "notes": update.notes}


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Return clean JSON for Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid input", "details": str(exc)},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Catch-all for unexpected server errors."""
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again."},
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
# Running this file directly (rather than invoking uvicorn on the CLI with
# hardcoded flags) is what makes config.SERVER_HOST / config.SERVER_PORT
# actually control where the server binds. run.sh and run.bat both launch
# the app this way for exactly that reason - edit those two config values
# and the port-in-use check, the server bind, and the auto-opened browser
# URL all stay in sync automatically.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)
