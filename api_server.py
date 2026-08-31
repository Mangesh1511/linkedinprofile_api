#!/usr/bin/env python3
"""
Reverse-Engineered LinkedIn Profile REST API Server (Pure HTTP - Zero Browser)

FastAPI server exposing REST endpoints for scraping LinkedIn person profiles
using direct reverse-engineered HTTP Voyager RESTli API endpoints.
100% pure Python HTTP stack with zero Chromium or Playwright runtime overhead.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv(".env.example")

from linkedinprofile_api.core.auth import extract_session_cookies, ensure_valid_session
from linkedinprofile_api.scrapers.reverse_person import ReverseEngineeredScraper
from linkedinprofile_api.core.exceptions import (
    AuthenticationError,
    RateLimitError,
    ScrapingError,
    ProfileNotFoundError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("api_server.log", mode="a", encoding="utf-8"),
    ]
)
logger = logging.getLogger("api_server")

SESSION_FILE = "linkedin_session.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager: Initializes and verifies session authentication state on startup.
    Pure HTTP stack with zero browser or Playwright overhead.
    """
    try:
        cookie_dict, csrf_token = await ensure_valid_session(SESSION_FILE)
        logger.info(f"✓ Pure HTTP session initialized successfully (li_at cookie present). Session saved to '{SESSION_FILE}'.")
    except AuthenticationError as auth_err:
        logger.warning(f"⚠️ Startup session warning: {auth_err}. Provide LI_AT environment variable or linkedin_session.json file.")

    yield  # REST API Server handles requests using direct HTTP Voyager API calls


app = FastAPI(
    title="Reverse-Engineered LinkedIn Profile REST API (Pure HTTP)",
    description="Sub-second REST API for extracting LinkedIn person profiles via direct HTTP Voyager API calls with zero browser overhead.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for public web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Healthcheck endpoint for load balancers and container monitoring."""
    session_active = Path(SESSION_FILE).exists() or bool(os.getenv("LI_AT"))
    return {
        "status": "healthy",
        "session_active": session_active,
        "engine": "Pure Reverse-Engineered Direct HTTP (Zero Browser / No Playwright)",
    }


@app.get("/api/profileinfo")
async def get_profile_info(
    profileUrl: str = Query(..., description="LinkedIn profile URL to scrape (e.g. https://www.linkedin.com/in/williamhgates/)")
):
    """
    Scrape a LinkedIn person profile by URL using direct reverse-engineered HTTP endpoints (Voyager API).
    
    Sub-second response time (~150ms) with zero browser execution overhead.
    """
    try:
        scraper = ReverseEngineeredScraper(session_path=SESSION_FILE)
        person = await scraper.scrape(profileUrl)
        return {
            "status": "success",
            "data": person.to_dict(),
        }
    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit detected: {e}"
        )
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {e}"
        )
    except ScrapingError as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while scraping profile: {e}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
