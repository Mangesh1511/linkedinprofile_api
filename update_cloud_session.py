#!/usr/bin/env python3
"""
Automated Local Session Refresher & Cloud Run Sync Script for LinkedIn.

Runs Playwright locally on your Mac (residential IP) to refresh session cookies automatically
without manual copy-pasting, then updates Google Cloud Run environment variables.
"""

import os
import json
import subprocess
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()


async def refresh_and_sync():
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    service_name = os.getenv("CLOUD_RUN_SERVICE", "linkedin-profile-api")
    region = os.getenv("CLOUD_RUN_REGION", "us-central1")

    if not email or not password:
        print("❌ Error: LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env")
        return

    print(f"🔑 [1/3] Starting local Playwright login for: {email}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        await page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
        
        user_selector = "input[type='email']:visible, input[type='text']:visible, #username:visible"
        pass_selector = "input[type='password']:visible, #password:visible"
        
        await page.wait_for_selector(user_selector, timeout=15000, state='visible')
        
        email_el = page.locator(user_selector).first
        await email_el.click()
        await email_el.press_sequentially(email, delay=20)
        
        pass_el = page.locator(pass_selector).first
        await pass_el.click()
        await pass_el.press_sequentially(password, delay=20)
        await pass_el.press("Enter")
        
        await page.wait_for_timeout(5000)
        
        state = await context.storage_state()
        cookie_dict = {}
        for c in state.get("cookies", []):
            if "linkedin.com" in c.get("domain", ""):
                cookie_dict[c["name"]] = c["value"]

        li_at = cookie_dict.get("li_at")
        jsessionid = cookie_dict.get("JSESSIONID", "").strip('"')

        if not li_at:
            print(f"❌ Error: Automated login failed to obtain 'li_at' cookie. Page URL: {page.url}")
            await browser.close()
            return

        print(f"✓ [2/3] Successfully obtained fresh session cookies!")
        print(f"   LI_AT: {li_at[:20]}...")
        print(f"   JSESSIONID: {jsessionid[:20]}...")

        # Save to local session file
        with open("linkedin_session.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        print("💾 Updated local 'linkedin_session.json'")

        await browser.close()

    # Step 3: Automatically update Cloud Run Service
    print(f"🚀 [3/3] Syncing fresh session cookies to Google Cloud Run ({service_name})...")
    cmd = [
        "gcloud", "run", "services", "update", service_name,
        "--region", region,
        "--set-env-vars", f"LI_AT={li_at},JSESSIONID=ajax:{jsessionid}"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Cloud Run updated successfully! Fresh session cookies are now live!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ gcloud sync notice: {e.stderr}")
        print("Manual command to sync:")
        print(f"gcloud run services update {service_name} --region {region} --set-env-vars LI_AT=\"{li_at}\",JSESSIONID=\"ajax:{jsessionid}\"")


if __name__ == "__main__":
    asyncio.run(refresh_and_sync())
