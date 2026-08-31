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
    Read authenticated li_at and JSESSIONID cookies from environment variables or linkedin_session.json.
    
    Returns:
        Tuple of (cookie_dict, csrf_token_string)
    """
    # Check 1: Direct LI_AT environment variable override (Best for Production / Cloud Run)
    env_li_at = os.getenv("LI_AT")
    if env_li_at:
        env_jsessionid = os.getenv("JSESSIONID", "ajax:1234567890123456789").strip('"')
        cookie_dict = {
            "li_at": env_li_at.strip(),
            "JSESSIONID": f'"{env_jsessionid}"',
        }
        return cookie_dict, env_jsessionid

    # Check 2: Base64 session string in environment
    env_b64 = os.getenv("LINKEDIN_SESSION_B64")
    if env_b64:
        try:
            import base64
            decoded = base64.b64decode(env_b64.strip()).decode("utf-8")
            data = json.loads(decoded)
            cookie_dict = {}
            for c in data.get("cookies", []):
                if "linkedin.com" in c.get("domain", ""):
                    cookie_dict[c["name"]] = c["value"]
            li_at = cookie_dict.get("li_at")
            jsessionid = cookie_dict.get("JSESSIONID", "").strip('"')
            if li_at:
                return cookie_dict, jsessionid
        except Exception as b64_err:
            logger.warning(f"Could not decode LINKEDIN_SESSION_B64: {b64_err}")

    # Check 3: Local linkedin_session.json file
    if not os.path.exists(session_path):
        raise AuthenticationError(
            f"Session file '{session_path}' not found and LI_AT / LINKEDIN_SESSION_B64 env vars not set."
        )
    
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


async def ensure_valid_session(
    session_path: str = "linkedin_session.json",
    force_refresh: bool = False,
) -> Tuple[Dict[str, str], str]:
    """
    Ensure valid session cookies exist (from LI_AT / LINKEDIN_SESSION_B64 env vars or linkedin_session.json).
    If environment variables are set, uses them directly to avoid datacenter IP login blockers.
    """
    # 1. Environment variables take top precedence (100% fail-safe for Cloud Run)
    if os.getenv("LI_AT") or os.getenv("LINKEDIN_SESSION_B64"):
        return extract_session_cookies(session_path)

    # 2. Check local session_path file on disk
    if not force_refresh and os.path.exists(session_path):
        try:
            return extract_session_cookies(session_path)
        except AuthenticationError as auth_err:
            logger.warning(f"⚠️ Session file '{session_path}' invalid ({auth_err}). Regenerating session...")

    if force_refresh and os.path.exists(session_path):
        try:
            os.remove(session_path)
            logger.info(f"🔄 Removed stale session file '{session_path}' for session refresh.")
        except Exception:
            pass

    email, password = load_credentials_from_env()
    if not email or not password:
        raise AuthenticationError(
            "Session file missing `li_at` cookie and credentials (LINKEDIN_EMAIL, LINKEDIN_PASSWORD) not set in environment."
        )

    from .browser import BrowserManager
    logger.info(f"🔑 Regenerating valid '{session_path}' authentication cookies via Playwright...")
    async with BrowserManager(headless=True) as browser:
        page = await browser.context.new_page()
        await login_with_credentials(page, email=email, password=password)
        await browser.save_session(session_path)

    return extract_session_cookies(session_path)


async def is_logged_in(page: Page) -> bool:
    """Check if currently logged into LinkedIn in browser context."""
    try:
        current_url = page.url
        auth_blockers = ['/login', '/authwall', '/checkpoint', '/challenge', '/uas/login']
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
    """Perform automated login to LinkedIn using email and password with diagnostic logging."""
    if not email or not password:
        env_email, env_password = load_credentials_from_env()
        email = email or env_email
        password = password or env_password

    if not email or not password:
        raise AuthenticationError("LinkedIn credentials not provided in .env file.")

    logger.info(f"🔑 [Auth Step 1/4] Navigating to LinkedIn login page for: {email}...")

    try:
        await page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
        logger.info(f"📍 [Auth Step 2/4] On login page URL: {page.url}")

        user_selector = "input[type='email']:visible, input[type='text']:visible, #username:visible"
        pass_selector = "input[type='password']:visible, #password:visible"

        try:
            await page.wait_for_selector(user_selector, timeout=timeout, state='visible')
        except PlaywrightTimeoutError:
            logger.error(f"❌ [Auth Error] Login form inputs not visible on page. Current URL: {page.url}")
            raise AuthenticationError(f"Login form not found on {page.url}.")

        email_el = page.locator(user_selector).first
        await email_el.click()
        await email_el.press_sequentially(email, delay=20)

        pass_el = page.locator(pass_selector).first
        await pass_el.click()
        await pass_el.press_sequentially(password, delay=20)

        logger.info("📩 [Auth Step 3/4] Submitting credentials (pressing Enter)...")
        await pass_el.press("Enter")

        try:
            await page.wait_for_url(
                lambda url: any(k in url for k in ['feed', 'in/', 'checkpoint', 'challenge', 'authwall', 'uas/login']),
                timeout=timeout
            )
        except PlaywrightTimeoutError:
            logger.warning(f"⚠️ [Auth Notice] Navigation timeout after submit. Current URL: {page.url}")

        post_url = page.url
        logger.info(f"📍 [Auth Step 4/4] Post-submit URL: {post_url}")

        if 'checkpoint' in post_url or 'challenge' in post_url or 'uas/login-submit' in post_url:
            logger.error(
                f"❌ [Auth Checkpoint] LinkedIn security verification / PIN challenge triggered at URL: {post_url}. "
                "Datacenter automated login requires passing LI_AT environment variable or solving PIN."
            )
            raise AuthenticationError(
                f"Security checkpoint triggered: {post_url}. Pass LI_AT environment variable to bypass."
            )

        if 'login' in post_url:
            logger.error(f"❌ [Auth Error] Login remained on login page. Credentials may be invalid or rejected.")
            raise AuthenticationError("Login failed. Please verify LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env.")

        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < 5:
            if await is_logged_in(page):
                logger.info("✓ [Auth Success] Authenticated session established!")
                return
            await asyncio.sleep(0.5)

    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        logger.error(f"❌ [Auth Unexpected Error]: {e}")
        raise AuthenticationError(f"Unexpected error during login: {e}")
