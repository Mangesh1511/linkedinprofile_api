#!/usr/bin/env python3
"""
Live Voyager Profile API Inspector & File Exporter

Launches a visible Chromium desktop browser window on your Mac screen.
Captures ALL live Voyager API calls, logs them to stdout with flush=True,
and saves captured JSON records to 'voyager_captured_sample.json'.
"""

import os
import sys
import json
import asyncio
from playwright.async_api import async_playwright

SAVED_JSON_PATH = "voyager_captured_sample.json"


async def main():
    print("\n" + "=" * 90, flush=True)
    print("🚀 LAUNCHING VISIBLE CHROMIUM DESKTOP BROWSER FOR VOYAGER API CAPTURE...", flush=True)
    print("   Please look at your Mac screen. A Chromium browser window will open.", flush=True)
    print(f"   All captured Voyager JSON payloads will be saved to '{SAVED_JSON_PATH}'.", flush=True)
    print("=" * 90 + "\n", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context_options = {
            'viewport': {'width': 1280, 'height': 800},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        }
        if os.path.exists("linkedin_session.json"):
            context_options['storage_state'] = "linkedin_session.json"

        context = await browser.new_context(**context_options)
        page = await context.new_page()

        captured_count = 0
        records = []

        # Intercept and record ALL Voyager API endpoints
        async def handle_response(response):
            nonlocal captured_count
            url = response.url
            if "voyager" in url or "dash" in url or "identity" in url:
                captured_count += 1
                req_headers = response.request.headers
                csrf = req_headers.get("csrf-token")
                restli_ver = req_headers.get("x-restli-protocol-version")

                banner = f"""
==========================================================================================
🔥 [INTERCEPTED VOYAGER API CALL #{captured_count}]
📍 URL     : {url}
⚡ METHOD  : {response.request.method} | STATUS: {response.status}
🔑 HEADERS : csrf-token={csrf} | x-restli-protocol-version={restli_ver}
==========================================================================================
"""
                print(banner, flush=True)

                try:
                    data = await response.json()
                    capture_record = {
                        "captured_url": url,
                        "status": response.status,
                        "csrf_token_header": csrf,
                        "restli_protocol_version": restli_ver,
                        "json_payload": data
                    }
                    records.append(capture_record)
                    with open(SAVED_JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(records, f, indent=2)
                    print(f"💾 SAVED VOYAGER JSON RECORD #{captured_count} TO: '{SAVED_JSON_PATH}'", flush=True)
                except Exception as parse_err:
                    pass

        page.on("response", handle_response)

        profile_url = "https://www.linkedin.com/in/mangesh-dudhgaonkar-patil-422870209/"
        print(f"🌐 Navigating browser to profile: {profile_url}...\n", flush=True)
        await page.goto(profile_url, wait_until="domcontentloaded")

        # Save session automatically if logged in
        await page.wait_for_timeout(3000)
        if "login" not in page.url and "authwall" not in page.url:
            state = await context.storage_state()
            with open("linkedin_session.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

        print("⏳ Browser is OPEN on your Mac screen!", flush=True)
        print(f"   Check file '{SAVED_JSON_PATH}' in your editor to see captured payloads!\n", flush=True)
        
        # Keep browser open for 120 seconds
        for remaining in range(120, 0, -10):
            await asyncio.sleep(10)
            print(f"   ⏱️ Visual Inspection active ({remaining-10}s remaining)...", flush=True)

        await browser.close()
        print("\n✓ Inspection finished.", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Closed by user.", flush=True)
