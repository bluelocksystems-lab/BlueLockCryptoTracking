# =============================================================================
# BlueLock Crypto Tracking V1.4 - Data Models
# =============================================================================
# Pydantic models for request body validation and response shapes.
# FastAPI uses these automatically for input parsing and OpenAPI docs.
# =============================================================================

from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional
from config import SUPPORTED_COINS, MAX_AMOUNT, MAX_NOTE_LENGTH


def _clean_note(v: str) -> str:
    """
    Shared note-sanitization for watchlist free-text fields:
    strip leading/trailing whitespace, drop control characters (which have
    no legitimate use in a short reminder note and can break rendering/CSV
    export), and enforce a max length so one entry can't bloat storage or
    the UI.
    """
    if not v:
        return ""
    cleaned = "".join(ch for ch in v if ch == "\n" or ch.isprintable())
    cleaned = cleaned.strip()
    if len(cleaned) > MAX_NOTE_LENGTH:
        raise ValueError(f"Note must be {MAX_NOTE_LENGTH} characters or fewer.")
    return cleaned


class PortfolioEntryCreate(BaseModel):
    """
    Model for adding a new purchase entry.
    symbol:         Coin ticker (e.g. "XNV")
    amount:         How many coins purchased (must be > 0)
    purchase_price: Price per coin at time of purchase (must be > 0)
    purchase_date:  Optional date string (e.g. "2026-01-15")
    """
    symbol: str
    amount: float
    purchase_price: float
    purchase_date: Optional[str] = ""

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in SUPPORTED_COINS:
            raise ValueError(
                f"Unsupported coin: {v}. Supported: {', '.join(SUPPORTED_COINS.keys())}"
            )
        return upper

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero.")
        if v > MAX_AMOUNT:
            raise ValueError(f"Amount must be <= {MAX_AMOUNT:,}")
        return v

    @field_validator("purchase_price")
    @classmethod
    def validate_purchase_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Purchase price must be greater than zero.")
        return v

    @field_validator("purchase_date")
    @classmethod
    def validate_purchase_date(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("purchase_date must be in YYYY-MM-DD format (e.g. 2026-01-15).")
        return v


class PortfolioEntryUpdate(BaseModel):
    """Model for updating an existing purchase entry."""
    amount: float
    purchase_price: float
    purchase_date: Optional[str] = ""

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero.")
        if v > MAX_AMOUNT:
            raise ValueError(f"Amount must be <= {MAX_AMOUNT:,}")
        return v

    @field_validator("purchase_price")
    @classmethod
    def validate_purchase_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Purchase price must be greater than zero.")
        return v

    @field_validator("purchase_date")
    @classmethod
    def validate_purchase_date(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("purchase_date must be in YYYY-MM-DD format (e.g. 2026-01-15).")
        return v


class FavoriteEntry(BaseModel):
    """Model for adding a coin to favorites."""
    symbol: str

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in SUPPORTED_COINS:
            raise ValueError(f"Unsupported coin symbol: {v}")
        return upper


class WatchlistEntry(BaseModel):
    """Model for adding a coin to the watchlist."""
    symbol: str
    notes: str = ""

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in SUPPORTED_COINS:
            raise ValueError(f"Unsupported coin symbol: {v}")
        return upper

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str) -> str:
        return _clean_note(v)


class WatchlistNoteUpdate(BaseModel):
    """Model for updating the note on a watched coin."""
    notes: str = ""

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str) -> str:
        return _clean_note(v)


class CalculateRequest(BaseModel):
    """Model for the price calculator endpoint."""
    symbol: str
    amount: float

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in SUPPORTED_COINS:
            raise ValueError(f"Unsupported coin symbol: {v}")
        return upper

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        if v > MAX_AMOUNT:
            raise ValueError(f"Amount must be <= {MAX_AMOUNT:,}")
        return v
