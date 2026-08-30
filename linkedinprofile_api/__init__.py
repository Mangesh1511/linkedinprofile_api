"""
Reverse-Engineered LinkedIn Profile API Package.
"""

from .models import Person, Experience, Education, Accomplishment, Interest, Contact
from .scrapers import ReverseEngineeredScraper
from .core import BrowserManager, extract_session_cookies, login_with_credentials, ScrapingError, AuthenticationError

__version__ = "1.0.0"

__all__ = [
    'Person',
    'Experience',
    'Education',
    'Accomplishment',
    'Interest',
    'Contact',
    'ReverseEngineeredScraper',
    'BrowserManager',
    'extract_session_cookies',
    'login_with_credentials',
    'ScrapingError',
    'AuthenticationError',
]
