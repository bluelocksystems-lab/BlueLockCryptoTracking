# Security Policy

## About BlueLock Crypto Tracking

BlueLock Crypto Tracking is a **local-only, self-hosted** application. It:

- Stores all data in a local SQLite database on your machine
- Makes outbound connections **only** to CoinGecko's public read-only price API
- Binds exclusively to `127.0.0.1` — it is **not** accessible from other devices
- Has **no user accounts**, no cloud sync, and no telemetry of any kind

## Supported Versions

| Version | Supported |
|---|---|
| 1.x (latest) | ✅ Active support |
| < 1.0 | ❌ No longer supported |

## Reporting a Vulnerability

**Please open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability, please report it responsibly:
 
**Subject line:** `[BlueLock Security] Brief description`

Include:
- A description of the vulnerability
- Steps to reproduce it
- The potential impact
- Any suggested mitigations (optional)

We will:
- Acknowledge your report within **72 hours**
- Provide a status update within **7 days**
- Coordinate a fix and public disclosure timeline with you
- Credit you in the release notes 

## Security Scope

| In Scope | Out of Scope |
|---|---|
| SQL injection | Attacks requiring physical access to the machine |
| XSS in the web UI | Social engineering |
| CSRF or unauthorized API access | CoinGecko API vulnerabilities (report to them) |
| Sensitive data exposure | Issues in Python/FastAPI/SQLite themselves |
| Dependency vulnerabilities | |

## Security Design Notes

- All SQL queries use parameterized statements (no string interpolation)
- All user input rendered in the frontend is HTML-escaped via `escHtml()`
- Server binds to `127.0.0.1` only — not `0.0.0.0`
- CORS is restricted to `http://127.0.0.1:8765`
- No wallet connections, no private keys, no transaction functionality

---

*Blue Lock Systems LLC — Privacy First. Security Focused.*
