"""
Custom exception classes for LinkedIn Profile API scraper.
"""


class ScrapingError(Exception):
    """Base exception for scraping operations."""
    pass


class AuthenticationError(ScrapingError):
    """Raised when authentication fails or session credentials are invalid."""
    pass


class RateLimitError(ScrapingError):
    """Raised when LinkedIn rate limit or security check is encountered."""
    pass


class ElementNotFoundError(ScrapingError):
    """Raised when required profile elements or Voyager endpoints are missing."""
    pass
