"""
Authentication helpers and Playwright session generator for LinkedIn.
"""

import os
import json
import asyncio
import logging
from typing import Optional, Tuple, Dict
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

from .exceptions import AuthenticationError

logger = logging.getLogger(__name__)


def load_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """Load LinkedIn email and password from .env file."""
    load_dotenv()
    load_dotenv(".env.example")
    
    email = os.getenv('LINKEDIN_EMAIL') or os.getenv('LINKEDIN_USERNAME')
    password = os.getenv('LINKEDIN_PASSWORD')
    return email, password


def extract_session_cookies(session_path: str = "linkedin_session.json") -> Tuple[Dict[str, str], str]:
    """
    Read authenticated li_at and JSESSIONID cookies from linkedin_session.json.
    
    Returns:
        Tuple of (cookie_dict, csrf_token_string)
    """
    if not os.path.exists(session_path):
        raise AuthenticationError(f"Session file '{session_path}' not found. Run authentication first.")
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cookie_dict = {}
        for c in data.get("cookies", []):
            if "linkedin.com" in c.get("domain", ""):
                cookie_dict[c["name"]] = c["value"]
        
        li_at = cookie_dict.get("li_at")
        jsessionid = cookie_dict.get("JSESSIONID", "").strip('"')
        
        if not li_at:
            raise AuthenticationError("`li_at` cookie not found in session file.")
        
        return cookie_dict, jsessionid
    except Exception as e:
        raise AuthenticationError(f"Could not read session cookies from {session_path}: {e}")


async def is_logged_in(page: Page) -> bool:
    """Check if currently logged into LinkedIn in browser context."""
    try:
        current_url = page.url
        auth_blockers = ['/login', '/authwall', '/checkpoint', '/challenge']
        if any(pattern in current_url for pattern in auth_blockers):
            return False
        
        selectors = 'nav a[href*="/feed"], nav button:has-text("Home"), .global-nav__me'
        count = await page.locator(selectors).count()
        return count > 0 or '/feed' in current_url
    except Exception:
        return False


async def login_with_credentials(
    page: Page,
    email: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = 30000,
) -> None:
    """Perform automated login to LinkedIn using email and password."""
    if not email or not password:
        env_email, env_password = load_credentials_from_env()
        email = email or env_email
        password = password or env_password
    
    if not email or not password:
        raise AuthenticationError("LinkedIn credentials not provided in .env file.")
    
    logger.info(f"🔑 Performing startup automated login for: {email}...")
    
    try:
        await page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
        
        user_selector = "input[type='email']:visible, input[type='text']:visible, #username:visible"
        pass_selector = "input[type='password']:visible, #password:visible"
        
        await page.wait_for_selector(user_selector, timeout=timeout, state='visible')
        
        email_el = page.locator(user_selector).first
        await email_el.click()
        await email_el.press_sequentially(email, delay=20)
        
        pass_el = page.locator(pass_selector).first
        await pass_el.click()
        await pass_el.press_sequentially(password, delay=20)
        
        await pass_el.press("Enter")
        
        try:
            await page.wait_for_url(
                lambda url: any(k in url for k in ['feed', 'in/', 'checkpoint', 'challenge', 'authwall']),
                timeout=timeout
            )
        except PlaywrightTimeoutError:
            if 'login' in page.url:
                raise AuthenticationError("Login failed. Please check credentials in .env file.")
        
        if 'checkpoint' in page.url or 'challenge' in page.url:
            raise AuthenticationError(f"Security checkpoint triggered: {page.url}")
        
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < 5:
            if await is_logged_in(page):
                logger.info("✓ Login successful!")
                return
            await asyncio.sleep(0.5)
            
    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(f"Unexpected error during login: {e}")
