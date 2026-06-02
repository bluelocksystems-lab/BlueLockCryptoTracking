# BlueLock Crypto Tracking

> Open-source cryptocurrency price and portfolio tracker.  
> Privacy-focused. Local storage only. No accounts. No ads.

---

## What It Does

BlueLock lets you track what your crypto holdings are worth right now — without spreadsheets or manual math. You enter three things:

1. **Which coin** you bought
2. **How many** you own
3. **What you paid** per coin

The app does everything else automatically:

| Calculated for you | How |
|---|---|
| Cost Basis | Amount × Purchase Price |
| Current Value | Amount × Live Market Price |
| Profit / Loss | Current Value − Cost Basis |
| ROI % | ((Current Value − Cost Basis) ÷ Cost Basis) × 100 |
| Weighted Average Cost | Total Cost Basis ÷ Total Amount |
| Portfolio Totals | Rolled up across all coins |

Prices are fetched live from CoinGecko and refreshed every 60 seconds.

---

## Features

| Feature | Description |
|---|---|
| **Portfolio Tracker** | Track holdings with full multi-purchase support and weighted average cost |
| **Live Purchase Preview** | See Cost Basis, Current Value, P&L, and ROI instantly as you fill in the form |
| **Live Prices** | Real-time prices for 11 cryptocurrencies via CoinGecko |
| **Portfolio Summary** | Total value, total cost, overall P&L, and ROI at a glance |
| **Dashboard** | Portfolio snapshot, top gainer, top loser, favorites, and API status |
| **Coin Detail View** | Full purchase history with per-entry edit and delete |
| **Export CSV** | Download your full portfolio as a spreadsheet |
| **Price Calculator** | Instantly calculate the USD value of any coin amount |
| **Favorites** | Star coins to pin them to your Dashboard |
| **Search & Filter** | Filter by name, symbol, or category (Privacy / Major / Stablecoin) |
| **Auto-Refresh** | Prices and portfolio refresh automatically every 60 seconds |
| **Dark Theme** | Cyber-style dark UI with blue accents |

---

## Supported Coins

### Privacy Coins
| Symbol | Name |
|---|---|
| XMR | Monero |
| XNV | Nerva |
| WOW | Wownero |
| ZEC | Zcash |

### Major Coins
| Symbol | Name |
|---|---|
| BTC | Bitcoin |
| ETH | Ethereum |
| LTC | Litecoin |

### Stablecoins
| Symbol | Name |
|---|---|
| USDT | Tether |
| USDC | USD Coin |
| DAI | DAI |
| FDUSD | First Digital USD |

---

## Installation

### Requirements
- **Windows 10 / 11**
- **Python 3.10 or higher** — [Download here](https://www.python.org/downloads/)
  - During install, check **"Add Python to PATH"**
- **Internet connection** (for live price data from CoinGecko)

### First Launch

1. **Download or clone** this repository:
   ```
   git clone https://github.com/YOUR_USERNAME/BlueLockCryptoTracking.git
   ```
2. Open the folder and **double-click `run.bat`**.
3. The launcher will automatically:
   - Verify Python is installed
   - Create a virtual environment (`venv/`)
   - Install all dependencies
   - Create the local database
   - Open your browser to `http://127.0.0.1:8765`

### Subsequent Launches
Double-click `run.bat` again. Setup steps are skipped once the environment exists.

### Stopping the Server
Press `Ctrl+C` in the terminal window.

---

## How to Use the Portfolio Tracker

1. Go to the **Portfolio** tab.
2. Select your coin from the dropdown.
3. Enter **Amount Owned** and **Purchase Price Per Coin (USD)**.
4. Optionally set a purchase date.
5. A **live preview** appears showing your Cost Basis, Current Value, P&L, and ROI — calculated automatically.
6. Click **Add Purchase**.

To record multiple purchases of the same coin (dollar-cost averaging), just add them one at a time. The app calculates your weighted average cost and total P&L automatically.

---

## Project Structure

```
BlueLockCryptoTracking/
│
├── backend/
│   ├── main.py          # FastAPI server & all API endpoints
│   ├── config.py        # Supported coins, settings, constants
│   ├── database.py      # SQLite database operations
│   ├── prices.py        # CoinGecko API integration & 60s cache
│   ├── portfolio.py     # Calculation engine (cost basis, ROI, etc.)
│   ├── models.py        # Pydantic request validation models
│   └── requirements.txt # Python dependencies
│
├── frontend/
│   ├── index.html       # Single-page application HTML
│   ├── style.css        # Dark cyber theme stylesheet
│   └── app.js           # All frontend JavaScript
│
├── data/
│   └── portfolio.db     # SQLite database (auto-created, gitignored)
│
├── run.bat              # Windows one-click launcher
├── CHANGELOG.md         # Version history
├── CONTRIBUTING.md      # How to contribute
├── README.md            # This file
├── LICENSE              # MIT License
└── .gitignore
```

---

## API Reference

All endpoints served at `http://127.0.0.1:8765`:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Server and API health check |
| GET | `/api/prices` | All coin prices (60s cache) |
| GET | `/api/prices/{symbol}` | Single coin price |
| POST | `/api/calculate` | Calculate USD value of an amount |
| GET | `/api/portfolio` | All holdings with calculated stats |
| POST | `/api/portfolio` | Add a purchase entry |
| PUT | `/api/portfolio/{id}` | Update a purchase entry |
| DELETE | `/api/portfolio/{id}` | Delete a purchase entry |
| GET | `/api/portfolio/{symbol}` | Coin detail + purchase history |
| GET | `/api/portfolio/export/csv` | Download portfolio as CSV |
| GET | `/api/favorites` | Get favorited symbols |
| POST | `/api/favorites` | Add a coin to favorites |
| DELETE | `/api/favorites/{symbol}` | Remove from favorites |

---

## Troubleshooting

**"Python is not installed or not in PATH"**
Install Python from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during setup. Then open a new terminal and run `python --version` to confirm.

**"Price data unavailable" / API Offline**
CoinGecko's free API has rate limits. Wait 60 seconds and click Refresh. If the problem persists, CoinGecko may have a temporary outage.

**Browser doesn't open automatically**
Navigate manually to `http://127.0.0.1:8765`.

**Port already in use**
Edit `run.bat` and `backend/config.py` to change `8765` to a different port (e.g. `8766`).

**Resetting the database**
Stop the server, delete `data/portfolio.db`, and restart. A fresh database is created automatically.

---

## Privacy & Security

**BlueLock collects zero data.**

- All portfolio and favorites data is stored locally in `data/portfolio.db` — never transmitted anywhere
- The only external connection is to CoinGecko's public read-only price API
- No analytics, no telemetry, no accounts, no cookies
- Server only listens on `127.0.0.1` — not accessible from other devices on your network
- No private keys, no seed phrases, no wallet connections, no transaction functionality
- All SQL queries are parameterized (no SQL injection)
- All user inputs are validated and HTML-escaped

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add coins, fix bugs, or suggest features.

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

---

## Disclaimer

This application does not provide financial advice, custody services, wallet services, or transaction functionality. Cryptocurrency prices are volatile. Always do your own research.
