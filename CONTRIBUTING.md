# Contributing to BlueLock Crypto Tracking

Thanks for your interest in contributing. This is a small privacy-focused project and contributions are welcome.

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```
   git clone https://github.com/bluelocksystems-lab/BlueLockCryptoTracking.git
   cd BlueLockCryptoTracking
   ```
3. **Create a branch** for your change:
   ```
   git checkout -b feature/your-feature-name
   ```
4. **Launch the app** with `run.bat` (Windows) or `./run.sh` (macOS/Linux) to test your changes locally.
5. **Run the test suite** before opening a PR (see [Testing](#testing) below).
6. **Commit** your changes with a clear message.
7. **Push** your branch and open a **Pull Request** against `main`.

---

## Adding a New Coin

This is the most common contribution. To add a coin:

1. Find its CoinGecko ID — go to `https://www.coingecko.com`, search for the coin, and copy the ID from the URL (e.g. `https://www.coingecko.com/en/coins/monero` → ID is `monero`).

2. Open `backend/config.py` and add entries to all three dicts:
   ```python
   SUPPORTED_COINS = {
       ...
       "XYZ": "coingecko-id-here",
   }
   COIN_NAMES = {
       ...
       "XYZ": "Coin Full Name",
   }
   COIN_CATEGORIES = {
       ...
       "XYZ": "Privacy",  # or "Major" or "Stablecoin"
   }
   ```

3. Open `frontend/app.js` and add the coin to the `coins` array inside `populateCoinSelects()`:
   ```javascript
   { symbol: "XYZ", name: "Coin Full Name", category: "Privacy" },
   ```

4. Restart the server and verify the coin appears in the Prices tab with a live price.

---

## Testing

```
pip install pytest httpx -r backend/requirements.txt
python -m pytest tests/ -v
```

Every push and PR also runs this same suite automatically via GitHub Actions
(`.github/workflows/ci.yml`) across Python 3.10–3.12. If you add a new
backend endpoint or change validation behavior, add a test for it in
`tests/test_api.py` (endpoint-level) or `tests/test_portfolio.py`
(calculation-engine-level) rather than only testing manually through the UI.

---

## Code Style

- **Python**: Follow PEP 8. Use descriptive variable names. Add a docstring to any new function.
- **JavaScript**: Plain ES6+, `"use strict"`, no frameworks. Keep functions small and focused.
- **CSS**: Add new rules at the bottom of `style.css` under a clear section comment.

---

## What We Won't Accept

- Anything that requires a user account or login.
- Features that send user data to any server other than CoinGecko's public price API.
- Exchange integrations or transaction functionality.
- Dependencies that add significant bundle weight without clear benefit.

---

## Reporting Bugs

Open a GitHub Issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version (`python --version`) and OS

---

## License

By contributing, you agree your contributions will be licensed under the project's MIT License.
