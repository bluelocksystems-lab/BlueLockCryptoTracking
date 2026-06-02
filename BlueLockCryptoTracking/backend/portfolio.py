# =============================================================================
# BlueLock Crypto Tracking V1 - Portfolio Calculation Engine
# =============================================================================
# Pure calculation logic: weighted average cost, P&L, ROI.
# No database calls here - receives data, returns computed results.
# This keeps the math easy to test and verify independently.
# =============================================================================

from typing import Optional


def calculate_coin_stats(entries: list[dict], current_price: Optional[float]) -> dict:
    """
    Given a list of purchase entries for one coin and its current price,
    compute all portfolio statistics.

    entries: list of dicts with keys: amount, purchase_price
    current_price: live price in USD, or None if unavailable

    Returns a dict with all calculated fields.
    """

    # --- Guard: empty entries ---
    if not entries:
        return {
            "total_amount":    0.0,
            "total_cost":      0.0,
            "average_cost":    0.0,
            "current_price":   current_price,
            "current_value":   None,
            "profit_loss":     None,
            "roi_percent":     None,
        }

    # --- Step 1: Total amount owned (sum of all purchase amounts) ---
    total_amount = sum(e["amount"] for e in entries)

    # --- Step 2: Total cost basis (sum of amount × purchase_price for each entry) ---
    total_cost = sum(e["amount"] * e["purchase_price"] for e in entries)

    # --- Step 3: Weighted average cost per coin ---
    # Protect against division by zero (shouldn't happen with valid entries)
    if total_amount > 0:
        average_cost = total_cost / total_amount
    else:
        average_cost = 0.0

    # --- Step 4: Current value, P&L, ROI (only if price is available) ---
    if current_price is not None:
        current_value = current_price * total_amount
        profit_loss   = current_value - total_cost

        # Protect against division by zero cost basis
        if total_cost > 0:
            roi_percent = ((current_value - total_cost) / total_cost) * 100
        else:
            roi_percent = 0.0
    else:
        current_value = None
        profit_loss   = None
        roi_percent   = None

    return {
        "total_amount":  round(total_amount, 8),   # Support micro-coins
        "total_cost":    round(total_cost, 8),
        "average_cost":  round(average_cost, 8),
        "current_price": current_price,
        "current_value": round(current_value, 2) if current_value is not None else None,
        "profit_loss":   round(profit_loss, 2)   if profit_loss   is not None else None,
        "roi_percent":   round(roi_percent, 4)   if roi_percent   is not None else None,
    }


def calculate_portfolio_summary(coin_stats: list[dict]) -> dict:
    """
    Roll up per-coin stats into a total portfolio summary card.
    coin_stats: list of calculate_coin_stats() results (with symbol included)

    Returns total_value, total_cost, total_profit_loss, overall_roi_percent.
    """
    total_value  = 0.0
    total_cost   = 0.0
    has_any_price = False

    for coin in coin_stats:
        # Only include coins where we have a live price
        if coin.get("current_value") is not None:
            total_value  += coin["current_value"]
            total_cost   += coin["total_cost"]
            has_any_price = True
        elif coin.get("total_cost") is not None:
            # Still add cost basis even if no price
            total_cost += coin["total_cost"]

    if has_any_price and total_cost > 0:
        total_profit_loss  = total_value - total_cost
        overall_roi        = ((total_value - total_cost) / total_cost) * 100
    else:
        total_profit_loss  = None
        overall_roi        = None

    return {
        "total_value":       round(total_value, 2),
        "total_cost":        round(total_cost, 2),
        "total_profit_loss": round(total_profit_loss, 2) if total_profit_loss is not None else None,
        "overall_roi":       round(overall_roi, 4)        if overall_roi        is not None else None,
    }


def find_top_gainer(coin_stats: list[dict]) -> Optional[dict]:
    """Return the coin with the highest ROI %, or None if no data."""
    eligible = [c for c in coin_stats if c.get("roi_percent") is not None]
    if not eligible:
        return None
    return max(eligible, key=lambda c: c["roi_percent"])


def find_top_loser(coin_stats: list[dict]) -> Optional[dict]:
    """Return the coin with the lowest ROI %, or None if no data."""
    eligible = [c for c in coin_stats if c.get("roi_percent") is not None]
    if not eligible:
        return None
    return min(eligible, key=lambda c: c["roi_percent"])
