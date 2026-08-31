"""
Playwright Browser Manager used during server startup to authenticate and save session.
"""

import os
import json
import logging
from typing import Optional
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser lifecycle for session cookie generation."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def start(self) -> None:
        """Start Playwright and launch Chromium browser."""
        logger.info(f"Starting Playwright Chromium (headless={self.headless})...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        self.context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        )
        logger.info("✓ Playwright BrowserManager started successfully")

    async def save_session(self, filepath: str = "linkedin_session.json") -> None:
        """Save storage state (cookies) to file with diagnostic logging."""
        if not self.context:
            raise RuntimeError("Browser context is not initialized.")
        state = await self.context.storage_state()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        
        cookie_names = [c.get("name") for c in state.get("cookies", []) if "linkedin.com" in c.get("domain", "")]
        has_li_at = "li_at" in cookie_names
        
        if has_li_at:
            logger.info(f"💾 Saved {len(cookie_names)} LinkedIn session cookies to '{filepath}' (✓ 'li_at' cookie verified: {cookie_names})")
        else:
            logger.warning(f"⚠️ Saved session file '{filepath}', BUT 'li_at' cookie was MISSING! Extracted cookies: {cookie_names}")

    async def close(self) -> None:
        """Close browser and stop Playwright."""
        if self.context:
            await self.context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("✓ Playwright BrowserManager closed")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
