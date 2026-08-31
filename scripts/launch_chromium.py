#!/usr/bin/env python3
"""
Launch bundled Chromium browser with proxy configured.
This ensures browser traffic strictly adheres to local proxy settings
without interference from enterprise extensions or policy overrides.
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def main():
    # User profile directory (persistent so login state is kept)
    default_profile = os.path.expanduser("~/.config/playwright-chromium-profile")
    profile_dir = os.environ.get("CHROME_USER_DATA_DIR", default_profile)
    print(f"[*] Using browser profile directory: {profile_dir}")
    
    # Configure display (e.g. for VNC / Cloudtop CRD environments)
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"
    print(f"[*] Display set to: {os.environ['DISPLAY']}")

    proxy_server = os.environ.get("PROXY_SERVER", "http://127.0.0.1:8080")
    print(f"[*] Routing traffic through proxy: {proxy_server}")
    
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    default_url = f"https://console.cloud.google.com/bigquery?project={project_id}" if project_id else "https://console.cloud.google.com/bigquery"
    target_url = os.environ.get("TARGET_URL", default_url)
    
    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=[
                    "--ignore-certificate-errors",
                    "--remote-debugging-port=9222"
                ],
                proxy={"server": proxy_server}
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            print(f"[*] Navigating to: {target_url}")
            await page.goto(target_url)
            
            print("\n[+] Chromium is running with proxy enforced.")
            print("[+] Complete login if required, then test BigQuery Studio actions.")
            print("[!] Press Ctrl+C in this terminal to stop the browser session.\n")
            
            # Keep browser process alive
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[*] Stopping Chromium browser...")
        except Exception as e:
            print(f"[-] Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Exited.")
