"""
Pure HTTP Authentication and Session Cookie Manager for LinkedIn (Zero Browser / No Playwright).
"""

import os
import json
import logging
from typing import Optional, Tuple, Dict
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
    # Priority 1: Direct LI_AT environment variable (Best for cloud deployment & server startup)
    env_li_at = os.getenv("LI_AT")
    if env_li_at:
        env_jsessionid = os.getenv("JSESSIONID", "ajax:1234567890123456789").strip('"')
        cookie_dict = {
            "li_at": env_li_at.strip(),
            "JSESSIONID": f'"{env_jsessionid}"',
        }
        _persist_session_if_missing(session_path, cookie_dict)
        return cookie_dict, env_jsessionid

    # Priority 2: Base64 session string in environment
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
                _persist_session_if_missing(session_path, cookie_dict)
                return cookie_dict, jsessionid
        except Exception as b64_err:
            logger.warning(f"Could not decode LINKEDIN_SESSION_B64: {b64_err}")

    # Priority 3: Local linkedin_session.json file on disk
    if not os.path.exists(session_path):
        raise AuthenticationError(
            f"Session file '{session_path}' not found and LI_AT / LINKEDIN_SESSION_B64 env vars not set."
        )
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cookie_dict = {}
        # Support both Playwright storage_state format and simple dict format
        if isinstance(data, dict) and "cookies" in data:
            for c in data.get("cookies", []):
                if "linkedin.com" in c.get("domain", ""):
                    cookie_dict[c["name"]] = c["value"]
        elif isinstance(data, dict):
            cookie_dict = data

        li_at = cookie_dict.get("li_at")
        jsessionid = cookie_dict.get("JSESSIONID", "ajax:1234567890123456789").strip('"')
        
        if not li_at:
            raise AuthenticationError("`li_at` cookie not found in session file.")
        
        return cookie_dict, jsessionid
    except Exception as e:
        raise AuthenticationError(f"Could not read session cookies from {session_path}: {e}")


def _persist_session_if_missing(session_path: str, cookie_dict: Dict[str, str]) -> None:
    """Save session cookies to linkedin_session.json if not present."""
    if not os.path.exists(session_path):
        try:
            formatted_state = {
                "cookies": [
                    {
                        "name": k,
                        "value": v,
                        "domain": ".www.linkedin.com",
                        "path": "/",
                        "expires": -1,
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "None"
                    }
                    for k, v in cookie_dict.items()
                ],
                "origins": []
            }
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(formatted_state, f, indent=2)
            logger.info(f"💾 Persisted environment session cookies to '{session_path}'")
        except Exception as e:
            logger.warning(f"Could not persist session file: {e}")


async def ensure_valid_session(
    session_path: str = "linkedin_session.json",
    force_refresh: bool = False,
) -> Tuple[Dict[str, str], str]:
    """
    Ensure valid session cookies exist (from LI_AT / LINKEDIN_SESSION_B64 env vars or linkedin_session.json).
    100% pure HTTP with ZERO browser / Playwright runtime dependencies.
    """
    return extract_session_cookies(session_path)
