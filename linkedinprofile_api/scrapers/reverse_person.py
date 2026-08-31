"""
Pure Reverse-Engineered LinkedIn Person Scraper (No Browser).

Directly hits LinkedIn internal endpoints (Voyager API & HTML SSR payloads)
using lightweight async HTTP requests with session cookies and CSRF headers.
Executes in sub-second speed (<200ms) with ZERO browser overhead.
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from ..models import Person, Experience, Education, Accomplishment, Interest, Contact
from ..core.auth import extract_session_cookies, ensure_valid_session
from ..core.exceptions import ScrapingError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class ReverseEngineeredScraper:
    """
    Pure reverse-engineered LinkedIn scraper using direct HTTP requests.
    Does NOT use a browser.
    """

    def __init__(self, session_path: str = "linkedin_session.json"):
        self.session_path = session_path

    def _extract_slug(self, url_or_slug: str) -> str:
        """Extract public profile identifier slug from URL or string."""
        clean = url_or_slug.strip()
        if clean.startswith("http://") or clean.startswith("https://"):
            parsed = urlparse(clean)
            parts = [p for p in parsed.path.split("/") if p]
            if "in" in parts:
                idx = parts.index("in")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
            return parts[-1] if parts else clean
        return clean.strip("/")

    async def scrape(self, linkedin_url: str) -> Person:
        """
        Scrape LinkedIn person profile using direct HTTP calls to reverse-engineered endpoints.
        """
        slug = self._extract_slug(linkedin_url)
        canonical_url = f"https://www.linkedin.com/in/{slug}/"
        logger.info(f"⚡ Reverse-Engineered HTTP Scrape starting for slug: '{slug}'...")

        cookie_dict, csrf_token = await ensure_valid_session(self.session_path)

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/vnd.linkedin.normalized+json+2.0, application/json, text/html",
            "Accept-Language": "en-US,en;q=0.9",
            "csrf-token": csrf_token,
            "x-restli-protocol-version": "2.0.0",
            "x-li-lang": "en_US",
        }

        try:
            async with httpx.AsyncClient(headers=headers, cookies=cookie_dict, follow_redirects=True, timeout=15.0) as client:
                # Step 1: Call Voyager Dash Profile API endpoint
                voyager_url = f"https://www.linkedin.com/voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={slug}"
                positions_url = f"https://www.linkedin.com/voyager/api/identity/profiles/{slug}/positionGroups"
                
                logger.info(f"📡 Requesting Voyager API endpoint: {voyager_url}")
                
                dash_res = await client.get(voyager_url)
                
                # Check for token expiration (401 / 403) and auto-refresh session once
                if dash_res.status_code in (401, 403):
                    logger.warning(f"⚠️ Voyager API returned HTTP {dash_res.status_code} (Session token expired/invalid). Force refreshing session cookies...")
                    try:
                        cookie_dict, csrf_token = await ensure_valid_session(self.session_path, force_refresh=True)
                        headers["csrf-token"] = csrf_token
                        async with httpx.AsyncClient(headers=headers, cookies=cookie_dict, follow_redirects=True, timeout=15.0) as retry_client:
                            dash_res = await retry_client.get(voyager_url)
                            pos_res = await retry_client.get(positions_url)
                    except Exception as refresh_err:
                        logger.error(f"❌ Session auto-refresh failed: {refresh_err}")
                        raise AuthenticationError(f"LinkedIn session expired and automated refresh failed: {refresh_err}")

                if dash_res.status_code in (401, 403):
                    raise AuthenticationError(f"LinkedIn session expired or unauthorized (Status {dash_res.status_code}).")
                elif dash_res.status_code == 429:
                    raise RateLimitError("LinkedIn rate limit encountered.")

                pos_res = await client.get(positions_url)

                # Check if Voyager Dash API returned 200 OK
                if dash_res.status_code == 200:
                    data = dash_res.json()
                    pos_data = pos_res.json() if pos_res.status_code == 200 else {}
                    return self._parse_voyager_json(canonical_url, data, pos_data)
                
                # Step 2: Fallback to Direct HTML SSR Parsing
                logger.info("ℹ️ Voyager API returned fallback code; hitting direct HTML profile endpoint...")
                html_res = await client.get(canonical_url)
                if html_res.status_code == 200:
                    return self._parse_html_ssr(canonical_url, html_res.text)
                else:
                    raise ScrapingError(f"Direct profile HTTP fetch failed with status code {html_res.status_code}.")

        except httpx.TooManyRedirects:
            logger.error("❌ LinkedIn redirected to authwall/login loop. Session cookie `li_at` is expired or invalid.")
            raise AuthenticationError("LinkedIn session cookie (`li_at`) is expired or invalid. Please update the `LI_AT` environment variable.")
        except httpx.HTTPError as http_err:
            logger.error(f"❌ HTTP transport error: {http_err}")
            raise ScrapingError(f"Network error while connecting to LinkedIn: {http_err}")

    def _parse_voyager_json(self, linkedin_url: str, dash_data: Dict[str, Any], pos_data: Dict[str, Any]) -> Person:
        """Parse structured JSON returned by LinkedIn Voyager API."""
        elements = dash_data.get("elements", [])
        if not elements:
            raise ScrapingError("No profile elements found in Voyager API JSON response.")

        p_data = elements[0]
        first_name = p_data.get("multiLocaleFirstName", {}).get("en_US") or p_data.get("firstName", "")
        last_name = p_data.get("multiLocaleLastName", {}).get("en_US") or p_data.get("lastName", "")
        name = f"{first_name} {last_name}".strip() or "Unknown"

        about = p_data.get("multiLocaleSummary", {}).get("en_US") or p_data.get("summary")
        headline = p_data.get("headline")
        location = p_data.get("locationName")

        # Parse Work Experiences from Position Groups API JSON
        experiences: List[Experience] = []
        for grp in pos_data.get("elements", []):
            company_name = grp.get("name") or "Company"
            for pos in grp.get("positions", []):
                title = pos.get("title") or pos.get("companyName") or "Position"
                loc = pos.get("locationName") or pos.get("geoLocationName")
                
                # Parse start/end dates
                time_period = pos.get("timePeriod", {})
                start_dict = time_period.get("startDate", {})
                end_dict = time_period.get("endDate", {})
                
                from_d = f"{start_dict.get('month', '')}/{start_dict.get('year', '')}".strip("/") if start_dict else None
                to_d = f"{end_dict.get('month', '')}/{end_dict.get('year', '')}".strip("/") if end_dict else "Present"

                experiences.append(
                    Experience(
                        position_title=title,
                        institution_name=company_name,
                        from_date=from_d,
                        to_date=to_d,
                        location=loc,
                        description=pos.get("description"),
                    )
                )

        return Person(
            linkedin_url=linkedin_url,
            name=name,
            headline=headline,
            location=location,
            about=about,
            experiences=experiences,
        )

    def _parse_html_ssr(self, linkedin_url: str, html: str) -> Person:
        """Fallback HTML SSR parser using BeautifulSoup."""
        soup = BeautifulSoup(html, "lxml")
        raw_title = soup.title.string.replace("| LinkedIn", "").strip() if soup.title else "Unknown"

        # Detect logged-out or authwall signup page titles
        if any(bad in raw_title.lower() for bad in ["join linkedin", "linked in", "linkedin", "sign in", "log in"]):
            logger.error(f"❌ Received logged-out LinkedIn page title: '{raw_title}'. Session cookie `li_at` is invalid or expired.")
            raise AuthenticationError("LinkedIn session cookie (`li_at`) is expired or invalid. Please update the `LI_AT` environment variable.")

        headline = None
        for el in soup.find_all(["p", "span", "h2"]):
            t = el.get_text(strip=True)
            if "Software Engineer" in t or "Developer" in t or "Manager" in t:
                if len(t) < 150:
                    headline = t
                    break

        return Person(
            linkedin_url=linkedin_url,
            name=raw_title,
            headline=headline,
        )
