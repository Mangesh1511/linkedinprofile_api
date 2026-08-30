# Project instructions

## Purpose
Standalone reverse-engineered LinkedIn profile API using direct HTTP requests.

## Commands
- `python3 -m pytest -q` runs the test suite.
- `uvicorn api_server:app --host 0.0.0.0 --port 8000` starts the service.

## Conventions
- Keep direct LinkedIn HTTP logic behind `ReverseEngineeredScraper`.
- Never commit credentials or session cookies.
- The current interim version may use Playwright only for startup login; later versions should remove that browser dependency entirely.
