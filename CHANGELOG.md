# Changelog

All notable changes to BlueLock Crypto Tracking are documented here.

---

## [1.4] — update 3 of 3 (unreleased)

### Fixed
- **`config.py`'s `SERVER_PORT`/`SERVER_HOST` now actually control the server** — previously they were log-line decoration only; the real bind address was hardcoded as `--host 127.0.0.1 --port 8765` in `run.sh`/`run.bat`'s `uvicorn` command, so editing config.py silently did nothing. Added a `if __name__ == "__main__"` entry point to `main.py` that calls `uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)`, and switched both launch scripts to run `python main.py` instead of invoking `uvicorn` directly with hardcoded flags. `run.sh`/`run.bat` now read the host/port from `config.py` themselves too, so the port-in-use check, the server bind, and the auto-opened browser URL can't drift out of sync with each other again.
  - Verified live: ran the server via `python main.py` on the default port, then again after changing `SERVER_PORT` to `8877` in `config.py` - confirmed the server bound to `8877`, `8765` was correctly unbound, and reverted the change afterward.

### QC / Consistency Pass
Cross-checked docs against actual repo contents and fixed several genuine mismatches (some pre-dating this update line):
- **`.gitignore` didn't exist.** README claimed `data/portfolio.db` was "gitignored" - it wasn't. For a project whose whole pitch is local-first/no-telemetry, an unignored real portfolio DB was a real gap. Added one.
- **`.github/ISSUE_TEMPLATE/` and `PULL_REQUEST_TEMPLATE.md` were documented (README tree, and the 1.4 changelog's "security-contact link" note) but never actually committed.** Added `config.yml` (with a working security-contact link), `bug_report.yml`, `feature_request.yml`, and `PULL_REQUEST_TEMPLATE.md`.
- **`SECURITY.md` told people to "report responsibly" with no actual reporting mechanism.** Added a link to GitHub's private Security Advisories.
- **README's API Reference table was missing the entire Watchlist endpoint group and `DELETE /api/portfolio/symbol/{symbol}`** (Delete Holdings) - both shipped in update 1 but were never documented.
- **README's CI description said "pytest + ruff"** - the actual `ci.yml` only runs pytest. Corrected the wording rather than silently adding a linter nobody asked for.
- **`/api/watchlist`'s new `is_stale` field was dead data** - nothing consumed it, so the status indicator went stale if you refreshed only the Watchlist tab. `loadWatchlist()` now also pulls `/api/health` to keep the shared status indicator in sync.
- README Dashboard feature description and file tree updated to mention the Watchlist Snapshot, stale-cache indicator, and `test_api.py`.
- Added a CI badge to the README now that `ci.yml` is real.
- `CONTRIBUTING.md` never mentioned running tests at all - added a `pytest` step to the getting-started flow and a short Testing section.

### Added
- **API test coverage** — `tests/test_api.py` adds 13 tests against the live FastAPI app (via `TestClient`), covering the two feature sets update 1 shipped with zero coverage:
  - Watchlist: add/get/update/remove, note sanitization (trim, control-char strip, 280-char cap), unsupported-symbol rejection, double-delete returns 404.
  - Delete Holdings: single-entry delete, delete-all-for-symbol, double-delete 404s, and confirms deleting one symbol's holdings never touches another's (the case the frontend's bulk-delete relies on).
  - Tests run against an isolated throwaway SQLite file and a mocked price cache, so the suite never hits the real network or a person's actual portfolio data.
- **`.github/workflows/ci.yml`** — GitHub Actions workflow that runs the full `pytest` suite on push/PR across Python 3.10–3.12. This was referenced in the 1.2 changelog but was never actually committed; it exists now.
- **`BLUELOCK_DB_PATH` environment variable** — `config.py` now reads the database path from this env var if set, falling back to the existing default. This is what makes the new tests possible without touching real data, and it's also handy for anyone who wants to point the app at a different data file.
- **Friendly port-in-use check** in both `run.sh` and `run.bat` — if something is already listening on 8765 (most often BlueLock still running in another window), the launcher now says so plainly and exits, instead of surfacing a raw asyncio/uvicorn bind error.
- **Dependency import verification** in `run.sh`, matching the check `run.bat` already had — catches a partially-corrupted `venv` install before it fails later with a confusing traceback.

### Notes
- Pillars #1 (live purchase previews) and #2 (dynamic coin loading) were shipped in earlier versions (v1.1 and v1.2 respectively) and remain untouched by this 1.4 update line - nothing was missing here.

---

## [1.4] — update 2 of 3 (unreleased)

### Added
- **Watchlist Snapshot** on the Dashboard — mirrors the existing Favorites/Portfolio Snapshot panels, showing symbol, live price, and note (truncated) for every watched coin without needing to open the Watchlist tab. Refreshes on the same cycle as the rest of the dashboard.
- **Stale-cache indicator** — when the price cache is older than `CACHE_DURATION_SECONDS`, the API status dot/label switch to an amber "cached" state instead of silently claiming ONLINE. Exposed via a new `is_stale` field on `/api/health`, `/api/prices`, `/api/portfolio`, and `/api/watchlist`.
- **Watchlist note validation** — `notes` is now capped at `MAX_NOTE_LENGTH` (280 chars), stripped of control characters, and trimmed, both on add and on inline edit (`WatchlistEntry`, `WatchlistNoteUpdate`). Frontend inputs got matching `maxlength="280"`.

### Fixed
- **CoinGecko retry storm** — previously, once the 60s cache expired, *every* incoming request during an outage independently ran the full retry+sleep sequence against a downed API (worst case ~24s of blocking per request). `prices.py` now tracks the last failure time and enters a 15s cooldown (`API_FAILURE_COOLDOWN_SECONDS`) where it serves the existing stale cache immediately instead of retrying, verified with a network-level test that confirms only one retry sequence fires across three consecutive refresh calls during an outage.

### Changed
- `refreshAll()` on the frontend now also loads the Watchlist, so its dashboard snapshot and stale badge stay current without switching tabs.

---

## [1.4] — 2026-07-05

### Added
- **Watchlist tab** — track coins you don't own yet, independent of your Portfolio holdings.
  - Add any supported coin with an optional personal note (e.g. "Buy under $80k").
  - Live price shown per watched coin, driven by the existing price cache.
  - Double-click a note to edit it inline.
  - New backend table (`watchlist`) and endpoints: `GET/POST /api/watchlist`, `DELETE /api/watchlist/{symbol}`, `PUT /api/watchlist/{symbol}`.
- **Delete Holdings from the Portfolio table** — previously the only way to remove a coin was to open its detail modal and delete purchases one by one, which made deletion feel broken/hidden.
  - Each Holdings row now has 👁 View, ➕ Add Purchase, and 🗑 Delete Holdings buttons.
  - Deleting opens a confirmation dialog showing how many purchase entries exist for that coin, with explicit **Delete All Purchases**, **Manage Individually** (opens the detail modal), and **Cancel** choices — no accidental one-click data loss.
  - New backend endpoint `DELETE /api/portfolio/symbol/{symbol}` (wired to the existing `delete_all_entries_for_symbol()` database function, which previously had no route).
- **Multi-select bulk delete** on the Holdings table — checkboxes per row plus a "select all," with a "Delete Selected (N)" action that appears once something is checked.
- **`entry_count`** added to the coin stats returned by `calculate_coin_stats()`, so the frontend can show "You currently have N purchase entries" without an extra API call.
- **Dynamic version display** — the header, footer, and page title now pull the version live from `/api/health` (`config.APP_VERSION`) instead of a hardcoded string, so the two can no longer drift out of sync.

### Changed
- Version bumped to 1.4 in `config.py`.

### Documentation
- Added `ROADMAP.md` outlining planned and possible future work.
- Added version/license/Python badges to `README.md`.
- Updated `README.md` clone URL, Features table (Watchlist, improved delete UX), and privacy description.
- Added a security-contact link to the issue template picker (`.github/ISSUE_TEMPLATE/config.yml`).

---

## [1.3] — 2026-06-03

### Changed
- Version bumped to 1.3
- Improved Windows launcher reliability (`run.bat` rewritten):
  - All pip commands now use `venv\Scripts\python.exe -m pip` to prevent pip.exe lock errors
  - Browser opens after server is ready (4-second delay) — eliminates race condition
  - Removed `--reload` flag to avoid `watchfiles` Rust dependency on clean Windows installs
  - Added Python 3.10+ version check with clear download instructions
  - venv detection now checks for `venv\Scripts\python.exe` instead of folder presence
  - Per-command error handling with actionable error messages
  - Package import verification step before server starts
- `uvicorn[standard]` replaced with plain `uvicorn` in requirements.txt — removes native compilation dependency on Windows
- `.gitignore` updated to block `portfolio.db-shm` and `portfolio.db-wal` from being committed

---

## [1.2] — 2026-06-01

### Security
- **Restricted CORS** — `allow_origins` changed from `"*"` to `http://127.0.0.1:8765` to prevent cross-origin requests from other local pages.
- **purchase_date validation** — Date fields now enforce `YYYY-MM-DD` format server-side. Invalid formats return a clear validation error.
- **Thread-safe price cache** — Added a `threading.Lock` to prevent concurrent CoinGecko API requests under load.

### Fixed
- **CSV export route shadowed** — Moved `/api/portfolio/export/csv` before `/api/portfolio/{symbol}` in route registration so the export is always reachable.
- **Rate limiter memory leak** — Empty IP key entries are now cleaned up after their sliding window expires.
- **Coin dropdown out of sync** — `populateCoinSelects()` now builds dropdowns dynamically from the `/api/prices` API response instead of a hardcoded JS list. Adding a coin to `config.py` now automatically propagates to the frontend.
- **Locale hardcoded to en-US** — `formatLocalTime()` now uses the browser's locale for date/time display.

### Changed
- **FastAPI lifespan** — Migrated `@app.on_event("startup")` to the modern `lifespan` context manager (the `on_event` decorator is deprecated in current FastAPI).
- **Auto-refresh pauses on hidden tabs** — The 60-second auto-refresh now checks `document.hidden` and skips fetches when the browser tab is not visible.
- Removed unused `MIN_AMOUNT` constant from `config.py`.

### Added
- **Unit test suite** — `tests/test_portfolio.py` with 16 tests covering the calculation engine (single entry, DCA, price unavailable, edge cases, summary rollup, top gainer/loser).
- **GitHub Actions CI** — `.github/workflows/ci.yml` runs `pytest` and `ruff` on Python 3.10/3.11/3.12 on every push and pull request.
- **GitHub issue templates** — Bug report and feature request templates with Blue Lock Systems LLC privacy guidelines.
- **Pull request template** — Checklist including privacy/security requirements.
- **`SECURITY.md`** — Responsible disclosure policy and security design notes.
- **`run.sh`** — Linux and macOS one-click launcher (equivalent to `run.bat`).

---

## [1.1] — 2026-06-01

### Added
- **Live Purchase Preview** — as you fill in the Add Purchase form, the app instantly shows your Cost Basis, Current Market Price, Current Value, Profit/Loss, and ROI. No calculator needed.
- **Help text on all form fields** — every input now has a plain-language hint below it explaining what to enter.
- **Required field markers** and an `(Optional)` label on the date picker so the form is immediately clear to new users.
- **Large "Add Purchase" button** — more prominent and easier to find.
- **Top Gainer / Top Loser cards** on the Dashboard — automatically populated from your portfolio holdings.
- **Colored API Status** — the Dashboard API Status card now shows green `ONLINE` or red `OFFLINE`.
- **Local timestamp formatting** — Last Updated times are displayed in your local timezone instead of UTC.
- **`formatROI()` helper** — handles very large ROI values (e.g. +19,900%) cleanly without scientific notation.
- **Coin dropdown grouped by category** — Major, Privacy, and Stablecoin optgroups make selection faster.
- **`data/.gitkeep`** — ensures the `data/` folder is present in fresh clones so the server starts without errors.
- **`CHANGELOG.md`** — this file.
- **`CONTRIBUTING.md`** — contribution guide.

### Changed
- Portfolio table "Price Unavailable" now shows styled muted italic text instead of a bare dash.
- `About` page coin list now shows category badges alongside each coin.
- Version string bumped to `1.1` in `config.py` and the About tab.

### Fixed
- Dashboard Top Gainer / Top Loser grid was rendered but never shown — now correctly wired to portfolio data.
- Friendly validation messages on the Add Purchase form now read as natural sentences rather than terse error codes.

---

## [1.0] — Initial Release

- Live prices for 11 cryptocurrencies via CoinGecko public API (60-second cache).
- Portfolio tracker with multi-purchase support and weighted average cost calculation.
- Automatic calculation of Cost Basis, Current Value, Profit/Loss, and ROI.
- Price Calculator panel.
- Favorites system with Dashboard pinning.
- Search and category filtering on both Prices and Portfolio tabs.
- Portfolio Summary card (total value, total cost, P&L, overall ROI).
- Coin detail modal with full purchase history, edit, and delete.
- Export portfolio to CSV.
- SQLite local database — all data stays on your machine.
- Auto-refresh every 60 seconds.
- Windows launcher (`run.bat`) with automatic venv setup.
- Rate limiting, input validation, and graceful API failure handling.
