"""
Reverse-Engineered LinkedIn Profile REST API Package.
"""

from .models import Person, Experience, Education, Accomplishment, Interest, Contact
from .scrapers import ReverseEngineeredScraper
from .core import extract_session_cookies, ensure_valid_session, ScrapingError, AuthenticationError

__version__ = "1.0.0"

__all__ = [
    'Person',
    'Experience',
    'Education',
    'Accomplishment',
    'Interest',
    'Contact',
    'ReverseEngineeredScraper',
    'extract_session_cookies',
    'ensure_valid_session',
    'ScrapingError',
    'AuthenticationError',
]
